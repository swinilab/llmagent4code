package com.example.oms.controller;

import com.example.oms.model.*;
import com.example.oms.service.OrderService;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.math.BigDecimal;
import java.util.List;

@RestController
@RequestMapping("/api/v1/orders")
@Validated
public class OrderController {
    private final OrderService service;

    public OrderController(OrderService service) { this.service = service; }

    @GetMapping
    public List<Order> all() { return service.getAll(); }

    @GetMapping("/{id}")
    public ResponseEntity<Order> get(@PathVariable Long id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/place/{customerId}")
    public Order place(@PathVariable Long customerId, @RequestBody List<OrderItem> items) {
        return service.placeOrder(customerId, items);
    }

    @PostMapping("/accept/{orderId}")
    public Order accept(@PathVariable Long orderId) { return service.acceptOrder(orderId); }

    @PostMapping("/invoice/{orderId}")
    public Invoice createInvoice(@PathVariable Long orderId, @RequestParam String billingInfo) {
        return service.createInvoice(orderId, billingInfo);
    }

    @PostMapping("/pay/{invoiceId}")
    public Payment pay(@PathVariable Long invoiceId,
                       @RequestParam BigDecimal amount,
                       @RequestParam String method) {
        return service.recordPayment(invoiceId, amount, method);
    }

    @PostMapping("/ship/{orderId}")
    public Order ship(@PathVariable Long orderId) { return service.shipOrder(orderId); }

    @PostMapping("/close/{orderId}")
    public Order close(@PathVariable Long orderId) { return service.closeOrder(orderId); }
}
