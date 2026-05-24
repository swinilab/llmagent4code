import { Invoice, InvoiceData } from '../../../modules/invoice/Invoice';
import InvoiceService from './InvoiceService';

class InvoiceController {
	private invoiceService: InvoiceService;

	constructor() {
		this.invoiceService = new InvoiceService();
	}

	async createInvoice(data: InvoiceData): Promise<Invoice> {
		return this.invoiceService.createInvoice(data);
	}

	async getInvoice(invoiceId: number): Promise<Invoice | null> {
		return this.invoiceService.getInvoice(invoiceId);
	}

	async getInvoicesByOrder(orderId: number): Promise<Invoice[]> {
		return this.invoiceService.getInvoicesByOrder(orderId);
	}

	async updateInvoice(
		invoiceId: number,
		update: Partial<InvoiceData>
	): Promise<Invoice | null> {
		return this.invoiceService.updateInvoice(invoiceId, update);
	}

	async deleteInvoice(invoiceId: number): Promise<boolean> {
		return this.invoiceService.deleteInvoice(invoiceId);
	}

	async sendInvoice(orderId: number): Promise<Invoice | null> {
		return this.invoiceService.sendInvoice(orderId);
	}

	async getAllInvoices(): Promise<Invoice[]> {
		return this.invoiceService.getAllInvoices();
	}
}

export default InvoiceController;
