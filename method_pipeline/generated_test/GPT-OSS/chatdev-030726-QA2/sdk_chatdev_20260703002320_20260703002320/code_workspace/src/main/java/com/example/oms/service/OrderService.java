package com.example.oms.service;

import com.example.oms.model.*;
import com.example.oms.repository.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

@Service
public class OrderService {
    private final OrderRepository orderRepo;
    private final CustomerRepository customerRepo;
    private final ProductRepository productRepo;
    private final InvoiceRepository invoiceRepo;
    private final PaymentRepository paymentRepo;

    public OrderService(OrderRepository orderRepo, CustomerRepository customerRepo,
                        ProductRepository productRepo, InvoiceRepository invoiceRepo,
                        PaymentRepository paymentRepo) {
        this.orderRepo = orderRepo;
        this.customerRepo = customerRepo;
        this.productRepo = productRepo;
        this.invoiceRepo = invoiceRepo;
        this.paymentRepo = paymentRepo;
    }

    @Transactional(readOnly = true)
    public List<Order> getAll() { return orderRepo.findAll(); }

    @Transactional(readOnly = true)
    public Optional<Order> getById(Long id) { return orderRepo.findById(id); }

    /**
     * Customer places order with line items.
     */
    @Transactional
    public Order placeOrder(Long customerId, List<OrderItem> items) {
        Customer customer = customerRepo.findById(customerId)
                .orElseThrow(() -> new IllegalArgumentException("Customer not found"));
        Order order = new Order();
        order.setCustomer(customer);
        // attach items and compute total
        BigDecimal total = BigDecimal.ZERO;
        for (OrderItem item : items) {
            Product product = productRepo.findById(item.getProduct().getId())
                    .orElseThrow(() -> new IllegalArgumentException("Product not found"));
            item.setProduct(product);
            item.setUnitPrice(product.getBasePrice());
            item.setOrder(order);
            total = total.add(product.getBasePrice().multiply(BigDecimal.valueOf(item.getQuantity())));
        }
        order.setItems(items);
        order.setTotalAmount(total);
        order.setStatus(OrderStatus.PLACED);
        return orderRepo.save(order);
    }

    /**
     * Order Staff reviews and accepts order.
     */
    @Transactional
    public Order acceptOrder(Long orderId) {
        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != OrderStatus.PLACED && order.getStatus() != OrderStatus.REVIEWED) {
            throw new IllegalStateException("Order not in a reviewable state");
        }
        order.setStatus(OrderStatus.ACCEPTED);
        return orderRepo.save(order);
    }

    /**
     * Accountant creates invoice for accepted order.
     */
    @Transactional
    public Invoice createInvoice(Long orderId, String billingInfo) {
        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != OrderStatus.ACCEPTED) {
            throw new IllegalStateException("Order must be accepted before invoicing");
        }
        Invoice invoice = new Invoice();
        invoice.setOrder(order);
        invoice.setBillingInfo(billingInfo);
        invoice.setAmount(order.getTotalAmount());
        invoice.setStatus(InvoiceStatus.ISSUED);
        Invoice saved = invoiceRepo.save(invoice);
        order.setInvoice(saved);
        order.setStatus(OrderStatus.INVOICED);
        orderRepo.save(order);
        return saved;
    }

    /**
     * Customer pays invoice.
     */
    @Transactional
    public Payment recordPayment(Long invoiceId, BigDecimal amount, String method) {
        Invoice invoice = invoiceRepo.findById(invoiceId)
                .orElseThrow(() -> new IllegalArgumentException("Invoice not found"));
        if (invoice.getStatus() != InvoiceStatus.ISSUED) {
            throw new IllegalStateException("Invoice not issued");
        }
        Payment payment = new Payment();
        payment.setOrder(invoice.getOrder());
        payment.setAmount(amount);
        payment.setMethod(method);
        payment.setStatus(PaymentStatus.COMPLETED);
        Payment saved = paymentRepo.save(payment);
        invoice.setStatus(InvoiceStatus.PAID);
        invoiceRepo.save(invoice);
        Order order = invoice.getOrder();
        order.setStatus(OrderStatus.PAID);
        orderRepo.save(order);
        return saved;
    }

    /**
     * Accountant verifies payment (placeholder, already done in recordPayment).
     */
    @Transactional(readOnly = true)
    public Payment verifyPayment(Long paymentId) {
        return paymentRepo.findById(paymentId)
                .orElseThrow(() -> new IllegalArgumentException("Payment not found"));
    }

    /**
     * Order Staff ships paid order.
     */
    @Transactional
    public Order shipOrder(Long orderId) {
        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != OrderStatus.PAID) {
            throw new IllegalStateException("Order must be paid before shipping");
        }
        order.setStatus(OrderStatus.SHIPPED);
        return orderRepo.save(order);
    }

    /**
     * Order Staff closes completed order.
     */
    @Transactional
    public Order closeOrder(Long orderId) {
        Order order = orderRepo.findById(orderId)
                .orElseThrow(() -> new IllegalArgumentException("Order not found"));
        if (order.getStatus() != OrderStatus.SHIPPED) {
            throw new IllegalStateException("Order must be shipped before closure");
        }
        order.setStatus(OrderStatus.CLOSED);
        return orderRepo.save(order);
    }
}
