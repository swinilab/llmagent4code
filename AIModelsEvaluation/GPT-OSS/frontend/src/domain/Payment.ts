import { Invoice } from "./Invoice";

export enum PaymentMethod {
  CARD = "CARD",
  PAYPAL = "PAYPAL",
  BANK_TRANSFER = "BANK_TRANSFER",
}

export enum PaymentStatus {
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
}

export interface Payment {
  id: string;
  invoice: Invoice;
  amount: number;
  method: PaymentMethod;
  status: PaymentStatus;
  createdAt: string;
}