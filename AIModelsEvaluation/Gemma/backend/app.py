from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///order_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Database Models
class CustomerModel(db.Model):
    customer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    banking_details = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    orders = db.relationship("OrderModel", backref="customer")


class OrderModel(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer_model.customer_id"), nullable=False
    )
    items = db.Column(db.String(255), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.now)
    invoice_reference = db.Column(
        db.Integer, db.ForeignKey("invoice_model.invoice_id"), nullable=True
    )


class InvoiceModel(db.Model):
    invoice_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), nullable=False)
    payments = db.relationship("PaymentModel", backref="invoice")


class PaymentModel(db.Model):
    payment_id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("invoice_model.invoice_id"), nullable=False
    )
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)


# Service Layer (Example for Customers)
def get_customer_by_id(customer_id):
    customer = CustomerModel.query.get(customer_id)
    if customer:
        return customer
    return None


# Controller Layer (Example for Customers)
@app.route("/customers/<int:customer_id>", methods=["GET"])
def get_customer(customer_id):
    customer = get_customer_by_id(customer_id)
    if customer:
        return jsonify(
            {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "address": customer.address,
                "role": customer.role,
            }
        )
    return jsonify({"message": "Customer not found"}), 404


# Add similar routes for other entities.
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist
    app.run(debug=True)

