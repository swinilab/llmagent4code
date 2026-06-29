package com.chatdev.oms.enums;

/**
 * Order lifecycle status enum.
 * Represents the complete order workflow from placement to closure.
 */
public enum OrderStatus {
    PENDING,          // Order placed by customer
    REVIEWING,        // Under review by order staff
    ACCEPTED,         // Accepted by order staff
    REJECTED,         // Rejected by order staff
    INVOICED,         // Invoice created by accountant
    PAYMENT_PENDING,  // Waiting for customer payment
    PAID,             // Payment verified by accountant
    SHIPPING,         // Being shipped by order staff
    SHIPPED,          // Shipped by order staff
    COMPLETED,        // Order completed
    CLOSED            // Order closed
}
