package com.example.oms.service;

import com.example.oms.model.Customer;
import com.example.oms.repository.CustomerRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.Optional;

@Service
public class CustomerService {
    private final CustomerRepository repository;

    public CustomerService(CustomerRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<Customer> getAll() { return repository.findAll(); }

    @Transactional(readOnly = true)
    public Optional<Customer> getById(Long id) { return repository.findById(id); }

    @Transactional
    public Customer create(Customer customer) { return repository.save(customer); }

    @Transactional
    public Customer update(Long id, Customer updated) {
        return repository.findById(id).map(c -> {
            c.setName(updated.getName());
            c.setAddress(updated.getAddress());
            c.setPhone(updated.getPhone());
            c.setEmail(updated.getEmail());
            c.setBankingDetails(updated.getBankingDetails());
            c.setRole(updated.getRole());
            return repository.save(c);
        }).orElseThrow(() -> new IllegalArgumentException("Customer not found"));
    }

    @Transactional
    public void delete(Long id) { repository.deleteById(id); }
}
