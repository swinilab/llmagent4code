package com.chatdev.oms.entity;

import com.chatdev.oms.enums.InvoiceStatus;
import jakarta.persistence.*;
import jakarta.persistence.PreUpdate;
import lombok.*;
import java.time.LocalDateTime;

/**
 * Invoice entity representing billing information for an order.
 */
@Entity
@Table(name = "invoices")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Invoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", unique = true, nullable = false)
    private Order order;

    @Column(unique = true, nullable = false, length = 50)
    private String invoiceNumber;

    @Column(nullable = false, length = 255)
    private String billingName;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String billingAddress;

    @Column(nullable = false)
    private Double subtotal;

    @Column(nullable = false)
    @Builder.Default
    private Double taxAmount = 0.0;

    @Column(nullable = false)
    @Builder.Default
    private Double discountAmount = 0.0;

    @Column(nullable = false)
    private Double totalAmount;

    private LocalDateTime issueDate;

    private LocalDateTime dueDate;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private InvoiceStatus status = InvoiceStatus.DRAFT;

    @Column(nullable = false, updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
