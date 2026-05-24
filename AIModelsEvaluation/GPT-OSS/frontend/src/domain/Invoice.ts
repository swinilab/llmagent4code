import { Order } from "./Order";

export enum InvoiceStatus {
  ISSUED = "ISSUED",
  PAID = "PAID",
}

export interface Invoice {
  id: string;
  order: Order;
  amount: number;
  billingAddress: string;
  status: InvoiceStatus;
  createdAt: string;
}