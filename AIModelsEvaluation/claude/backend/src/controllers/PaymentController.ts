import { Request, Response } from 'express';
import { PaymentService } from '../services/PaymentService';
import Joi from 'joi';

const paymentService = new PaymentService();

const createPaymentValidationSchema = Joi.object({
  invoiceId: Joi.string().uuid().required(),
  amount: Joi.number().positive().required(),
  paymentMethod: Joi.string().valid('credit_card', 'bank_transfer', 'check', 'cash', 'paypal').required(),
  paymentDetails: Joi.object({
    cardLast4: Joi.string().optional(),
    bankAccount: Joi.string().optional(),
    checkNumber: Joi.string().optional(),
    paypalEmail: Joi.string().email().optional(),
  }).required(),
});

export class PaymentController {
  async getAllPayments(req: Request, res: Response): Promise<void> {
    try {
      const payments = await paymentService.getAllPayments();
      res.json({
        success: true,
        data: payments,
        message: 'Payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments',
      });
    }
  }

  async getPaymentById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.getPaymentById(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payment',
      });
    }
  }

  async getPaymentsByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const payments = await paymentService.getPaymentsByCustomerId(customerId);
      res.json({
        success: true,
        data: payments,
        message: 'Customer payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer payments',
      });
    }
  }

  async getPaymentsByInvoiceId(req: Request, res: Response): Promise<void> {
    try {
      const { invoiceId } = req.params;
      const payments = await paymentService.getPaymentsByInvoiceId(invoiceId);
      res.json({
        success: true,
        data: payments,
        message: 'Invoice payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice payments',
      });
    }
  }

  async getPaymentsByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['pending', 'processing', 'completed', 'failed', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const payments = await paymentService.getPaymentsByStatus(status);
      res.json({
        success: true,
        data: payments,
        message: `Payments with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments by status',
      });
    }
  }

  async createPayment(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createPaymentValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const payment = await paymentService.createPayment(value);
      res.status(201).json({
        success: true,
        data: payment,
        message: 'Payment created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create payment',
      });
    }
  }

  async updatePayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const payment = await paymentService.updatePayment(updateData);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update payment',
      });
    }
  }

  async processPayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.processPayment(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment processed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to process payment',
      });
    }
  }

  async cancelPayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.cancelPayment(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel payment',
      });
    }
  }

  async deletePayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await paymentService.deletePayment(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Payment deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete payment',
      });
    }
  }

  async getPaymentsByDateRange(req: Request, res: Response): Promise<void> {
    try {
      const { startDate, endDate } = req.query;

      if (!startDate || !endDate) {
        res.status(400).json({
          success: false,
          message: 'Start date and end date are required',
        });
        return;
      }

      const start = new Date(startDate as string);
      const end = new Date(endDate as string);

      if (isNaN(start.getTime()) || isNaN(end.getTime())) {
        res.status(400).json({
          success: false,
          message: 'Invalid date format',
        });
        return;
      }

      const payments = await paymentService.getPaymentsByDateRange(start, end);
      res.json({
        success: true,
        data: payments,
        message: 'Payments by date range retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments by date range',
      });
    }
  }

  async getPaymentSummary(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.query;
      const summary = await paymentService.getPaymentSummary(customerId as string);
      
      res.json({
        success: true,
        data: summary,
        message: 'Payment summary retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payment summary',
      });
    }
  }
}