package com.chatdev.oms.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI/Swagger configuration for NFR 2.2 (Interface Stability).
 * Provides versioned API documentation.
 */
@Configuration
public class OpenApiConfig {

    @Value("${app.version:1.0.0}")
    private String appVersion;

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
            .info(new Info()
                .title("Order Management System API")
                .version(appVersion)
                .description("Production-grade e-commerce OMS backend API")
                .contact(new Contact()
                    .name("ChatDev")
                    .email("dev@chatdev.com")))
            .servers(List.of(
                new Server().url("/api/v1").description("API v1")
            ));
    }
}
