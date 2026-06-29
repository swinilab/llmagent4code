package com.chatdev.oms.service;

import com.chatdev.oms.dto.CustomerCreateRequest;
import com.chatdev.oms.dto.CustomerResponse;
import com.chatdev.oms.entity.Customer;
import com.chatdev.oms.enums.UserRole;
import com.chatdev.oms.repository.CustomerRepository;
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
 * Service layer for Customer operations.
 * Implements NFR 1.1 (Response Time) via caching, NFR 3.2 (Fault Detection & Recovery) via circuit breaker,
 * NFR 3.3 (State Preservation) via transactions.
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class CustomerService {

    private final CustomerRepository customerRepository;

    /**
     * Create a new customer.
     * NFR 3.2: Circuit breaker and time limiter for fault tolerance.
     */
    @CacheEvict(value = "customers", allEntries = true)
    @CircuitBreaker(name = "backend", fallbackMethod = "createCustomerFallback")
    @TimeLimiter(name = "backend")
    public CustomerResponse createCustomer(CustomerCreateRequest request) {
        log.info("Creating customer: {}", request.name());

        Customer customer = Customer.builder()
            .name(request.name())
            .address(request.address())
            .phone(request.phone())
            .bankingDetails(request.bankingDetails())
            .role(request.role() != null ? request.role() : UserRole.CUSTOMER)
            .build();

        Customer saved = customerRepository.save(customer);
        log.info("Customer created with ID: {}", saved.getId());

        return mapToResponse(saved);
    }

    /**
     * Fallback method for createCustomer when circuit breaker opens.
     */
    public CustomerResponse createCustomerFallback(CustomerCreateRequest request, Exception e) {
        log.error("Circuit breaker triggered for createCustomer: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get customer by ID with caching.
     * NFR 3.2: Circuit breaker for fault tolerance.
     */
    @Cacheable(value = "customers", key = "#id")
    @CircuitBreaker(name = "backend", fallbackMethod = "getCustomerFallback")
    @TimeLimiter(name = "backend")
    @Transactional(readOnly = true)
    public CustomerResponse getCustomer(Long id) {
        log.debug("Getting customer: {}", id);
        Customer customer = customerRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Customer not found: " + id));
        return mapToResponse(customer);
    }

    /**
     * Fallback method for getCustomer when circuit breaker opens.
     */
    public CustomerResponse getCustomerFallback(Long id, Exception e) {
        log.error("Circuit breaker triggered for getCustomer: {}", e.getMessage());
        throw new RuntimeException("Service temporarily unavailable. Please try again later.", e);
    }

    /**
     * Get all customers.
     */
    @Transactional(readOnly = true)
    public List<CustomerResponse> getAllCustomers() {
        return customerRepository.findAll().stream()
            .map(this::mapToResponse)
            .toList();
    }

    /**
     * Update customer.
     */
    @CacheEvict(value = "customers", key = "#id")
    public CustomerResponse updateCustomer(Long id, CustomerCreateRequest request) {
        log.info("Updating customer: {}", id);

        Customer customer = customerRepository.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("Customer not found: " + id));

        customer.setName(request.name());
        customer.setAddress(request.address());
        customer.setPhone(request.phone());
        customer.setBankingDetails(request.bankingDetails());
        if (request.role() != null) {
            customer.setRole(request.role());
        }

        Customer updated = customerRepository.save(customer);
        return mapToResponse(updated);
    }

    /**
     * Delete customer.
     */
    @CacheEvict(value = "customers", allEntries = true)
    public void deleteCustomer(Long id) {
        log.info("Deleting customer: {}", id);
        customerRepository.deleteById(id);
    }

    private CustomerResponse mapToResponse(Customer customer) {
        return new CustomerResponse(
            customer.getId(),
            customer.getName(),
            customer.getAddress(),
            customer.getPhone(),
            customer.getBankingDetails(),
            customer.getRole(),
            customer.getCreatedAt(),
            customer.getUpdatedAt()
        );
    }
}
