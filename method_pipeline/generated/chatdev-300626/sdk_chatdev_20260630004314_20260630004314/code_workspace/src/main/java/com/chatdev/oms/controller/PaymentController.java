package com.chatdev.oms.controller;

import com.chatdev.oms.dto.PaymentCreateRequest;
import com.chatdev.oms.dto.PaymentResponse;
import com.chatdev.oms.service.PaymentService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST Controller for Payment operations.
 * Step 4: Customer pays invoice (POST)
 * Step 5: Accountant verifies payment (PUT /{id}/verify)
 * 
 * API versioning: /api/v1/payments (NFR 2.2 - Interface Stability)
 */
@RestController
@RequestMapping("/api/v1/payments")
@RequiredArgsConstructor
@Tag(name = "Payments", description = "Payment management APIs")
public class PaymentController {

    private final PaymentService paymentService;

    /**
     * Step 4: Customer pays invoice.
     */
    @PostMapping
    @Operation(summary = "Create payment for order (Step 4)")
    public ResponseEntity<PaymentResponse> createPayment(
            @Valid @RequestBody PaymentCreateRequest request) {
        PaymentResponse response = paymentService.createPayment(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get payment by ID")
    public ResponseEntity<PaymentResponse> getPayment(@PathVariable Long id) {
        return ResponseEntity.ok(paymentService.getPayment(id));
    }

    @GetMapping("/order/{orderId}")
    @Operation(summary = "Get payments by order ID")
    public ResponseEntity<List<PaymentResponse>> getPaymentsByOrder(
            @PathVariable Long orderId) {
        return ResponseEntity.ok(paymentService.getPaymentsByOrder(orderId));
    }

    @GetMapping("/transaction/{transactionId}")
    @Operation(summary = "Get payment by transaction ID")
    public ResponseEntity<PaymentResponse> getPaymentByTransactionId(
            @PathVariable String transactionId) {
        return ResponseEntity.ok(paymentService.getPaymentByTransactionId(transactionId));
    }

    @GetMapping
    @Operation(summary = "Get all payments")
    public ResponseEntity<List<PaymentResponse>> getAllPayments() {
        return ResponseEntity.ok(paymentService.getAllPayments());
    }

    /**
     * Step 5: Accountant verifies payment.
     */
    @PutMapping("/{id}/verify")
    @Operation(summary = "Verify payment - approve or reject (Step 5)")
    public ResponseEntity<PaymentResponse> verifyPayment(
            @PathVariable Long id,
            @RequestParam boolean verified) {
        return ResponseEntity.ok(paymentService.verifyPayment(id, verified));
    }
}
