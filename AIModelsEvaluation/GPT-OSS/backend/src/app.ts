import express from "express";
import cors from "cors";
import {
  CustomerRouter,
  ProductRouter,
  OrderRouter,
  InvoiceRouter,
  PaymentRouter,
} from "./routes";

export const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/customers", CustomerRouter);
app.use("/api/products", ProductRouter);
app.use("/api/orders", OrderRouter);
app.use("/api/invoices", InvoiceRouter);
app.use("/api/payments", PaymentRouter);

app.get("/", (_req, res) => {
  res.json({ message: "Order Management API" });
});