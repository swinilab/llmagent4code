#!/usr/bin/env python3
"""
Flask Mock Application for Apache JMeter Performance Testing
============================================================

This is a lightweight, self-contained mock web application designed for
practicing Apache JMeter performance testing. It uses an in-memory Python
list for data storage (no external database required).

INSTALLATION & RUNNING:
-----------------------
1. Install Flask via pip:
   pip install flask

2. Run the application:
   python mock_jmeter_app.py

3. The server will start on http://localhost:5000

ENDPOINTS:
----------
1. GET  /              - Static welcome page (HTML)
2. GET  /items?id=X    - Dynamic item lookup (JSON)
3. POST /orders        - Order submission (JSON)

EXAMPLE JMeter TEST SCENARIOS:
------------------------------
- Test static page retrieval with HTTP Request sampler
- Test parameter handling with /items?id=1, /items?id=2, etc.
- Test POST requests with JSON body and HTTP Header Manager
  (Content-Type: application/json)
- Add Response Assertions to verify JSON responses
- Configure Thread Groups for load testing
"""

from flask import Flask, request, jsonify
import random

# Initialize Flask application
app = Flask(__name__)

# In-memory mock database - list of 3 items
# This simulates a fast database without external dependencies
MOCK_ITEMS = [
    {"id": 1, "name": "Wireless Mouse", "price": 25.99},
    {"id": 2, "name": "Mechanical Keyboard", "price": 89.99},
    {"id": 3, "name": "Gaming Monitor", "price": 299.99}
]


@app.route('/', methods=['GET'])
def static_page():
    """
    Static Page Endpoint (GET /)
    
    Returns a simple HTML welcome page.
    Used to test standard, static page retrieval in JMeter.
    
    Returns:
        HTML string with 200 OK status
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JMeter Mock App - Welcome</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .endpoints { background: #f9f9f9; padding: 15px; border-radius: 4px; margin: 20px 0; }
        code { background: #e8e8e8; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to JMeter Mock Application</h1>
        <p>This is a lightweight mock web application for Apache JMeter performance testing.</p>
        
        <div class="endpoints">
            <h3>Available Endpoints:</h3>
            <ul>
                <li><code>GET /</code> - This static welcome page</li>
                <li><code>GET /items?id=1</code> - Lookup item by ID (returns JSON)</li>
                <li><code>POST /orders</code> - Submit an order (JSON body required)</li>
            </ul>
        </div>
        
        <p><strong>Status:</strong> Server is running and ready for load testing!</p>
    </div>
</body>
</html>"""
    return html_content, 200


@app.route('/items', methods=['GET'])
def get_item():
    """
    Dynamic Resource Lookup Endpoint (GET /items?id=X)
    
    Accepts a query parameter 'id' and returns item details as JSON.
    Simulates a fast mock database lookup from an internal list.
    
    Query Parameters:
        id (int): The item ID to look up (1, 2, or 3)
    
    Returns:
        JSON object with item details (200 OK) if found
        JSON error object (404 Not Found) if not found
    """
    # Get the 'id' query parameter
    item_id = request.args.get('id')
    
    # Validate that id parameter was provided
    if item_id is None:
        return jsonify({"error": "Missing 'id' query parameter"}), 400
    
    # Convert to integer for comparison
    try:
        item_id = int(item_id)
    except ValueError:
        return jsonify({"error": "Invalid 'id' parameter. Must be an integer."}), 400
    
    # Search for item in mock database
    for item in MOCK_ITEMS:
        if item["id"] == item_id:
            # Item found - return with 200 OK
            return jsonify(item), 200
    
    # Item not found - return 404
    return jsonify({"error": "Item not found"}), 404


@app.route('/orders', methods=['POST'])
def create_order():
    """
    Data Submission Endpoint (POST /orders)
    
    Accepts a JSON payload containing 'item_id' and 'quantity'.
    Simulates processing an order and returns a success response.
    
    Request Body (JSON):
        {
            "item_id": 2,
            "quantity": 5
        }
    
    Returns:
        JSON success object with order_id (201 Created)
        JSON error object (400 Bad Request) if validation fails
    """
    # Check if request contains JSON
    if not request.is_json:
        return jsonify({"error": "Request must be JSON (Content-Type: application/json)"}), 400
    
    # Parse JSON payload
    data = request.get_json()
    
    # Validate required fields exist
    if 'item_id' not in data:
        return jsonify({"error": "Missing required field: 'item_id'"}), 400
    
    if 'quantity' not in data:
        return jsonify({"error": "Missing required field: 'quantity'"}), 400
    
    # Validate field types
    try:
        item_id = int(data['item_id'])
        quantity = int(data['quantity'])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid field types. 'item_id' and 'quantity' must be integers."}), 400
    
    # Validate quantity is positive
    if quantity <= 0:
        return jsonify({"error": "Quantity must be a positive integer."}), 400
    
    # Generate a random order ID (simulates database auto-increment)
    order_id = random.randint(10000, 99999)
    
    # Return success response with 201 Created status
    response_data = {
        "status": "Order created successfully",
        "order_id": order_id,
        "details": {
            "item_id": item_id,
            "quantity": quantity
        }
    }
    
    return jsonify(response_data), 201


# Error handlers for common HTTP errors
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors for undefined routes"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 internal server errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    """
    Main entry point - runs the Flask development server.
    
    The server runs on localhost:5000 by default.
    debug=True enables auto-reload on code changes (disable for production).
    """
    print("=" * 60)
    print("JMeter Mock Application Starting...")
    print("=" * 60)
    print("Server URL: http://localhost:5000")
    print("")
    print("Available Endpoints:")
    print("  GET  /              - Static welcome page")
    print("  GET  /items?id=X    - Item lookup (X = 1, 2, or 3)")
    print("  POST /orders        - Order submission (JSON body)")
    print("=" * 60)
    print("")
    
    # Run Flask app on localhost:5000
    # debug=True for development (auto-reload on changes)
    # Use 0.0.0.0 to make it accessible from other machines if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
