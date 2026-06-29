package com.chatdev.oms.dto;

import java.time.LocalDateTime;

/**
 * DTO for product response.
 */
public record ProductResponse(
    Long id,
    String name,
    String description,
    Double basePrice,
    String currency,
    Integer stockQuantity,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}
