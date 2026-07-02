package com.example.oms.model;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "invoices")
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Invoice {
    public enum Status { ISSUED, PAID, OVERDUE }

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToOne(mappedBy = "invoice", fetch = FetchType.LAZY)
    private Order order;

    private String billingInfo;
    private BigDecimal amount;
    private LocalDateTime issueDate;
    private LocalDateTime dueDate;
    @Enumerated(EnumType.STRING)
    private Status status;
}
