package com.chatdev.oms.dto;

import com.chatdev.oms.enums.OrderStatus;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;

/**
 * DTO for order creation requests.
 */
public record OrderCreateRequest(
    @NotNull(message = "Customer ID is required")
    Long customerId,

    @NotEmpty(message = "Order must have at least one item")
    List<OrderItemRequest> items,

    String shippingAddress,

    String notes
) {}
