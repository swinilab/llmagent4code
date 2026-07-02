package com.example.oms.controller;

import com.example.oms.model.Invoice;
import com.example.oms.repository.InvoiceRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/v1/invoices")
@Validated
public class InvoiceController {
    private final InvoiceRepository repository;
    public InvoiceController(InvoiceRepository repository) { this.repository = repository; }

    @GetMapping
    public List<Invoice> all() { return repository.findAll(); }

    @GetMapping("/{id}")
    public ResponseEntity<Invoice> get(@PathVariable Long id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
