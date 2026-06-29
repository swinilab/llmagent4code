package com.chatdev.oms.dto;

import com.chatdev.oms.enums.PaymentStatus;
import java.time.LocalDateTime;

/**
 * DTO for payment response.
 */
public record PaymentResponse(
    Long id,
    Long orderId,
    Double amount,
    PaymentStatus status,
    String paymentMethod,
    String transactionId,
    LocalDateTime processedAt,
    LocalDateTime createdAt
) {}
