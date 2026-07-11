package com.chatdev.oms.service;

import com.chatdev.oms.dto.CustomerCreateRequest;
import com.chatdev.oms.dto.CustomerResponse;
import com.chatdev.oms.enums.UserRole;
import com.chatdev.oms.repository.CustomerRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Integration test for CustomerService.
 */
@SpringBootTest
@Transactional
class CustomerServiceIntegrationTest {

    @Autowired
    private CustomerService customerService;

    @Autowired
    private CustomerRepository customerRepository;

    @Test
    void testCreateCustomer() {
        // Given
        CustomerCreateRequest request = new CustomerCreateRequest(
            "John Doe",
            "123 Main St",
            "555-1234",
            "BANK123",
            UserRole.CUSTOMER
        );

        // When
        CustomerResponse response = customerService.createCustomer(request);

        // Then
        assertNotNull(response.id());
        assertEquals("John Doe", response.name());
        assertEquals("123 Main St", response.address());
        assertEquals(UserRole.CUSTOMER, response.role());
    }

    @Test
    void testGetCustomer() {
        // Given
        CustomerCreateRequest request = new CustomerCreateRequest(
            "Jane Doe",
            "456 Oak Ave",
            "555-5678",
            null,
            UserRole.CUSTOMER
        );
        CustomerResponse created = customerService.createCustomer(request);

        // When
        CustomerResponse retrieved = customerService.getCustomer(created.id());

        // Then
        assertEquals(created.id(), retrieved.id());
        assertEquals("Jane Doe", retrieved.name());
    }

    @Test
    void testGetCustomerNotFound() {
        // When/Then
        assertThrows(IllegalArgumentException.class, () -> {
            customerService.getCustomer(999L);
        });
    }

    @Test
    void testUpdateCustomer() {
        // Given
        CustomerCreateRequest createRequest = new CustomerCreateRequest(
            "Original Name",
            "Original Address",
            "555-0000",
            null,
            UserRole.CUSTOMER
        );
        CustomerResponse created = customerService.createCustomer(createRequest);

        // When
        CustomerCreateRequest updateRequest = new CustomerCreateRequest(
            "Updated Name",
            "Updated Address",
            "555-1111",
            "BANK456",
            UserRole.ORDER_STAFF
        );
        CustomerResponse updated = customerService.updateCustomer(created.id(), updateRequest);

        // Then
        assertEquals("Updated Name", updated.name());
        assertEquals("Updated Address", updated.address());
        assertEquals(UserRole.ORDER_STAFF, updated.role());
    }

    @Test
    void testDeleteCustomer() {
        // Given
        CustomerCreateRequest request = new CustomerCreateRequest(
            "To Delete",
            "Delete Address",
            "555-9999",
            null,
            UserRole.CUSTOMER
        );
        CustomerResponse created = customerService.createCustomer(request);

        // When
        customerService.deleteCustomer(created.id());

        // Then
        assertEquals(0, customerRepository.count());
    }
}
