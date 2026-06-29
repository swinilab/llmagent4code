package com.chatdev.oms.dto;

import com.chatdev.oms.enums.UserRole;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * DTO for customer creation requests.
 */
public record CustomerCreateRequest(
    @NotBlank(message = "Name is required")
    @Size(max = 255, message = "Name must be less than 255 characters")
    String name,

    @NotBlank(message = "Address is required")
    String address,

    @NotBlank(message = "Phone is required")
    @Size(max = 50, message = "Phone must be less than 50 characters")
    String phone,

    String bankingDetails,

    UserRole role
) {}
