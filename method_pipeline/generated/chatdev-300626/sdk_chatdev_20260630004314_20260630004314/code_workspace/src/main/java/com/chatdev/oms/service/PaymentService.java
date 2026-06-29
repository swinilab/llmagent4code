package com.chatdev.oms.service;

import com.chatdev.oms.dto.PaymentCreateRequest;
import com.chatdev.oms.dto.PaymentResponse;
import com.chatdev.oms.entity.Order;
import com.chatdev.oms.entity.Payment;
import com.chatdev.oms.entity.Invoice;
import com.chatdev.oms.enums.InvoiceStatus;
import com.chatdev.oms.enums.OrderStatus;
import com.chatdev.oms.enums.PaymentStatus;
import com.chatdev.oms.repository.OrderRepository;
import com.chatdev.oms.repository.PaymentRepository;
import com.chatdev.oms.repository.InvoiceRepository;
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
 * Service layer for Payment operations.
 * Step 4: Customer pays invoice.
 * Step 5: Accountant verifies payment.
 * NFR 3.2 (Fault Detection & Recovery) - circuit breaker and time limiter applied.
 * NFR 3.3 (State Preservation) - transactional operations.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class PaymentService {

    private final PaymentRepository paymentRepository;
    private final OrderRepository orderRepository;
    private final InvoiceRepository invoiceRepository;

    /**
     * Step 4: Customer pays invoice.
     * Transitions order from INVOICED → PAYMENT_PENDING.
     * NFR 3.2: Circuit breaker and time limiter for fault tolerance.
     */
    @CacheEvict(value = "payments", allEntries = true)
    @CircuitBreaker(name = "backend", fallbackMethod = "createPaymentFallback")
    @TimeLimiter(name = "backend")
    public PaymentResponse createPayment(PaymentCreateRequest request) {
        log.info("Creating payment for order: {}", request.orderId());

        Order order = orderRepository.findById(request.orderId())
            .orElseThrow(() -> new IllegalArgumentException("Order not found: " + request.orderId()));

        if (order.getStatus() != OrderStatus.INVOICED) {
            throw new IllegalStateException("Order must be in INVOICED status to make payment");
        }

        // Transition order to PAYMENT_PENDING state
        order.setStatus(OrderStatus.PAYMENT_PENDING);
        orderRepository.save(order);

        Payment payment = Payment.builder()
            .order(order)
            .amount(request.amount())
            .paymentMethod(request.paymentMethod())
            .status(PaymentStatus.PROCESSING)
            .transactionId(generateTransactionId())
            .build();

        Payment saved = paymentRepository.save(payment);
        log.info("Payment created with transaction ID: {}", saved.getTransactionId());

        return mapToResponse(saved);
    }

    /**
     * Fallback method for createPayment when circuit breaker opens.
     */
    public PaymentResponse createPaymentFallback(PaymentCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for createPayment: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Step 5: Accountant verifies/approves payment.
     * This is the single source of truth for payment verification.
     * Upon successful verification, this method updates:
     * - Payment status to COMPLETED
     * - Order status to PAID
     * - Invoice status to PAID (if invoice exists)
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @CacheEvict(value = "payments", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "verifyPaymentFallback")
    @TimeLimiter(name = "backend")
    public PaymentResponse verifyPayment(Long id, boolean verified) {
        log.info("Verifying payment {}: verified={}", id, verified);

        Payment payment = paymentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Payment not found: " + id));

        if (payment.getStatus() != PaymentStatus.PROCESSING) {
            throw new IllegalStateException("Payment must be in PROCESSING status for verification");
        }

        if (verified) {
            payment.setStatus(PaymentStatus.COMPLETED);
            payment.setProcessedAt(LocalDateTime.now());

            // Update order status from PAYMENT_PENDING to PAID
            Order order = payment.getOrder();
            order.setStatus(OrderStatus.PAID);
            orderRepository.save(order);

            // Update invoice status
            if (order.getInvoice() != null) {
                Invoice invoice = order.getInvoice();
                invoice.setStatus(InvoiceStatus.PAID);
                invoiceRepository.save(invoice);
            }

            log.info("Payment {} verified and completed", id);
        } else {
            payment.setStatus(PaymentStatus.FAILED);
            
            // Revert order status back to INVOICED on payment failure
            Order order = payment.getOrder();
            order.setStatus(OrderStatus.INVOICED);
            orderRepository.save(order);
            
            log.info("Payment {} verification failed - order reverted to INVOICED", id);
        }

        Payment updated = paymentRepository.save(payment);
        return mapToResponse(updated);
    }

    /**
     * Fallback method for verifyPayment when circuit breaker opens.
     */
    public PaymentResponse verifyPaymentFallback(Long id, boolean verified, Exception e) {
        log.error("Circuit breaker triggered for verifyPayment: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get payment by ID with caching.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "payments", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "getPaymentFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public PaymentResponse getPayment(Long id) {
        log.debug("Getting payment: {}", id);
        Payment payment = paymentRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Payment not found: " + id));
        return mapToResponse(payment);
    }

    /**
     * Fallback method for getPayment when circuit breaker opens.
     */
    public PaymentResponse getPaymentFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for getPayment: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get all payments.
     */
    @Transactional(readOnly = true)
    public List<PaymentResponse> getAllPayments() {
        return paymentRepository.findAll().stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Get payments by order ID.
     */
    @Transactional(readOnly = true)
    public List<PaymentResponse> getPaymentsByOrder(Long orderId) {
        return paymentRepository.findByOrderId(orderId).stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Get payment by transaction ID.
     */
    @Transactional(readOnly = true)
    public PaymentResponse getPaymentByTransactionId(String transactionId) {
        return paymentRepository.findByTransactionId(transactionId)
            .map(this::mapToResponse)
            .orElseThrow(() -> new IllegalArgumentException("Payment not found with transaction ID: " + transactionId));
    }

    /**
     * Generate unique transaction ID.
     */
    private String generateTransactionId() {
        return "TXN-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
    }

    private PaymentResponse mapToResponse(Payment payment) {
        return new PaymentResponse(
            payment.getId(),
            payment.getOrder().getId(),
            payment.getAmount(),
            payment.getPaymentMethod(),
            payment.getStatus(),
            payment.getTransactionId(),
            payment.getCreatedAt(),
            payment.getProcessedAt()
        );
    }
}
