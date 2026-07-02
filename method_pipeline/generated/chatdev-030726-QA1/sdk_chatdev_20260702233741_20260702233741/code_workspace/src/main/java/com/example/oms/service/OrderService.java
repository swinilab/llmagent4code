package com.example.oms.service;

import com.example.oms.model.*;
import com.example.oms.repository.*;
import jakarta.transaction.Transactional;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

import com.example.oms.model.*;
import com.example.oms.repository.*;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final CustomerRepository customerRepository;
    private final ProductRepository productRepository;
    private final InvoiceRepository invoiceRepository;
    private final PaymentRepository paymentRepository;

    @Transactional
    public Order placeOrder(Long customerId, List<OrderLineItemDTO> items) {
        Customer customer = customerRepository.findById(customerId)
                .orElseThrow(() -> new IllegalArgumentException("Customer not found"));
        List<OrderLineItem> lineItems = items.stream().map(dto -> {
            Product product = productRepository.findById(dto.getProductId())
                    .orElseThrow(() -> new IllegalArgumentException("Product not found"));
            BigDecimal unitPrice = product.getBasePrice();
            BigDecimal totalPrice = unitPrice.multiply(BigDecimal.valueOf(dto.getQuantity()));
            return OrderLineItem.builder()
                    .product(product)
                    .quantity(dto.getQuantity())
                    .unitPrice(unitPrice)
                    .totalPrice(totalPrice)
                    .build();
        }).collect(Collectors.toList());
        BigDecimal totalAmount = lineItems.stream()
                .map(OrderLineItem::getTotalPrice)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        Order order = Order.builder()
                .customer(customer)
                .lineItems(lineItems)
                .totalAmount(totalAmount)
                .currency("USD")
                .status(Order.Status.CREATED)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
        // set back-reference
        lineItems.forEach(li -> li.setOrder(order));
        return orderRepository.save(order);
    }

    @Transactional
    public Order reviewOrder(Long orderId, boolean accept) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        order.setStatus(accept ? Order.Status.ACCEPTED : Order.Status.REJECTED);
        order.setUpdatedAt(LocalDateTime.now());
        return orderRepository.save(order);
    }

    @Transactional
    public Invoice createInvoice(Long orderId, String billingInfo) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != Order.Status.ACCEPTED) {
            throw new IllegalStateException("Order must be accepted before invoicing");
        }
        Invoice invoice = Invoice.builder()
                .order(order)
                .billingInfo(billingInfo)
                .amount(order.getTotalAmount())
                .issueDate(LocalDateTime.now())
                .dueDate(LocalDateTime.now().plusDays(30))
                .status(Invoice.Status.ISSUED)
                .build();
        order.setInvoice(invoice);
        order.setStatus(Order.Status.INVOICED);
        order.setUpdatedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
        return invoiceRepository.save(invoice);
    }

    @Transactional
    public Payment recordPayment(Long invoiceId, Payment.Method method) {
        Invoice invoice = invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found"));
        Payment payment = Payment.builder()
                .order(invoice.getOrder())
                .amount(invoice.getAmount())
                .timestamp(LocalDateTime.now())
                .status(Payment.Status.COMPLETED)
                .method(method)
                .build();
        paymentRepository.save(payment);
        // update invoice and order status
        invoice.setStatus(Invoice.Status.PAID);
        invoiceRepository.save(invoice);
        Order order = invoice.getOrder();
        order.setStatus(Order.Status.PAID);
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);
        return payment;
    }

    @Transactional
    public Order shipOrder(Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != Order.Status.PAID) {
            throw new IllegalStateException("Order must be paid before shipping");
        }
        order.setStatus(Order.Status.SHIPPED);
        order.setUpdatedAt(LocalDateTime.now());
        return orderRepository.save(order);
    }

    @Transactional
    public Order closeOrder(Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != Order.Status.SHIPPED) {
            throw new IllegalStateException("Order must be shipped before closure");
        }
        order.setStatus(Order.Status.CLOSED);
        order.setUpdatedAt(LocalDateTime.now());
        return orderRepository.save(order);
    }

    // DTO for incoming line items
    @Data
    public static class OrderLineItemDTO {
        private Long productId;
        private Integer quantity;
    }
}
