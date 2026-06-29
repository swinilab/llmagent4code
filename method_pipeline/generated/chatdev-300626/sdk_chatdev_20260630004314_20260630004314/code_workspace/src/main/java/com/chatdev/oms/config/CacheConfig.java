package com.chatdev.oms.config;

import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.concurrent.ConcurrentMapCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Cache configuration for NFR 1.1 (Response Time).
 * Uses concurrent map cache for simplicity; can be replaced with Redis/Caffeine.
 */
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public CacheManager cacheManager() {
        ConcurrentMapCacheManager cacheManager = new ConcurrentMapCacheManager();
        cacheManager.setCacheNames(java.util.List.of(
            "customers",
            "products",
            "orders",
            "invoices",
            "payments"
        ));
        return cacheManager;
    }
}
