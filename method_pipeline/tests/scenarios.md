# Order Management System (OMS) - Test Cases Specification

This document outlines the functional and non-functional test cases for the Order Management System (OMS) backend. The test cases are designed to simulate real-world production user behavior and are structured generically to allow seamless adaptation to any API structure or versioning scheme. They are explicitly formatted for easy conversion into Apache JMeter test plans.

---

## 1. Functional Requirements Test Cases

### 1.1 Customer Workflow (Browsing & Checkout)
| Test ID | Scenario | Flow | Pre-conditions | Expected Result / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | **Product Search & Browse** | 1. Search Products Action (with query params)<br>2. Fetch Product Details Action (using extracted Product ID) | None | **Success (2xx)**. Response contains valid product list/details. |
| **F-02** | **Place Order (Checkout)** | 1. Create Order Action (Payload: items, customer info, idempotency key)<br>2. Extract Order ID and Status | Valid customer session | **Created (2xx)**. Status is `CREATED`. Idempotency key prevents duplicate creation on immediate retry. |
| **F-ERR-01** | **Checkout - Insufficient Stock** | 1. Create Order Action (Payload: item quantity exceeding available stock) | Product with 0 or low stock | **Client Error (4xx)**. Clear error message indicating stock failure. Order is not created. |

### 1.2 Order Staff Workflow (Review, Ship, Close)
| Test ID | Scenario | Flow | Pre-conditions | Expected Result / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **F-03** | **Review & Accept Order** | 1. Fetch Order Details Action<br>2. Accept Order Action (using extracted Order ID) | Order exists in `CREATED` status | **Success (2xx)**. Status transitions to `ACCEPTED`. Timestamp is updated. |
| **F-04** | **Ship Paid Order** | 1. Ship Order Action (Payload: tracking information) | Order exists in `PAID` status | **Success (2xx)**. Status transitions to `SHIPPED`. Tracking info is recorded. |
| **F-05** | **Close Completed Order** | 1. Close Order Action | Order exists in `SHIPPED` status | **Success (2xx)**. Status transitions to `CLOSED` (terminal state). |
| **F-ERR-02** | **Invalid State Transition** | 1. Ship Order Action | Order exists in `CREATED` or `ACCEPTED` status (not yet `PAID`) | **Client Error (4xx)**. Error message indicates invalid state transition (e.g., "Cannot ship unpaid order"). |

### 1.3 Accountant Workflow (Invoicing & Payment Verification)
| Test ID | Scenario | Flow | Pre-conditions | Expected Result / Assertions |
| :--- | :--- | :--- | :--- | :--- |
| **F-06** | **Create Invoice** | 1. Generate Invoice Action (Payload: Order ID, billing details) | Order exists in `ACCEPTED` status | **Created (2xx)**. Invoice status is `ISSUED`. Order status updates to `INVOICED`. |
| **F-07** | **Process Customer Payment** | 1. Submit Payment Action (Payload: Invoice ID, amount, payment method) | Invoice exists in `ISSUED` status | **Success (2xx)**. Payment status is `SUCCESS`. Order status updates to `PAID`. |
| **F-08** | **Verify Payment** | 1. Verify Payment Action | Payment exists in `SUCCESS` status | **Success (2xx)**. Payment is marked as fully verified by the system. |
| **F-ERR-03** | **Payment - Amount Mismatch** | 1. Submit Payment Action (Payload: amount less than invoice total) | Invoice exists in `ISSUED` status | **Client Error (4xx)**. Error message indicates payment amount does not match invoice total. |

---

## 2. Non-Functional Requirements (NFR) Test Cases

### 2.1 NFR 1: Performance

#### NFR 1.1: Response Time (Steady State)
*   **Objective:** Validate p95/p99 latencies under sustained, realistic production load.
*   **JMeter Configuration:**
    *   **Thread Group 1 (Search/Browse):** 1,400 threads (70% of load), Ramp-up: 60s, Duration: 10 mins.
    *   **Thread Group 2 (Checkout/Order):** 600 threads (30% of load), Ramp-up: 60s, Duration: 10 mins.
    *   **Total Concurrent Virtual Users:** 2,000.
    *   **Timers:** Gaussian Random Timer to simulate realistic human think-time (e.g., 500ms - 1500ms between actions).
*   **Pass Criteria:**
    *   Search/Browse Actions: p95 ≤ 150ms, p99 ≤ 300ms.
    *   Checkout Actions: p95 ≤ 300ms, p99 ≤ 600ms.
    *   Overall Error Rate: < 0.1%.

