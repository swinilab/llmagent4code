package com.example.oms.controller;

import com.example.oms.model.Payment;
import com.example.oms.repository.PaymentRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/v1/payments")
@Validated
public class PaymentController {
    private final PaymentRepository repository;
    public PaymentController(PaymentRepository repository) { this.repository = repository; }

    @GetMapping
    public List<Payment> all() { return repository.findAll(); }

    @GetMapping("/{id}")
    public ResponseEntity<Payment> get(@PathVariable Long id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
