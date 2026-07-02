package com.example.oms.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "invoices")
public class Invoice {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(mappedBy = "invoice")
    private Order order;

    @NotBlank
    private String billingInfo; // could be JSON string

    @NotNull
    private BigDecimal amount;

    private LocalDate issueDate;
    private LocalDate dueDate;

    @Enumerated(EnumType.STRING)
    private InvoiceStatus status;

    @PrePersist
    public void prePersist() {
        issueDate = LocalDate.now();
        dueDate = issueDate.plusDays(30);
        if (status == null) status = InvoiceStatus.DRAFT;
    }

    // getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }
    public String getBillingInfo() { return billingInfo; }
    public void setBillingInfo(String billingInfo) { this.billingInfo = billingInfo; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public LocalDate getIssueDate() { return issueDate; }
    public void setIssueDate(LocalDate issueDate) { this.issueDate = issueDate; }
    public LocalDate getDueDate() { return dueDate; }
    public void setDueDate(LocalDate dueDate) { this.dueDate = dueDate; }
    public InvoiceStatus getStatus() { return status; }
    public void setStatus(InvoiceStatus status) { this.status = status; }
}
