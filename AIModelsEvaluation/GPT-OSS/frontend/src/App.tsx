import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { HomePage } from "./components/HomePage";
import { CustomerPage } from "./components/customers/CustomerPage";
import { ProductPage } from "./components/products/ProductPage";
import { OrderPage } from "./components/orders/OrderPage";
import { InvoicePage } from "./components/invoices/InvoicePage";
import { PaymentPage } from "./components/payments/PaymentPage";

export const App = () => (
  <BrowserRouter>
    <nav style={{ margin: "1rem" }}>
      <Link to="/">Home</Link> | <Link to="/customers">Customers</Link> |{" "}
      <Link to="/products">Products</Link> | <Link to="/orders">Orders</Link> |{" "}
      <Link to="/invoices">Invoices</Link> | <Link to="/payments">Payments</Link>
    </nav>

    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/customers/*" element={<CustomerPage />} />
      <Route path="/products/*" element={<ProductPage />} />
      <Route path="/orders/*" element={<OrderPage />} />
      <Route path="/invoices/*" element={<InvoicePage />} />
      <Route path="/payments/*" element={<PaymentPage />} />
    </Routes>
  </BrowserRouter>
);