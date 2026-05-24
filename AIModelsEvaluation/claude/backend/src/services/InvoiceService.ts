import Invoice from '../models/Invoice';
import Order from '../models/Order';
import Customer from '../models/Customer';
import { Invoice as IInvoice, CreateInvoiceRequest, UpdateInvoiceRequest } from '../../../shared/domain/Invoice';

export class InvoiceService {
  async getAllInvoices(): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch invoices: ${error}`);
    }
  }

  async getInvoiceById(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      return invoice ? (invoice.toJSON() as IInvoice) : null;
    } catch (error) {
      throw new Error(`Failed to fetch invoice: ${error}`);
    }
  }

  async getInvoicesByCustomerId(customerId: string): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch customer invoices: ${error}`);
    }
  }

  async getInvoicesByStatus(status: string): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch invoices by status: ${error}`);
    }
  }

  async getInvoiceByOrderId(orderId: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findOne({
        where: { orderId },
      });
      return invoice ? (invoice.toJSON() as IInvoice) : null;
    } catch (error) {
      throw new Error(`Failed to fetch invoice by order ID: ${error}`);
    }
  }

  async createInvoice(invoiceData: CreateInvoiceRequest): Promise<IInvoice> {
    try {
      // Fetch order details
      const order = await Order.findByPk(invoiceData.orderId);
      if (!order) {
        throw new Error('Order not found');
      }

      if (order.status !== 'accepted') {
        throw new Error('Invoice can only be created for accepted orders');
      }

      // Check if invoice already exists for this order
      const existingInvoice = await Invoice.findOne({
        where: { orderId: invoiceData.orderId },
      });

      if (existingInvoice) {
        throw new Error('Invoice already exists for this order');
      }

      // Fetch customer details
      const customer = await Customer.findByPk(order.customerId);
      if (!customer) {
        throw new Error('Customer not found');
      }

      // Generate invoice number
      const invoiceCount = await Invoice.count();
      const invoiceNumber = `INV-${String(invoiceCount + 1).padStart(6, '0')}`;

      // Convert order items to invoice line items
      const lineItems = order.items.map(item => ({
        description: item.productName,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        totalPrice: item.totalPrice,
      }));

      const invoice = await Invoice.create({
        orderId: invoiceData.orderId,
        customerId: order.customerId,
        customerName: order.customerName,
        customerEmail: order.customerEmail,
        invoiceNumber,
        lineItems,
        subtotal: order.subtotal,
        tax: order.tax,
        total: order.total,
        status: 'draft',
        issueDate: new Date(),
        dueDate: invoiceData.dueDate,
        billingAddress: customer.address,
        notes: invoiceData.notes,
      } as any);

      // Update order status and link invoice
      await order.update({
        status: 'invoiced',
        invoiceId: invoice.id,
      });

      return invoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to create invoice: ${error}`);
    }
  }

  async updateInvoice(updateData: UpdateInvoiceRequest): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(updateData.id);
      if (!invoice) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      const updatedInvoice = await invoice.update(updateObject);
      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to update invoice: ${error}`);
    }
  }

  async markInvoiceAsPaid(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status === 'paid') {
        throw new Error('Invoice is already marked as paid');
      }

      const updatedInvoice = await invoice.update({
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

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to mark invoice as paid: ${error}`);
    }
  }

  async sendInvoice(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status !== 'draft') {
        throw new Error('Only draft invoices can be sent');
      }

      const updatedInvoice = await invoice.update({
        status: 'sent',
      });

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to send invoice: ${error}`);
    }
  }

  async cancelInvoice(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status === 'paid') {
        throw new Error('Cannot cancel a paid invoice');
      }

      const updatedInvoice = await invoice.update({
        status: 'cancelled',
      });

      // Update associated order status back to accepted
      const order = await Order.findByPk(invoice.orderId);
      if (order) {
        await order.update({ status: 'accepted' });
      }

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to cancel invoice: ${error}`);
    }
  }

  async deleteInvoice(id: string): Promise<boolean> {
    try {
      const result = await Invoice.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete invoice: ${error}`);
    }
  }

  async getOverdueInvoices(): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: {
          status: ['sent'],
          dueDate: {
            [require('sequelize').Op.lt]: new Date(),
          },
        },
        order: [['dueDate', 'ASC']],
      });

      // Mark overdue invoices
      for (const invoice of invoices) {
        await invoice.update({ status: 'overdue' });
      }

      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch overdue invoices: ${error}`);
    }
  }
}