package com.chatdev.oms.controller;

import com.chatdev.oms.dto.OrderCreateRequest;
import com.chatdev.oms.dto.OrderResponse;
import com.chatdev.oms.enums.OrderStatus;
import com.chatdev.oms.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST Controller for Order operations.
 * Implements the order workflow:
 * Step 1: Customer places order (POST)
 * Step 2: Order Staff reviews & accepts (PUT /{id}/review)
 * Step 6: Order Staff ships paid order (PUT /{id}/ship)
 * Step 7: Order Staff closes completed order (PUT /{id}/close)
 * 
 * API versioning: /api/v1/orders (NFR 2.2 - Interface Stability)
 */
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
@Tag(name = "Orders", description = "Order management APIs - Complete workflow")
public class OrderController {

    private final OrderService orderService;

    /**
     * Step 1: Customer places order.
     */
    @PostMapping
    @Operation(summary = "Place a new order (Step 1)")
    public ResponseEntity<OrderResponse> createOrder(
            @Valid @RequestBody OrderCreateRequest request) {
        OrderResponse response = orderService.createOrder(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get order by ID")
    public ResponseEntity<OrderResponse> getOrder(@PathVariable Long id) {
        return ResponseEntity.ok(orderService.getOrder(id));
    }

    @GetMapping("/customer/{customerId}")
    @Operation(summary = "Get orders by customer ID")
    public ResponseEntity<List<OrderResponse>> getOrdersByCustomer(
            @PathVariable Long customerId) {
        return ResponseEntity.ok(orderService.getOrdersByCustomer(customerId));
    }

    @GetMapping("/status/{status}")
    @Operation(summary = "Get orders by status")
    public ResponseEntity<List<OrderResponse>> getOrdersByStatus(
            @PathVariable OrderStatus status) {
        return ResponseEntity.ok(orderService.getOrdersByStatus(status));
    }

    @GetMapping
    @Operation(summary = "Get all orders")
    public ResponseEntity<List<OrderResponse>> getAllOrders() {
        return ResponseEntity.ok(orderService.getAllOrders());
    }

    /**
     * Step 2: Order Staff reviews and accepts order.
     */
    @PutMapping("/{id}/review")
    @Operation(summary = "Review order - accept or reject (Step 2)")
    public ResponseEntity<OrderResponse> reviewOrder(
            @PathVariable Long id,
            @RequestParam boolean accept) {
        return ResponseEntity.ok(orderService.reviewOrder(id, accept));
    }

    /**
     * Update shipping address.
     */
    @PutMapping("/{id}/shipping-address")
    @Operation(summary = "Update shipping address")
    public ResponseEntity<OrderResponse> updateShippingAddress(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {
        return ResponseEntity.ok(orderService.updateShippingAddress(id, body.get("shippingAddress")));
    }

    /**
     * Step 6: Order Staff ships paid order.
     */
    @PutMapping("/{id}/ship")
    @Operation(summary = "Ship order (Step 6)")
    public ResponseEntity<OrderResponse> shipOrder(@PathVariable Long id) {
        return ResponseEntity.ok(orderService.shipOrder(id));
    }

    /**
     * Step 7: Order Staff closes completed order.
     */
    @PutMapping("/{id}/close")
    @Operation(summary = "Close order (Step 7)")
    public ResponseEntity<OrderResponse> closeOrder(@PathVariable Long id) {
        return ResponseEntity.ok(orderService.closeOrder(id));
    }
}
