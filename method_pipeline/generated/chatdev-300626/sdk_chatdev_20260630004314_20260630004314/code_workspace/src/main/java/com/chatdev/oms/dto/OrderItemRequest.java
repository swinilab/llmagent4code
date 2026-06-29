package com.chatdev.oms.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

/**
 * DTO for order item in order creation.
 */
public record OrderItemRequest(
    @NotNull(message = "Product ID is required")
    Long productId,

    @Positive(message = "Quantity must be positive")
    Integer quantity
) {}
