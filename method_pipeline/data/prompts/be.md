Act as an expert backend developer. Write a complete, single-file Python script using the Flask framework to create a lightweight mock web application. This application will be used to practice Apache JMeter performance testing, so it needs to be fast and completely self-contained (no external database setup required, use an in-memory Python list for data).

The mock application must implement exactly 3 endpoints representing different HTTP request types:

1. Static Page (GET `/`):
   - Returns a simple HTML page welcoming the user.
   - Used to test standard, static page retrieval.

2. Dynamic Resource Lookup (GET `/items?id=X`):
   - Accepts a query parameter 'id' (e.g., /items?id=1).
   - Simulates a fast mock database lookup from an internal list of 3 items:
     * id 1: {"name": "Wireless Mouse", "price": 25.99}
     * id 2: {"name": "Mechanical Keyboard", "price": 89.99}
     * id 3: {"name": "Gaming Monitor", "price": 299.99}
   - If the id exists, return it as a JSON object with a 200 OK status.
   - If it doesn't exist, return an error JSON object {"error": "Item not found"} with a 404 Not Found status.
   - Used to test parameter handling and response assertions in JMeter.

3. Data Submission (POST `/orders`):
   - Accepts a JSON payload containing 'item_id' and 'quantity', for example:
     {"item_id": 2, "quantity": 5}
   - Simulates processing an order. It should validate that the fields exist.
   - Returns a success JSON response {"status": "Order created successfully", "order_id": <random_int>} with a 201 Created status.
   - Used to test HTTP POST bodies and HTTP Header Managers (Content-Type: application/json) in JMeter.

Include instructions at the top on how to install Flask via pip and run the script on localhost (port 5000). Keep the code clean, robust, and well-commented.