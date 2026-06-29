package com.chatdev.oms.service;

import com.chatdev.oms.dto.ProductCreateRequest;
import com.chatdev.oms.dto.ProductResponse;
import com.chatdev.oms.entity.Product;
import com.chatdev.oms.repository.ProductRepository;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Service layer for Product operations.
 * Implements NFR 1.1 (Response Time) via caching, NFR 3.2 (Fault Detection & Recovery) via circuit breaker.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class ProductService {

    private final ProductRepository productRepository;

    /**
     * Create a new product.
     * NFR 3.2: Circuit breaker and time limiter for fault tolerance.
     */
    @CacheEvict(value = "products", allEntries = true)
    @CircuitBreaker(name = "backend", fallbackMethod = "createProductFallback")
    @TimeLimiter(name = "backend")
    public ProductResponse createProduct(ProductCreateRequest request) {
        log.info("Creating product: {}", request.name());

        Product product = Product.builder()
            .name(request.name())
            .description(request.description())
            .basePrice(request.basePrice())
            .currency(request.currency() != null ? request.currency() : "USD")
            .stockQuantity(request.stockQuantity() != null ? request.stockQuantity() : 0)
            .build();

        Product saved = productRepository.save(product);
        log.info("Product created with ID: {}", saved.getId());

        return mapToResponse(saved);
    }

    /**
     * Fallback method for createProduct when circuit breaker opens.
     */
    public ProductResponse createProductFallback(ProductCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for createProduct: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get product by ID with caching.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "products", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "getProductFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public ProductResponse getProduct(Long id) {
        log.debug("Getting product: {}", id);
        Product product = productRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Product not found: " + id));
        return mapToResponse(product);
    }

    /**
     * Fallback method for getProduct when circuit breaker opens.
     */
    public ProductResponse getProductFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for getProduct: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Search products by name.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "products", key = "'search:' + #name")
    @CircuitBreaker(name = "backend", fallbackMethod = "searchProductsFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public List<ProductResponse> searchProducts(String name) {
        log.debug("Searching products: {}", name);
        return productRepository.findByNameContainingIgnoreCase(name).stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Fallback method for searchProducts when circuit breaker opens.
     */
    public List<ProductResponse> searchProductsFallback(String name, Exception e) {
        log.error("Circuit breaker triggered for searchProducts: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get all products.
     */
    @Transactional(readOnly = true)
    public List<ProductResponse> getAllProducts() {
        return productRepository.findAll().stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Update product.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @CacheEvict(value = "products", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "updateProductFallback")
    @TimeLimiter(name = "backend")
    public ProductResponse updateProduct(Long id, ProductCreateRequest request) {
        log.info("Updating product: {}", id);

        Product product = productRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Product not found: " + id));

        product.setName(request.name());
        product.setDescription(request.description());
        product.setBasePrice(request.basePrice());
        if (request.currency() != null) {
            product.setCurrency(request.currency());
        }
        if (request.stockQuantity() != null) {
            product.setStockQuantity(request.stockQuantity());
        }

        Product updated = productRepository.save(product);
        return mapToResponse(updated);
    }

    /**
     * Fallback method for updateProduct when circuit breaker opens.
     */
    public ProductResponse updateProductFallback(Long id, ProductCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for updateProduct: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Delete product.
     */
    @CacheEvict(value = "products", allEntries = true)
    public void deleteProduct(Long id) {
        log.info("Deleting product: {}", id);
        productRepository.deleteById(id);
    }

    private ProductResponse mapToResponse(Product product) {
        return new ProductResponse(
            product.getId(),
            product.getName(),
            product.getDescription(),
            product.getBasePrice(),
            product.getCurrency(),
            product.getStockQuantity(),
            product.getCreatedAt(),
            product.getUpdatedAt()
        );
    }
}
