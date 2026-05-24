import { OrderItem } from "./OrderItem";
import { Customer } from "./Customer";

export enum OrderStatus {
  NEW = "NEW",
  ACCEPTED = "ACCEPTED",
  SHIPPED = "SHIPPED",
  CLOSED = "CLOSED",
}

export interface Order {
  id: string;
  customer: Customer;
  items: OrderItem[];
  totalAmount: number;
  status: OrderStatus;
  createdAt: string;
  updatedAt: string;
  invoiceId?: string;
}