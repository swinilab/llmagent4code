package com.chatdev.oms.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * DTO for product creation requests.
 */
public record ProductCreateRequest(
    @NotBlank(message = "Name is required")
    @Size(max = 255, message = "Name must be less than 255 characters")
    String name,

    String description,

    @Positive(message = "Price must be positive")
    Double basePrice,

    @Size(min = 3, max = 3, message = "Currency must be 3 characters")
    String currency,

    Integer stockQuantity
) {}
