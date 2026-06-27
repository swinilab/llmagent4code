## **Overview**

Design and implement only an ordering process: **Context → Tasks/Requirements → Output**

## **Prompt**

**Context:** You are building a order process system that handles the complete workflow of customer orders processing. The order system takes order from anonymous user with browser session. The product list is fixed.

**Tasks/Requirements:**

**IMPORTANT: Provide COMPLETE, FULL implementations for ALL components. Do not use placeholders, comments like 'repeat this pattern', or abbreviated examples. Generate the actual, complete code for every single component in every section.**

- **Architecture Design**
  - Follow RESTful, module-based Domain-Driven design principles
  - Organize code into three main areas: user interface, server logic, and shared domain models
  - Each business entity should have its own dedicated space in all three areas
  - Ensure frontend and backend communicate through shared domain classes via REST API
- **Domain Model Definition** Create complete definitions for these core entities:
  - Customer: Include unique identifier, basic info (name, address, phone), banking details, order history, and user role
  - Order: Include order details, customer information, item list, amounts, status tracking, dates, and invoice reference
  - Product: Include identification, description, and pricing information
- **User Workflow Implementation** The system must support this complete business process:
  - Customers place orders
  - The system records placed order
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

**Tech-stack requirements:**
- Choose tech-stack that requires minimal code, but still maintain the fucntional and non-functional requirements.
- The solution must include Docker setup that use supporting microservices to ensure the non-functional requirements are satisfied.

**Non-functional requirements:**

- Performance:
  - NFR 1.1 (Response Time): The API response round-trip time for core user journeys (product search, cart updates, checkout) must be as short as possible under expected load.
  - NFR 1.2 (Resource Utilization & Concurrency): The system must process concurrent user requests up to the maximum capacity of the available server resources (leveraging the 98GB RAM) with minimal queuing delay.
  - NFR 1.3 (Queue Management): During sudden traffic spikes, the system must prevent request queue overflow by bounding the size of incoming request queues and rejecting or delaying excess requests gracefully rather than crashing.



**Output Requirements:**

- Complete, working implementations for every component mentioned. No shortcuts, placeholders, or pattern repetition instructions
- Full setup instructions
- Every component must be fully implemented and ready to use

**CRITICAL: Generate complete, functional code across all layers. Show actual implementation details, not abbreviated examples.**
