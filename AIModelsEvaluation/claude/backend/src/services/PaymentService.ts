import Payment from '../models/Payment';
import Invoice from '../models/Invoice';
import Order from '../models/Order';
import { Payment as IPayment, CreatePaymentRequest, UpdatePaymentRequest } from '../../../shared/domain/Payment';
import { v4 as uuidv4 } from 'uuid';

export class PaymentService {
  async getAllPayments(): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments: ${error}`);
    }
  }

  async getPaymentById(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      return payment ? (payment.toJSON() as IPayment) : null;
    } catch (error) {
      throw new Error(`Failed to fetch payment: ${error}`);
    }
  }

  async getPaymentsByCustomerId(customerId: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch customer payments: ${error}`);
    }
  }

  async getPaymentsByInvoiceId(invoiceId: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { invoiceId },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch invoice payments: ${error}`);
    }
  }

  async getPaymentsByStatus(status: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments by status: ${error}`);
    }
  }

  async createPayment(paymentData: CreatePaymentRequest): Promise<IPayment> {
    try {
      // Fetch invoice details
      const invoice = await Invoice.findByPk(paymentData.invoiceId);
      if (!invoice) {
        throw new Error('Invoice not found');
      }

      if (invoice.status === 'paid') {
        throw new Error('Invoice is already paid');
      }

      if (invoice.status === 'cancelled') {
        throw new Error('Cannot make payment for cancelled invoice');
      }

      // Validate payment amount
      if (paymentData.amount <= 0) {
        throw new Error('Payment amount must be greater than zero');
      }

      if (paymentData.amount > invoice.total) {
        throw new Error('Payment amount cannot exceed invoice total');
      }

      // Fetch order details
      const order = await Order.findByPk(invoice.orderId);
      if (!order) {
        throw new Error('Associated order not found');
      }

      const payment = await Payment.create({
        invoiceId: paymentData.invoiceId,
        orderId: invoice.orderId,
        customerId: invoice.customerId,
        amount: paymentData.amount,
        paymentMethod: paymentData.paymentMethod,
        status: 'pending',
        paymentDate: new Date(),
        paymentDetails: paymentData.paymentDetails,
      } as any);

      return payment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to create payment: ${error}`);
    }
  }

  async updatePayment(updateData: UpdatePaymentRequest): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(updateData.id);
      if (!payment) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      const updatedPayment = await payment.update(updateObject);
      return updatedPayment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to update payment: ${error}`);
    }
  }

  async processPayment(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      if (!payment) {
        return null;
      }

      if (payment.status !== 'pending') {
        throw new Error('Only pending payments can be processed');
      }

      // Simulate payment processing
      const isSuccessful = Math.random() > 0.1; // 90% success rate
      const transactionId = uuidv4();

      if (isSuccessful) {
        const updatedPayment = await payment.update({
          status: 'completed',
          transactionId,
          processedDate: new Date(),
        });

        // Check if this payment completes the invoice
        const invoice = await Invoice.findByPk(payment.invoiceId);
        if (invoice) {
          const totalPayments = await Payment.sum('amount', {
            where: {
              invoiceId: payment.invoiceId,
              status: 'completed',
            },
          });

          if (totalPayments >= invoice.total) {
            // Mark invoice as paid
            await invoice.update({
              status: 'paid',
              paidDate: new Date(),
            });

            // Update associated order status
            const order = await Order.findByPk(invoice.orderId);
            if (order) {
              await order.update({
                status: 'paid',
              });
            }
          }
        }

        return updatedPayment.toJSON() as IPayment;
      } else {
        const updatedPayment = await payment.update({
          status: 'failed',
          transactionId,
          processedDate: new Date(),
          failureReason: 'Payment processing failed',
        });

        return updatedPayment.toJSON() as IPayment;
      }
    } catch (error) {
      throw new Error(`Failed to process payment: ${error}`);
    }
  }

  async cancelPayment(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      if (!payment) {
        return null;
      }

      if (!['pending', 'processing'].includes(payment.status)) {
        throw new Error('Only pending or processing payments can be cancelled');
      }

      const updatedPayment = await payment.update({
        status: 'cancelled',
        processedDate: new Date(),
      });

      return updatedPayment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to cancel payment: ${error}`);
    }
  }

  async deletePayment(id: string): Promise<boolean> {
    try {
      const result = await Payment.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete payment: ${error}`);
    }
  }

  async getPaymentsByDateRange(startDate: Date, endDate: Date): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: {
          paymentDate: {
            [require('sequelize').Op.between]: [startDate, endDate],
          },
        },
        order: [['paymentDate', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments by date range: ${error}`);
    }
  }

  async getPaymentSummary(customerId?: string): Promise<{
    totalPayments: number;
    completedPayments: number;
    pendingPayments: number;
    failedPayments: number;
    totalAmount: number;
  }> {
    try {
      const whereClause: any = {};
      if (customerId) {
        whereClause.customerId = customerId;
      }

      const allPayments = await Payment.findAll({
        where: whereClause,
      });

      const totalPayments = allPayments.length;
      const completedPayments = allPayments.filter(p => p.status === 'completed').length;
      const pendingPayments = allPayments.filter(p => p.status === 'pending').length;
      const failedPayments = allPayments.filter(p => p.status === 'failed').length;
      const totalAmount = allPayments
        .filter(p => p.status === 'completed')
        .reduce((sum, p) => sum + parseFloat(p.amount.toString()), 0);

      return {
        totalPayments,
        completedPayments,
        pendingPayments,
        failedPayments,
        totalAmount,
      };
    } catch (error) {
      throw new Error(`Failed to get payment summary: ${error}`);
    }
  }
}