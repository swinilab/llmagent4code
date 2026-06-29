package com.chatdev.oms.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Externalized configuration properties for NFR 2.3 (Deferred Binding).
 * All values can be changed via environment variables or application.yml without restart.
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    /**
     * Feature flags for graceful degradation (NFR 3.1).
     */
    private Features features = new Features();

    /**
     * Business rules that can be externalized (NFR 2.1).
     */
    private BusinessRules businessRules = new BusinessRules();

    /**
     * Performance settings (NFR 1.1, NFR 1.2).
     */
    private Performance performance = new Performance();

    @Data
    public static class Features {
        private boolean recommendationsEnabled = true;
        private boolean analyticsEnabled = true;
        private boolean cachingEnabled = true;
    }

    @Data
    public static class BusinessRules {
        private double taxRate = 0.10;
        private double bulkDiscountThreshold = 1000.0;
        private double bulkDiscountRate = 0.05;
        private int invoiceDueDateOffsetDays = 30;
    }

    @Data
    public static class Performance {
        private int cacheTtlSeconds = 300;
        private int maxConnections = 50;
        private int connectionTimeoutMs = 5000;
    }
}
