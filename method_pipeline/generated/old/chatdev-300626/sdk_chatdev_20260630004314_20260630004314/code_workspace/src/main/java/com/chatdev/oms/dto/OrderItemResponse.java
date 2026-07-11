package com.chatdev.oms.dto;

/**
 * DTO for order item response.
 */
public record OrderItemResponse(
    Long id,
    Long productId,
    String productName,
    Integer quantity,
    Double unitPrice,
    Double subtotal
) {}
