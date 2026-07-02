package com.example.oms.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "payments")
public class Payment {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne
    @JoinColumn(name = "order_id", unique = true)
    private Order order;

    @NotNull
    private BigDecimal amount;

    private LocalDateTime timestamp;

    @Enumerated(EnumType.STRING)
    private PaymentStatus status;

    @NotBlank
    private String method; // e.g., CREDIT_CARD, PAYPAL

    @PrePersist
    public void prePersist() {
        timestamp = LocalDateTime.now();
        if (status == null) status = PaymentStatus.PENDING;
    }

    // getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public LocalDateTime getTimestamp() { return timestamp; }
    public void setTimestamp(LocalDateTime timestamp) { this.timestamp = timestamp; }
    public PaymentStatus getStatus() { return status; }
    public void setStatus(PaymentStatus status) { this.status = status; }
    public String getMethod() { return method; }
    public void setMethod(String method) { this.method = method; }
}