#### NFR 1.2: Concurrency & Resource Utilization
*   **Objective:** Sustain peak concurrent sessions while maintaining optimal hardware utilization.
*   **JMeter Configuration:**
    *   **Thread Group:** 5,000 threads, Ramp-up: 120s, Duration: 15 mins.
    *   **Workload Mix:** 70% Search/Browse, 30% Checkout/Order Processing.
    *   **Monitoring:** JMeter PerfMon Plugin or Prometheus/Grafana agent polling the SUT.
*   **Pass Criteria:**
    *   Average Server-Side Queueing Time: < 50ms.
    *   CPU Utilization: Stabilizes between 60% – 85% (validates efficient multi-core QEMU vCPU usage without thrashing).
    *   RAM Utilization: < 80% of 98GB (validates connection pool sizing and cache eviction policies).

#### NFR 1.3: Queue Management & Spike Absorption
*   **Objective:** Absorb a sudden 3x traffic spike over 60 seconds without crashes, unbounded memory growth, or silent request loss.
*   **JMeter Configuration:**
    *   **Plugin:** Ultimate Thread Group or Stepping Thread Group.
    *   **Load Profile:**
        *   0-60s: Baseline load of 1,500 users.
        *   60-120s: Spike to 4,500 users (3x baseline).
        *   120-180s: Drop back to 1,500 users.
    *   **Assertions:** Monitor for explicit admission control responses (e.g., 429 Too Many Requests) but **zero** 500 Internal Server Errors or 503 Service Unavailable (unless explicitly part of the circuit breaker fallback).
*   **Pass Criteria:**
    *   System absorbs the spike. If admission control triggers, it returns clean, structured rejection responses with retry guidance.
    *   Message broker queue depth spikes but remains strictly within bounded capacity limits.
    *   No silent request loss (sum of successful responses and explicit rejections equals 100% of sent requests).

### 2.2 NFR 2: Reliability

#### NFR 2.1: Graceful Degradation (GPU Recommendation Service)
*   **Objective:** Ensure core checkout functionality survives the complete failure or saturation of the non-essential, GPU-heavy Recommendation service.
*   **Test Setup:**
    *   Run NFR 1.1 Checkout load (600 concurrent users).
    *   **Chaos Action:** At minute 3, artificially disable or overload the Recommendation service (e.g., simulate GPU VRAM exhaustion or service shutdown).
*   **JMeter Assertions:**
    *   Core Checkout Action: Must continue returning **Success (2xx)**. Response payload should contain default/fallback recommendation data or an empty list, without breaking the checkout flow.
    *   Recommendation Action (if called independently): Should return a fast fallback response or explicit Service Unavailable (5xx) within 50ms (validating circuit breaker is open).
*   **Pass Criteria:** Core checkout latency remains ≤ 300ms (p95) despite the downstream GPU service being completely unresponsive.

#### NFR 2.2: Fault Detection and Recovery (Transient Database Drop)
*   **Objective:** Validate auto-recovery from temporary database network partitions or connection drops.
*   **Test Setup:**
    *   Run continuous Checkout load (1,000 concurrent users).
    *   **Chaos Action:** Use network simulation tools (e.g., `tc` or `iptables`) on the database server to drop 100% of incoming TCP packets for 15 seconds, then restore connectivity.
*   **JMeter Assertions:**
    *   Monitor error rate: Expected to spike briefly during the 15s drop.
    *   Post-recovery: Error rate must drop back to < 0.1% within 10 seconds *without* requiring a manual restart of the OMS application.
*   **Pass Criteria:** Application health checks temporarily fail, then recover. Retry logic with exponential backoff successfully handles transient drops, and the connection pool automatically evicts dead connections and reconnects.

#### NFR 2.3: State Preservation (Crash Recovery)
*   **Objective:** Ensure no data loss, orphaned states, or duplicate processing if the OMS process crashes mid-transaction.
*   **Test Setup:**
    *   Run continuous Order Placement load (500 concurrent users).
    *   **Chaos Action:** Identify the OMS application Process ID (PID) and execute a force termination (`kill -9`) exactly during peak order creation.
    *   **Recovery Action:** Restart the OMS application via the process manager (e.g., systemd).
*   **JMeter / Database Verification:**
    *   Query the database for orders in intermediate states (e.g., `CREATED` but not `ACCEPTED`).
    *   Verify that the Transactional Outbox has either fully committed or fully rolled back in-flight events.
*   **Pass Criteria:**
    *   No "zombie" orders stuck in invalid intermediate states.
    *   Upon restart, the system seamlessly resumes processing. Idempotency keys successfully prevent duplicate orders if the simulated client retries after the crash.