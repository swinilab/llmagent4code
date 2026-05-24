import { Request, Response } from 'express';
import { InvoiceService } from '../services/InvoiceService';
import Joi from 'joi';

const invoiceService = new InvoiceService();

const createInvoiceValidationSchema = Joi.object({
  orderId: Joi.string().uuid().required(),
  dueDate: Joi.date().required(),
  notes: Joi.string().optional(),
});

export class InvoiceController {
  async getAllInvoices(req: Request, res: Response): Promise<void> {
    try {
      const invoices = await invoiceService.getAllInvoices();
      res.json({
        success: true,
        data: invoices,
        message: 'Invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoices',
      });
    }
  }

  async getInvoiceById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.getInvoiceById(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice',
      });
    }
  }

  async getInvoicesByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const invoices = await invoiceService.getInvoicesByCustomerId(customerId);
      res.json({
        success: true,
        data: invoices,
        message: 'Customer invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer invoices',
      });
    }
  }

  async getInvoicesByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['draft', 'sent', 'paid', 'overdue', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const invoices = await invoiceService.getInvoicesByStatus(status);
      res.json({
        success: true,
        data: invoices,
        message: `Invoices with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoices by status',
      });
    }
  }

  async getInvoiceByOrderId(req: Request, res: Response): Promise<void> {
    try {
      const { orderId } = req.params;
      const invoice = await invoiceService.getInvoiceByOrderId(orderId);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found for this order',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice by order ID',
      });
    }
  }

  async createInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createInvoiceValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const invoice = await invoiceService.createInvoice(value);
      res.status(201).json({
        success: true,
        data: invoice,
        message: 'Invoice created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create invoice',
      });
    }
  }

  async updateInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const invoice = await invoiceService.updateInvoice(updateData);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update invoice',
      });
    }
  }

  async markInvoiceAsPaid(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.markInvoiceAsPaid(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice marked as paid successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to mark invoice as paid',
      });
    }
  }

  async sendInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.sendInvoice(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice sent successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to send invoice',
      });
    }
  }

  async cancelInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.cancelInvoice(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel invoice',
      });
    }
  }

  async deleteInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await invoiceService.deleteInvoice(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Invoice deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete invoice',
      });
    }
  }

  async getOverdueInvoices(req: Request, res: Response): Promise<void> {
    try {
      const invoices = await invoiceService.getOverdueInvoices();
      res.json({
        success: true,
        data: invoices,
        message: 'Overdue invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve overdue invoices',
      });
    }
  }
}