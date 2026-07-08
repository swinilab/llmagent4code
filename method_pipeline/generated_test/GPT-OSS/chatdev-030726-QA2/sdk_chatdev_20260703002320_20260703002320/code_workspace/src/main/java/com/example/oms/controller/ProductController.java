package com.example.oms.controller;

import com.example.oms.model.Product;
import com.example.oms.repository.ProductRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/api/v1/products")
@Validated
public class ProductController {
    private final ProductRepository repository;
    public ProductController(ProductRepository repository) { this.repository = repository; }

    @GetMapping
    public List<Product> all() { return repository.findAll(); }

    @GetMapping("/{id}")
    public ResponseEntity<Product> get(@PathVariable Long id) {
        return repository.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public Product create(@RequestBody Product product) { return repository.save(product); }

    @PutMapping("/{id}")
    public Product update(@PathVariable Long id, @RequestBody Product product) {
        return repository.findById(id).map(p -> {
            p.setDescription(product.getDescription());
            p.setBasePrice(product.getBasePrice());
            p.setCurrency(product.getCurrency());
            return repository.save(p);
        }).orElseThrow(() -> new IllegalArgumentException("Product not found"));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) { repository.deleteById(id); return ResponseEntity.noContent().build(); }
}
