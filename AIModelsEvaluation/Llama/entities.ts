// Shared domain models

interface Customer {
  id: number;
  name: string;
  address: string;
  phone: string;
  bankingDetails: string;
  orderHistory: Order[];
  userRole: string;
}

interface Order {
  id: number;
  customerId: number;
  items: string[];
  amounts: number[];
  status: string;
  dates: Date[];
  invoiceReference: string;
}

interface Product {
  id: number;
  description: string;
  pricing: number;
}

interface Payment {
  id: number;
  transactionDetails: string;
  amount: number;
  timing: Date;
  status: string;
  paymentMethod: string;
}

interface Invoice {
  id: number;
  billingInformation: string;
  amounts: number[];
  dates: Date[];
  status: string;
}