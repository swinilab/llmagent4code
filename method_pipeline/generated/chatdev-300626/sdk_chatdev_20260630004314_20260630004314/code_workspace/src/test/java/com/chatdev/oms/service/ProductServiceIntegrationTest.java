package com.chatdev.oms.service;

import com.chatdev.oms.dto.ProductCreateRequest;
import com.chatdev.oms.dto.ProductResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test for ProductService.
 */
@SpringBootTest
@Transactional
class ProductServiceIntegrationTest {

    @Autowired
    private ProductService productService;

    @Test
    void testCreateProduct() {
        // Given
        ProductCreateRequest request = new ProductCreateRequest(
            "Test Product",
            "A test product description",
            99.99,
            "USD",
            100
        );

        // When
        ProductResponse response = productService.createProduct(request);

        // Then
        assertNotNull(response.id());
        assertEquals("Test Product", response.name());
        assertEquals(99.99, response.basePrice());
        assertEquals(100, response.stockQuantity());
    }

    @Test
    void testSearchProducts() {
        // Given
        productService.createProduct(new ProductCreateRequest("Widget A", "Description A", 10.0, "USD", 50));
        productService.createProduct(new ProductCreateRequest("Widget B", "Description B", 20.0, "USD", 30));

        // When
        List<ProductResponse> results = productService.searchProducts("Widget");

        // Then
        assertEquals(2, results.size());
    }

    @Test
    void testGetAllProducts() {
        // Given
        productService.createProduct(new ProductCreateRequest("Product 1", "Desc 1", 15.0, "USD", 25));
        productService.createProduct(new ProductCreateRequest("Product 2", "Desc 2", 25.0, "USD", 35));

        // When
        List<ProductResponse> all = productService.getAllProducts();

        // Then
        assertTrue(all.size() >= 2);
    }
}
