package com.chatdev.oms.entity;

import com.chatdev.oms.enums.OrderStatus;
import jakarta.persistence.*;
import jakarta.persistence.PreUpdate;
import lombok.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Order entity representing a customer order.
 * Contains full lifecycle status tracking.
 */
@Entity
@Table(name = "orders")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", nullable = false)
    private Customer customer;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    @Builder.Default
    private OrderStatus status = OrderStatus.PENDING;

    @Column(nullable = false)
    @Builder.Default
    private Double totalAmount = 0.0;

    @Column(nullable = false)
    @Builder.Default
    private Double taxAmount = 0.0;

    @Column(nullable = false)
    @Builder.Default
    private Double discountAmount = 0.0;

    @Column(columnDefinition = "TEXT")
    private String shippingAddress;

    @Column(columnDefinition = "TEXT")
    private String notes;

    @Column(nullable = false, updatable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @OneToOne(fetch = FetchType.LAZY, mappedBy = "order")
    private Invoice invoice;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<OrderItem> items = new ArrayList<>();

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Payment> payments = new ArrayList<>();

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public void addItem(OrderItem item) {
        this.items.add(item);
        item.setOrder(this);
    }

    public void removeItem(OrderItem item) {
        this.items.remove(item);
        item.setOrder(null);
    }

    public void addPayment(Payment payment) {
        this.payments.add(payment);
        payment.setOrder(this);
    }
}
