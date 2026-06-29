package com.chatdev.oms.dto;

import com.chatdev.oms.enums.InvoiceStatus;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

/**
 * DTO for invoice creation requests.
 */
public record InvoiceCreateRequest(
    @NotNull(message = "Order ID is required")
    Long orderId,

    @NotBlank(message = "Billing name is required")
    String billingName,

    @NotBlank(message = "Billing address is required")
    String billingAddress
) {}
