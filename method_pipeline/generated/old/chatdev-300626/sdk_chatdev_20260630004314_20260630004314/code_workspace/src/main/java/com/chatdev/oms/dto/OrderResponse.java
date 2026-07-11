package com.chatdev.oms.dto;

import com.chatdev.oms.enums.OrderStatus;
import java.time.LocalDateTime;
import java.util.List;

/**
 * DTO for order response.
 */
public record OrderResponse(
    Long id,
    Long customerId,
    String customerName,
    OrderStatus status,
    Double totalAmount,
    Double taxAmount,
    Double discountAmount,
    String shippingAddress,
    String notes,
    LocalDateTime createdAt,
    LocalDateTime updatedAt,
    Long invoiceId,
    List<OrderItemResponse> items
) {}
