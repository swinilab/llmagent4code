package com.chatdev.oms;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Main Spring Boot application class for the Order Management System.
 * Implements NFR 1.1 (Response Time) via caching, NFR 3.2 (Fault Detection) via resilience.
 */
@SpringBootApplication
@EnableCaching
@EnableAsync
public class OrderManagementSystemApplication {

    public static void main(String[] args) {
        SpringApplication.run(OrderManagementSystemApplication.class, args);
    }
}
