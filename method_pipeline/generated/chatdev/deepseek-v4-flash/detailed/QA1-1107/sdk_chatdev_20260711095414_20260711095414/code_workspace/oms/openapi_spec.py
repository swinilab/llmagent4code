"""
OpenAPI 3.0 specification for the OMS backend.
"""
openapi_spec = {
    "openapi": "3.0.3",
    "info": {
        "title": "Order Management System",
        "version": "1.0.0",
        "description": "Production-grade e-commerce OMS backend serving Customer, Order Staff, and Accountant roles.",
    },
    "servers": [{"url": "http://localhost:8000", "description": "Local dev"}],
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/metrics": {
            "get": {
                "summary": "Prometheus metrics",
                "responses": {"200": {"description": "Metrics in text format"}},
            }
        },
        "/api/v1/customers": {
            "post": {
                "summary": "Create a new customer",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/CreateCustomerRequest"}
                        }
                    },
                },
                "responses": {"201": {"description": "Customer created"}},
            },
            "get": {
                "summary": "List all customers",
                "responses": {"200": {"description": "Customer list"}},
            },
        },
        "/api/v1/customers/{customer_id}": {
            "get": {
                "summary": "Get customer by ID",
                "parameters": [
                    {
                        "name": "customer_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {"200": {"description": "Customer details"}},
            }
        },
        "/api/v1/orders": {
            "post": {
                "summary": "Place a new order (checkout-critical)",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PlaceOrderRequest"}
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Order created"},
                    "429": {"description": "Rate limited"},
                },
            }
        },
        "/api/v1/orders/payment": {
            "post": {
                "summary": "Submit payment (checkout-critical, idempotent)",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SubmitPaymentRequest"}
                        }
                    },
                },
                "responses": {
                    "201": {"description": "Payment processed"},
                    "429": {"description": "Rate limited"},
                },
            }
        },
        "/api/v1/orders/{order_id}/accept": {
            "post": {
                "summary": "Accept order (back-office)",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"200": {"description": "Order accepted"}},
            }
        },
        "/api/v1/orders/{order_id}/invoice": {
            "post": {
                "summary": "Create invoice (back-office)",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"201": {"description": "Invoice created"}},
            }
        },
        "/api/v1/orders/{order_id}/verify-payment": {
            "post": {
                "summary": "Verify payment (back-office)",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"200": {"description": "Payment verified"}},
            }
        },
        "/api/v1/orders/{order_id}/ship": {
            "post": {
                "summary": "Ship order (back-office)",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"200": {"description": "Order shipped"}},
            }
        },
        "/api/v1/orders/{order_id}/close": {
            "post": {
                "summary": "Close order (back-office)",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"200": {"description": "Order closed"}},
            }
        },
        "/api/v1/orders/{order_id}/cancel": {
            "post": {
                "summary": "Cancel order",
                "parameters": [
                    {
                        "name": "order_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/TransitionRequest"}
                        }
                    },
                },
                "responses": {"200": {"description": "Order cancelled"}},
            }
        },
        "/api/v1/products/search": {
            "get": {
                "summary": "Search products (browse, p95 ≤ 150ms)",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "schema": {"type": "integer", "default": 20},
                    },
                ],
                "responses": {"200": {"description": "Product list"}},
            }
        },
        "/api/v1/products/{product_id}": {
            "get": {
                "summary": "Get product by ID (cache-aside)",
                "parameters": [
                    {
                        "name": "product_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "responses": {"200": {"description": "Product details"}},
            }
        },
    },
    "components": {
        "schemas": {
            "CreateCustomerRequest": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"type": "string"},
                    "phone": {"type": "string"},
                    "banking_details": {"type": "string"},
                    "role": {"type": "string", "enum": ["CUSTOMER", "ORDER_STAFF", "ACCOUNTANT"]},
                },
                "required": ["name", "address", "phone", "banking_details"],
            },
            "PlaceOrderRequest": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "format": "uuid"},
                    "line_items": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/OrderLineItem"},
                    },
                },
                "required": ["customer_id", "line_items"],
            },
            "OrderLineItem": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "format": "uuid"},
                    "quantity": {"type": "integer", "minimum": 1},
                    "unit_price": {"type": "number"},
                },
                "required": ["product_id", "quantity", "unit_price"],
            },
            "SubmitPaymentRequest": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "format": "uuid"},
                    "amount": {"type": "number"},
                    "method": {
                        "type": "string",
                        "enum": ["CREDIT_CARD", "DEBIT_CARD", "BANK_TRANSFER", "DIGITAL_WALLET"],
                    },
                    "idempotency_key": {"type": "string"},
                },
                "required": ["order_id", "amount", "method", "idempotency_key"],
            },
            "TransitionRequest": {
                "type": "object",
                "properties": {
                    "expected_version": {"type": "integer"},
                },
                "required": ["expected_version"],
            },
        }
    },
}
