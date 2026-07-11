package com.chatdev.oms.dto;

import com.chatdev.oms.enums.InvoiceStatus;
import java.time.LocalDateTime;

/**
 * DTO for invoice response.
 */
public record InvoiceResponse(
    Long id,
    String invoiceNumber,
    Long orderId,
    String billingName,
    String billingAddress,
    Double subtotal,
    Double taxAmount,
    Double discountAmount,
    Double totalAmount,
    LocalDateTime issueDate,
    LocalDateTime dueDate,
    InvoiceStatus status,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}
