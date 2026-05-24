import { Link } from "react-router-dom";

export const HomePage = () => (
  <div style={{ padding: "1rem" }}>
    <h1>Order Management Dashboard</h1>
    <p>Use the navigation links above to manage the system.</p>
    <p>
      <Link to="/customers">Add a customer</Link> <br />
      <Link to="/products">Add a product</Link> <br />
      <Link to="/orders">Create an order</Link> <br />
      <Link to="/invoices">Generate an invoice</Link> <br />
      <Link to="/payments">Make a payment</Link>
    </p>
  </div>
);