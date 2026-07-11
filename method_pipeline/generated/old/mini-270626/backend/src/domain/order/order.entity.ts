// Order Entity Implementation

import { v4 as uuidv4 } from 'uuid';

export type OrderStatus = 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';

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

export interface OrderData {
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

export class Order {
  public readonly id: string;
  public customerId: string;
  public customerInfo: CustomerInfo;
  public items: OrderItem[];
  public subtotal: number;
  public tax: number;
  public total: number;
  public status: OrderStatus;
  public readonly createdAt: Date;
  public updatedAt: Date;
  public invoiceReference: string;
  public sessionId: string;

  constructor(data: Partial<OrderData>) {
    this.id = data.id || uuidv4();
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

  addItem(item: OrderItem): void {
    const existingItem = this.items.find(i => i.productId === item.productId);
    if (existingItem) {
      existingItem.quantity += item.quantity;
      existingItem.totalPrice = existingItem.quantity * existingItem.unitPrice;
    } else {
      this.items.push(item);
    }
    this.calculateTotals();
  }

  removeItem(productId: string): void {
    this.items = this.items.filter(item => item.productId !== productId);
    this.calculateTotals();
  }

  updateItemQuantity(productId: string, quantity: number): void {
    const item = this.items.find(i => i.productId === productId);
    if (item) {
      if (quantity <= 0) {
        this.removeItem(productId);
      } else {
        item.quantity = quantity;
        item.totalPrice = item.quantity * item.unitPrice;
        this.calculateTotals();
      }
    }
  }

  confirm(): void {
    this.updateStatus('confirmed');
    this.generateInvoiceReference();
  }

  cancel(): void {
    this.updateStatus('cancelled');
  }

  toJSON(): OrderData {
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

  static fromJSON(data: OrderData): Order {
    return new Order(data);
  }
}
