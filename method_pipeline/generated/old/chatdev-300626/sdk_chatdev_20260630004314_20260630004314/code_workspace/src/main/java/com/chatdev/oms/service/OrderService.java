package com.chatdev.oms.service;

import com.chatdev.oms.dto.*;
import com.chatdev.oms.entity.*;
import com.chatdev.oms.enums.OrderStatus;
import com.chatdev.oms.repository.*;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * Service layer for Order operations.
 * Implements the complete order workflow and business rules.
 * NFR 2.1 (Localization of Changes) - business rules isolated here.
 * NFR 3.2 (Fault Detection & Recovery) - circuit breaker and time limiter applied.
 * NFR 3.3 (State Preservation) - transactional operations.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class OrderService {

    private final OrderRepository orderRepository;
    private final CustomerRepository customerRepository;
    private final ProductRepository productRepository;
    private final OrderItemRepository orderItemRepository;

    // Business rules - can be externalized via config (NFR 2.1, NFR 2.3)
    private static final double DEFAULT_TAX_RATE = 0.10; // 10%
    private static final double BULK_DISCOUNT_THRESHOLD = 1000.0;
    private static final double BULK_DISCOUNT_RATE = 0.05; // 5%

    /**
     * Step 1: Customer places order.
     * NFR 3.2: Circuit breaker and time limiter for fault tolerance.
     */
    @CacheEvict(value = "orders", allEntries = true)
    @CircuitBreaker(name = "backend", fallbackMethod = "createOrderFallback")
    @TimeLimiter(name = "backend")
    public OrderResponse createOrder(OrderCreateRequest request) {
        log.info("Creating order for customer: {}", request.customerId());

        Customer customer = customerRepository.findById(request.customerId())
            .orElseThrow(() -> new IllegalArgumentException("Customer not found: " + request.customerId()));

        Order order = Order.builder()
            .customer(customer)
            .status(OrderStatus.PENDING)
            .shippingAddress(request.shippingAddress())
            .notes(request.notes())
            .build();

        // Add order items
        for (OrderItemRequest itemRequest : request.items()) {
            Product product = productRepository.findById(itemRequest.productId())
                .orElseThrow(() -> new IllegalArgumentException("Product not found: " + itemRequest.productId()));

            OrderItem item = OrderItem.builder()
                .product(product)
                .quantity(itemRequest.quantity())
                .unitPrice(product.getBasePrice())
                .subtotal(product.getBasePrice() * itemRequest.quantity())
                .build();

            order.addItem(item);
        }

        // Calculate amounts
        calculateOrderAmounts(order);

        Order saved = orderRepository.save(order);
        log.info("Order created with ID: {}", saved.getId());

        return mapToResponse(saved);
    }

    /**
     * Fallback method for createOrder when circuit breaker opens.
     * NFR 3.2: Graceful degradation under transient failures.
     */
    public OrderResponse createOrderFallback(OrderCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for createOrder: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Step 2: Order Staff reviews order (transitions to REVIEWING then ACCEPTED/REJECTED).
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @CacheEvict(value = "orders", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "reviewOrderFallback")
    @TimeLimiter(name = "backend")
    public OrderResponse reviewOrder(Long id, boolean accept) {
        log.info("Reviewing order {}: accepted={}", id, accept);

        Order order = orderRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + id));

        if (order.getStatus() != OrderStatus.PENDING) {
            throw new IllegalStateException("Order must be in PENDING status for review");
        }

        // First transition to REVIEWING state
        order.setStatus(OrderStatus.REVIEWING);
        orderRepository.save(order);
        
        // Then transition to final state
        order.setStatus(accept ? OrderStatus.ACCEPTED : OrderStatus.REJECTED);
        Order updated = orderRepository.save(order);

        log.info("Order {} {}", id, accept ? "accepted" : "rejected");
        return mapToResponse(updated);
    }

    /**
     * Fallback method for reviewOrder when circuit breaker opens.
     */
    public OrderResponse reviewOrderFallback(Long id, boolean accept, Exception e) {
        log.error("Circuit breaker triggered for reviewOrder: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Step 6: Order Staff ships paid order.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @CacheEvict(value = "orders", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "shipOrderFallback")
    @TimeLimiter(name = "backend")
    public OrderResponse shipOrder(Long id) {
        log.info("Shipping order: {}", id);

        Order order = orderRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + id));

        if (order.getStatus() != OrderStatus.PAID) {
            throw new IllegalStateException("Order must be in PAID status for shipping");
        }

        // Transition through SHIPPING to SHIPPED
        order.setStatus(OrderStatus.SHIPPING);
        orderRepository.save(order);
        
        order.setStatus(OrderStatus.SHIPPED);
        Order updated = orderRepository.save(order);

        log.info("Order {} shipped", id);
        return mapToResponse(updated);
    }

    /**
     * Fallback method for shipOrder when circuit breaker opens.
     */
    public OrderResponse shipOrderFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for shipOrder: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Step 7: Order Staff closes completed order.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @CacheEvict(value = "orders", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "closeOrderFallback")
    @TimeLimiter(name = "backend")
    public OrderResponse closeOrder(Long id) {
        log.info("Closing order: {}", id);

        Order order = orderRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + id));

        if (order.getStatus() != OrderStatus.SHIPPED) {
            throw new IllegalStateException("Order must be in SHIPPED status for closing");
        }

        order.setStatus(OrderStatus.CLOSED);
        Order updated = orderRepository.save(order);

        log.info("Order {} closed", id);
        return mapToResponse(updated);
    }

    /**
     * Fallback method for closeOrder when circuit breaker opens.
     */
    public OrderResponse closeOrderFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for closeOrder: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get order by ID with caching.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "orders", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "getOrderFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public OrderResponse getOrder(Long id) {
        log.debug("Getting order: {}", id);
        Order order = orderRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + id));
        return mapToResponse(order);
    }

    /**
     * Fallback method for getOrder when circuit breaker opens.
     */
    public OrderResponse getOrderFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for getOrder: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get all orders.
     */
    @Transactional(readOnly = true)
    public List<OrderResponse> getAllOrders() {
        return orderRepository.findAll().stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Get orders by customer ID.
     */
    @Transactional(readOnly = true)
    public List<OrderResponse> getOrdersByCustomer(Long customerId) {
        return orderRepository.findByCustomerId(customerId).stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Get orders by status.
     */
    @Transactional(readOnly = true)
    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderRepository.findByStatus(status).stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Calculate order amounts (subtotal, tax, discount, total).
     * NFR 2.1: Business rule isolated in service layer.
     */
    private void calculateOrderAmounts(Order order) {
        double subtotal = order.getItems().stream()
            .mapToDouble(OrderItem::getSubtotal)
            .sum();

        double taxAmount = subtotal * DEFAULT_TAX_RATE;
        double discountAmount = 0.0;

        // Apply bulk discount if threshold met
        if (subtotal >= BULK_DISCOUNT_THRESHOLD) {
            discountAmount = subtotal * BULK_DISCOUNT_RATE;
        }

        double totalAmount = subtotal + taxAmount - discountAmount;

        order.setSubtotal(subtotal);
        order.setTaxAmount(taxAmount);
        order.setDiscountAmount(discountAmount);
        order.setTotalAmount(totalAmount);
    }

    private OrderResponse mapToResponse(Order order) {
        return new OrderResponse(
            order.getId(),
            order.getCustomer().getId(),
            order.getStatus(),
            order.getTotalAmount(),
            order.getTaxAmount(),
            order.getDiscountAmount(),
            order.getShippingAddress(),
            order.getNotes(),
            order.getCreatedAt(),
            order.getUpdatedAt(),
            order.getInvoice() != null ? order.getInvoice().getId() : null,
            order.getItems().stream().map(item -> new OrderItemResponse(
                item.getId(),
                item.getProduct().getId(),
                item.getProduct().getName(),
                item.getQuantity(),
                item.getUnitPrice(),
                item.getSubtotal()
            )).toList()
        );
    }
}
