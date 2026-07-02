package com.example.oms.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.List;

@Entity
@Table(name = "orders")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {
    public enum Status {
        CREATED, REVIEWED, ACCEPTED, INVOICED, PAID, SHIPPED, CLOSED, REJECTED
    }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id")
    private Customer customer;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderLineItem> lineItems;

    private BigDecimal totalAmount;
    private String currency;
    @Enumerated(EnumType.STRING)
    private Status status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @OneToOne(cascade = CascadeType.ALL)
    @JoinColumn(name = "invoice_id")
    private Invoice invoice;
}
