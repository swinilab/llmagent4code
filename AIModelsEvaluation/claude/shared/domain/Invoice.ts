export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export interface Invoice {
  id: string;
  orderId: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  invoiceNumber: string;
  lineItems: InvoiceLineItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  issueDate: Date;
  dueDate: Date;
  paidDate?: Date;
  billingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateInvoiceRequest {
  orderId: string;
  dueDate: Date;
  notes?: string;
}

export interface UpdateInvoiceRequest {
  id: string;
  status?: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  paidDate?: Date;
  notes?: string;
}