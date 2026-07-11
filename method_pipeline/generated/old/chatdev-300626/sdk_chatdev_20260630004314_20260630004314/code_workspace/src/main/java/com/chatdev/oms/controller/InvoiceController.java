package com.chatdev.oms.controller;

import com.chatdev.oms.dto.InvoiceCreateRequest;
import com.chatdev.oms.dto.InvoiceResponse;
import com.chatdev.oms.service.InvoiceService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * REST Controller for Invoice operations.
 * Step 3: Accountant creates invoice (POST)
 * Step 5 is handled via Payment verification endpoint (not here)
 * 
 * API versioning: /api/v1/invoices (NFR 2.2 - Interface Stability)
 */
@RestController
@RequestMapping("/api/v1/invoices")
@RequiredArgsConstructor
@Tag(name = "Invoices", description = "Invoice management APIs")
public class InvoiceController {

    private final InvoiceService invoiceService;

    /**
     * Step 3: Accountant creates invoice for accepted order.
     */
    @PostMapping
    @Operation(summary = "Create invoice for order (Step 3)")
    public ResponseEntity<InvoiceResponse> createInvoice(
            @Valid @RequestBody InvoiceCreateRequest request) {
        InvoiceResponse response = invoiceService.createInvoice(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get invoice by ID")
    public ResponseEntity<InvoiceResponse> getInvoice(@PathVariable Long id) {
        return ResponseEntity.ok(invoiceService.getInvoice(id));
    }

    @GetMapping("/order/{orderId}")
    @Operation(summary = "Get invoice by order ID")
    public ResponseEntity<InvoiceResponse> getInvoiceByOrderId(
            @PathVariable Long orderId) {
        return ResponseEntity.ok(invoiceService.getInvoiceByOrderId(orderId));
    }

    @GetMapping
    @Operation(summary = "Get all invoices")
    public ResponseEntity<List<InvoiceResponse>> getAllInvoices() {
        return ResponseEntity.ok(invoiceService.getAllInvoices());
    }

    /**
     * Cancel invoice.
     */
    @PutMapping("/{id}/cancel")
    @Operation(summary = "Cancel invoice")
    public ResponseEntity<InvoiceResponse> cancelInvoice(@PathVariable Long id) {
        return ResponseEntity.ok(invoiceService.cancelInvoice(id));
    }
}
