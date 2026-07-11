package com.chatdev.oms.dto;

import com.chatdev.oms.enums.PaymentStatus;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/**
 * DTO for payment creation requests.
 */
public record PaymentCreateRequest(
    @NotNull(message = "Order ID is required")
    Long orderId,

    @NotNull(message = "Amount is required")
    @Positive(message = "Amount must be positive")
    Double amount,

    @NotNull(message = "Payment method is required")
    String paymentMethod
) {}
