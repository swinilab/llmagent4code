// Order Domain Model

export class Order {
  id: string;
  customerId: string;
  customerInfo: CustomerInfo;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: OrderStatus;
  createdAt: Date;
  updatedAt: Date;
  invoiceReference: string;
  sessionId: string;

  constructor(data: Partial<Order>) {
    this.id = data.id || '';
    this.customerId = data.customerId || '';
    this.customerInfo = data.customerInfo || { name: '', email: '', address: '', phone: '' };
    this.items = data.items || [];
    this.subtotal = data.subtotal || 0;
    this.tax = data.tax || 0;
    this.total = data.total || 0;
    this.status = data.status || 'pending';
    this.createdAt = data.createdAt || new Date();
    this.updatedAt = data.updatedAt || new Date();
    this.invoiceReference = data.invoiceReference || '';
    this.sessionId = data.sessionId || '';
  }

  calculateTotals(): void {
    this.subtotal = this.items.reduce((sum, item) => sum + item.totalPrice, 0);
    this.tax = this.subtotal * 0.1;
    this.total = this.subtotal + this.tax;
    this.updatedAt = new Date();
  }

  updateStatus(status: OrderStatus): void {
    this.status = status;
    this.updatedAt = new Date();
  }

  generateInvoiceReference(): void {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8).toUpperCase();
    this.invoiceReference = `INV-${timestamp}-${random}`;
  }

  toJSON(): OrderDTO {
    return {
      id: this.id,
      customerId: this.customerId,
      customerInfo: this.customerInfo,
      items: this.items,
      subtotal: this.subtotal,
      tax: this.tax,
      total: this.total,
      status: this.status,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt,
      invoiceReference: this.invoiceReference,
      sessionId: this.sessionId
    };
  }
}

export interface OrderDTO {
  id: string;
  customerId: string;
  customerInfo: CustomerInfo;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: OrderStatus;
  createdAt: Date;
  updatedAt: Date;
  invoiceReference: string;
  sessionId: string;
}

export interface CustomerInfo {
  name: string;
  email: string;
  address: string;
  phone: string;
}

export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export type OrderStatus = 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';
