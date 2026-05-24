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

**Output Requirements:**

- Complete, working implementations for every component mentioned. No shortcuts, placeholders, or pattern repetition instructions
- Full setup instructions
- Every component must be fully implemented and ready to use

**CRITICAL: Generate complete, functional code across all layers. Show actual implementation details, not abbreviated examples.**
