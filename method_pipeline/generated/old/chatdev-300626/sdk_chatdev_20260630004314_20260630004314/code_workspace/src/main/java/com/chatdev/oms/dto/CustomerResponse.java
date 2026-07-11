package com.chatdev.oms.dto;

import com.chatdev.oms.enums.UserRole;
import java.time.LocalDateTime;

/**
 * DTO for customer response.
 */
public record CustomerResponse(
    Long id,
    String name,
    String address,
    String phone,
    String bankingDetails,
    UserRole role,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {}
