## **Overview**

Design and implement a full-stack web application following this structure: **Context → Tasks/Requirements → Output**

## **Prompt**

**Context:** You are building a comprehensive order management system that handles the complete workflow from customer orders to payment processing and shipping. The system needs to support multiple user roles (customers, order staff, accountants) and manage the entire order lifecycle efficiently.

**Tasks/Requirements:**

**IMPORTANT: Provide COMPLETE, FULL implementations for ALL components. Do not use placeholders, comments like 'repeat this pattern', or abbreviated examples. Generate the actual, complete code for every single component in every section.**

- **Architecture Design**
  - Follow RESTful, module-based Domain-Driven design principles
  - Organize code into three main areas: user interface, server logic, and shared domain models
  - Each business entity should have its own dedicated space in all three areas
  - Ensure frontend and backend communicate through shared domain classes via REST API
- **Domain Model Definition** Create complete definitions for these five core entities:
  - Customer: Include unique identifier, basic info (name, address, phone), banking details, order history, and user role
  - Order: Include order details, customer information, item list, amounts, status tracking, dates, and invoice reference
  - Product: Include identification, description, and pricing information
  - Payment: Include transaction details, amount, timing, status, and payment method
  - Invoice: Include billing information, amounts, dates, and status tracking
- **User Workflow Implementation** The system must support this complete business process:
  - Customers place orders
  - Order staff review and accept customer orders
  - Accountants create invoices for accepted orders
  - Customers make payments on issued invoices
  - Accountant track if order is paid or not
  - Once the order has been paid, Order Staff ship order
  - Order staff close completed orders after shipping
  - No login needed
- **Front-end Logics** (Use a common front-end framework for implementation) For each business entity, create three complete interface components:
  - Overview component (main entry point for the entity)
  - List/browser component (displays collections of entity data)
  - Interactive form component (handles user input and submissions)
- **Back-end Logics** (Use a common back-end framework for implementation) For each business entity, create three complete server components:
  - Service layer (contains core business logic and operations)
  - Controller layer (handles request/response and coordinates with services)
  - Routing layer (defines API endpoints and HTTP methods)
  - Provide a data source design & implementation that is locally deployable
  - Data source design must be compatible with the shared domain model
- **Shared Domain Models** Create reusable domain model definitions for both front-end and back-end logics which can be used for consistent data handling and API communication.

**Non-functional requirements:**

- Performance:
  - NFR 1.1 (Response Time): The API response round-trip time for core user journeys (e.g., product search, cart updates, checkout initiation) must be as short as possible under expected load.
  - NFR 1.2 (Resource Utilization & Concurrency): The system must process concurrent user requests up to the maximum capacity of the available server resources (leveraging the 98GB RAM) with minimal queuing delay.
  - NFR 1.3 (Queue Management): During sudden traffic spikes, the system must prevent request queue overflow by bounding the size of incoming request queues and rejecting or delaying excess requests gracefully rather than crashing.
- Modifiability
  - NFR 2.1 (Localization of Changes): Modifications to specific business rules (e.g., tax calculations, discount logic, or shipping rates) must be isolatable to dedicated modules without requiring changes to the core order processing engine.
  - NFR 2.2 (Interface Stability): Updates to the frontend user interface or the addition of new client applications must not require recompilation or structural changes to the existing backend API contracts.
  - NFR 2.3 (Deferred Binding): System parameters (e.g., feature flags, cache expiration times, database connection pool limits) must be modifiable at runtime or via external configuration files without requiring a full application restart.
- Reliability
  - NFR 3.1 (Graceful Degradation): Under extreme resource contention (e.g., CPU or RAM saturation), the system must gracefully degrade non-essential features (e.g., personalized product recommendations, heavy analytics logging) to ensure core checkout functionality remains available with minimum downtime.
  - NFR 3.2 (Fault Detection and Recovery): The application must detect internal component failures (e.g., temporary database connection drops or GPU driver hiccups) and automatically attempt to recover or reconnect within the shortest possible time, minimizing user-facing errors.
  - NFR 3.3 (State Preservation): In the event of an unexpected application process crash, the system must be able to restore its operational state and resume processing pending orders upon restart with minimal data loss.



**Output Requirements:**

- Complete, working implementations for every component mentioned. No shortcuts, placeholders, or pattern repetition instructions
- Full setup instructions
- Every component must be fully implemented and ready to use

**CRITICAL: Generate complete, functional code across all layers. Show actual implementation details, not abbreviated examples.**
