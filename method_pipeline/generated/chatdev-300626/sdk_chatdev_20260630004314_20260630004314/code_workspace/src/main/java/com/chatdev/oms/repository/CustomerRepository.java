package com.chatdev.oms.repository;

import com.chatdev.oms.entity.Customer;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * Spring Data repository for Customer entity.
 */
@Repository
public interface CustomerRepository extends JpaRepository<Customer, Long> {
}
