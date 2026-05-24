export interface Payment {
  id: string;
  invoiceId: string;
  orderId: string;
  customerId: string;
  amount: number;
  paymentMethod: 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'paypal';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  transactionId?: string;
  paymentDate: Date;
  processedDate?: Date;
  failureReason?: string;
  paymentDetails: {
    cardLast4?: string;
    bankAccount?: string;
    checkNumber?: string;
    paypalEmail?: string;
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface CreatePaymentRequest {
  invoiceId: string;
  amount: number;
  paymentMethod: 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'paypal';
  paymentDetails: {
    cardLast4?: string;
    bankAccount?: string;
    checkNumber?: string;
    paypalEmail?: string;
  };
}

export interface UpdatePaymentRequest {
  id: string;
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  transactionId?: string;
  processedDate?: Date;
  failureReason?: string;
}