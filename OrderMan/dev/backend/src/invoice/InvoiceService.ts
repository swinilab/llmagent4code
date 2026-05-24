import { PrismaClient } from '@prisma/client';
import { Invoice, InvoiceData } from '../../../modules/invoice/Invoice';
import OrderService from '../order/OrderService';
import DomModel from '../../../modules/DomModel';

const prisma = new PrismaClient();

class InvoiceService {
	private createInvoiceFromRecord(record: any): Invoice {
		console.log(`[InvoiceService] Creating invoice instance from record: ID=${record.id}`);
		try {
			const invoice = new Invoice({
				...record,
				amount: Number(record.amount),
			});
			console.log(`[InvoiceService] Invoice instance created successfully: ID=${invoice.id}, Amount=${invoice.amount}`);
			DomModel.addInvoice(invoice);
			return invoice;
		} catch (error) {
			console.error(`[InvoiceService] Error creating invoice from record:`, error);
			throw error;
		}
	}

	async createInvoice(data: InvoiceData): Promise<Invoice> {
		console.log(`[InvoiceService] Creating new invoice: OrderID=${data.orderId}, Amount=${data.amount}`);
		try {
			const invoiceRecord = await prisma.invoice.create({ data });
			console.log(`[InvoiceService] Invoice created in database successfully: ID=${invoiceRecord.id}`);
			return this.createInvoiceFromRecord(invoiceRecord);
		} catch (error) {
			console.error(`[InvoiceService] Error creating invoice in database:`, error);
			throw error;
		}
	}

	async getInvoice(invoiceId: number): Promise<Invoice | null> {
		console.log(`[InvoiceService] Fetching invoice: ID=${invoiceId}`);
		let invoice = DomModel.getInvoiceById(invoiceId);
		if (!invoice) {
			console.log(`[InvoiceService] Invoice not found in cache, fetching from database: ID=${invoiceId}`);
			const invoiceRecord = await prisma.invoice.findUnique({
				where: { id: invoiceId },
			});
			if (invoiceRecord) {
				console.log(`[InvoiceService] Invoice found in database: ID=${invoiceId}`);
				invoice = this.createInvoiceFromRecord(invoiceRecord);
			} else {
				console.log(`[InvoiceService] Invoice not found in database: ID=${invoiceId}`);
			}
		} else {
			console.log(`[InvoiceService] Invoice found in cache: ID=${invoiceId}`);
		}
		return invoice || null;
	}

	async getInvoicesByOrder(orderId: number): Promise<Invoice[]> {
		const invoiceRecords = await prisma.invoice.findMany({
			where: { orderId },
			orderBy: { createdAt: 'desc' },
		});
		return invoiceRecords.map(record =>
			this.createInvoiceFromRecord(record)
		);
	}

	async updateInvoice(
		invoiceId: number,
		update: Partial<InvoiceData>
	): Promise<Invoice | null> {
		try {
			const invoiceRecord = await prisma.invoice.update({
				where: { id: invoiceId },
				data: update,
			});
			return this.createInvoiceFromRecord(invoiceRecord);
		} catch (error) {
			console.error('Error updating invoice:', error);
			return null;
		}
	}

	async deleteInvoice(invoiceId: number): Promise<boolean> {
		try {
			await prisma.invoice.delete({
				where: { id: invoiceId },
			});
			return true;
		} catch (error) {
			console.error('Error deleting invoice:', error);
			return false;
		}
	}

	async sendInvoice(orderId: number): Promise<Invoice | null> {
		// Find existing invoice for this order
		const existingInvoice = await prisma.invoice.findUnique({
			where: { orderId },
		});

		if (!existingInvoice) {
			throw new Error('No invoice found for this order');
		}

		if (existingInvoice.status === 'issued') {
			throw new Error('Invoice already sent');
		}

		// Simply update status to "issued"
		const updatedInvoice = await prisma.invoice.update({
			where: { orderId },
			data: { status: 'issued' },
		});

		return this.createInvoiceFromRecord(updatedInvoice);
	}

	async getAllInvoices(): Promise<Invoice[]> {
		const invoiceRecords = await prisma.invoice.findMany({
			orderBy: { createdAt: 'desc' },
		});

		return invoiceRecords.map(record =>
			this.createInvoiceFromRecord(record)
		);
	}
}

export default InvoiceService;
