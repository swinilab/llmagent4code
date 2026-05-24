export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export interface Order {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  status: 'pending' | 'accepted' | 'invoiced' | 'paid' | 'shipped' | 'completed' | 'cancelled';
  orderDate: Date;
  acceptedDate?: Date;
  shippedDate?: Date;
  completedDate?: Date;
  invoiceId?: string;
  shippingAddress: {
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

export interface CreateOrderRequest {
  customerId: string;
  items: {
    productId: string;
    quantity: number;
  }[];
  shippingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  notes?: string;
}

export interface UpdateOrderRequest {
  id: string;
  status?: 'pending' | 'accepted' | 'invoiced' | 'paid' | 'shipped' | 'completed' | 'cancelled';
  notes?: string;
  shippedDate?: Date;
  completedDate?: Date;
}