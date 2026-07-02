package com.example.oms.controller;

import com.example.oms.model.Order;
import com.example.oms.model.Invoice;
import com.example.oms.model.Payment;
import com.example.oms.service.OrderService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orderService;

    @PostMapping("/customer/{customerId}")
    public ResponseEntity<Order> placeOrder(
            @PathVariable Long customerId,
            @RequestBody @Valid List<OrderService.OrderLineItemDTO> items) {
        Order order = orderService.placeOrder(customerId, items);
        return ResponseEntity.ok(order);
    }

    @PostMapping("/{orderId}/review")
    public ResponseEntity<Order> reviewOrder(
            @PathVariable Long orderId,
            @RequestParam boolean accept) {
        Order order = orderService.reviewOrder(orderId, accept);
        return ResponseEntity.ok(order);
    }

    @PostMapping("/{orderId}/invoice")
    public ResponseEntity<Invoice> createInvoice(
            @PathVariable Long orderId,
            @RequestParam String billingInfo) {
        Invoice invoice = orderService.createInvoice(orderId, billingInfo);
        return ResponseEntity.ok(invoice);
    }

    @PostMapping("/invoice/{invoiceId}/pay")
    public ResponseEntity<Payment> payInvoice(
            @PathVariable Long invoiceId,
            @RequestParam Payment.Method method) {
        Payment payment = orderService.recordPayment(invoiceId, method);
        return ResponseEntity.ok(payment);
    }

    @PostMapping("/{orderId}/ship")
    public ResponseEntity<Order> shipOrder(@PathVariable Long orderId) {
        Order order = orderService.shipOrder(orderId);
        return ResponseEntity.ok(order);
    }

    @PostMapping("/{orderId}/close")
    public ResponseEntity<Order> closeOrder(@PathVariable Long orderId) {
        Order order = orderService.closeOrder(orderId);
        return ResponseEntity.ok(order);
    }
}
