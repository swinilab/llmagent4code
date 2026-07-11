package com.chatdev.oms.service;

import com.chatdev.oms.dto.InvoiceCreateRequest;
import com.chatdev.oms.dto.InvoiceResponse;
import com.chatdev.oms.entity.Invoice;
import com.chatdev.oms.entity.Order;
import com.chatdev.oms.entity.OrderItem;
import com.chatdev.oms.enums.InvoiceStatus;
import com.chatdev.oms.enums.OrderStatus;
import com.chatdev.oms.repository.InvoiceRepository;
import com.chatdev.oms.repository.OrderRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

/**
 * Service layer for Invoice operations.
 * Step 3: Accountant creates invoice for accepted order.
 * Step 5 (payment verification) is handled by PaymentService.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final OrderRepository orderRepository;

    // Business rule: Invoice due date offset (days) - can be externalized (NFR 2.3)
    private static final int INVOICE_DUE_DATE_OFFSET_DAYS = 30;

    /**
     * Step 3: Accountant creates invoice for accepted order.
     * NFR 3.2: Circuit breaker and time limiter for fault tolerance.
     * NFR 2.1: Subtotal calculated directly from order items (not derived from totals).
     */
    @CacheEvict(value = "invoices", allEntries = true)
    @CircuitBreaker(name = "backend", fallbackMethod = "createInvoiceFallback")
    @TimeLimiter(name = "backend")
    public InvoiceResponse createInvoice(InvoiceCreateRequest request) {
        log.info("Creating invoice for order: {}", request.orderId());

        Order order = orderRepository.findById(request.orderId())
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + request.orderId()));

        if (order.getStatus() != OrderStatus.ACCEPTED) {
            throw new IllegalStateException("Order must be in ACCEPTED status to create invoice");
        }

        if (order.getInvoice() != null) {
            throw new IllegalStateException("Invoice already exists for this order");
        }

        String invoiceNumber = generateInvoiceNumber();

        // Calculate subtotal directly from order items (NFR 2.1 - correct business logic)
        double subtotal = order.getItems().stream()
            .mapToDouble(OrderItem::getSubtotal)
            .sum();

        Invoice invoice = Invoice.builder()
            .order(order)
            .invoiceNumber(invoiceNumber)
            .billingName(request.billingName())
            .billingAddress(request.billingAddress())
            .subtotal(subtotal)
            .taxAmount(order.getTaxAmount())
            .discountAmount(order.getDiscountAmount())
            .totalAmount(order.getTotalAmount())
            .issueDate(LocalDateTime.now())
            .dueDate(LocalDateTime.now().plusDays(INVOICE_DUE_DATE_OFFSET_DAYS))
            .status(InvoiceStatus.ISSUED)
            .build();

        Invoice saved = invoiceRepository.save(invoice);

        // Update order status and link invoice
        order.setInvoice(invoice);
        order.setStatus(OrderStatus.INVOICED);
        orderRepository.save(order);

        log.info("Invoice created with number: {}", invoiceNumber);
        return mapToResponse(saved);
    }

    /**
     * Fallback method for createInvoice when circuit breaker opens.
     */
    public InvoiceResponse createInvoiceFallback(InvoiceCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for createInvoice: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get invoice by ID with caching.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "invoices", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "getInvoiceFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public InvoiceResponse getInvoice(Long id) {
        log.debug("Getting invoice: {}", id);
        Invoice invoice = invoiceRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Invoice not found: " + id));
        return mapToResponse(invoice);
    }

    /**
     * Fallback method for getInvoice when circuit breaker opens.
     */
    public InvoiceResponse getInvoiceFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for getInvoice: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get all invoices.
     */
    @Transactional(readOnly = true)
    public List<InvoiceResponse> getAllInvoices() {
        return invoiceRepository.findAll().stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Get invoice by order ID.
     */
    @Transactional(readOnly = true)
    public InvoiceResponse getInvoiceByOrderId(Long orderId) {
        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + orderId));
        
        if (order.getInvoice() == null) {
            throw new IllegalStateException("No invoice found for order: " + orderId);
        }
        
        return mapToResponse(order.getInvoice());
    }

    /**
     * Generate unique invoice number.
     */
    private String generateInvoiceNumber() {
        return "INV-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }

    private InvoiceResponse mapToResponse(Invoice invoice) {
        return new InvoiceResponse(
            invoice.getId(),
            invoice.getInvoiceNumber(),
            invoice.getOrder().getId(),
            invoice.getBillingName(),
            invoice.getBillingAddress(),
            invoice.getSubtotal(),
            invoice.getTaxAmount(),
            invoice.getDiscountAmount(),
            invoice.getTotalAmount(),
            invoice.getIssueDate(),
            invoice.getDueDate(),
            invoice.getStatus(),
            invoice.getCreatedAt(),
            invoice.getUpdatedAt()
        );
    }
}
