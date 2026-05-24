import { Customer } from './customer/Customer';
import { Order } from './order/Order';
import { Invoice } from './invoice/Invoice';
import { Payment } from './payment/Payment';
import { Product } from './product/Product';

class DomModel {
	private static instance: DomModel;
	public customers: Map<number, Customer> = new Map();
	public orders: Map<number, Order> = new Map();
	public invoices: Map<number, Invoice> = new Map();
	public payments: Map<number, Payment> = new Map();
	public products: Map<number, Product> = new Map();

	private constructor() {
		// Private constructor for singleton pattern
	}

	public static getInstance(): DomModel {
		if (!DomModel.instance) {
			DomModel.instance = new DomModel();
		}
		return DomModel.instance;
	}

	// Customer methods
	public addCustomer(customer: Customer): void {
		console.log(`[DomModel] Adding customer to cache: ID=${customer.id}, Name=${customer.name}`);
		if (!this.customers.has(customer.id)) {
			this.customers.set(customer.id, customer);
			console.log(`[DomModel] Customer cached successfully: ID=${customer.id}`);
		} else {
			console.log(`[DomModel] Customer already in cache: ID=${customer.id}`);
		}
	}

	public getCustomerById(id: number): Customer | null {
		const customer = this.customers.get(id) || null;
		console.log(`[DomModel] Customer cache lookup: ID=${id}, Found=${!!customer}`);
		return customer;
	}

	// Order methods
	public addOrder(order: Order): void {
		console.log(`[DomModel] Adding order to cache: ID=${order.id}, Customer=${order.customerName}, Amount=${order.totalAmount}`);
		if (!this.orders.has(order.id)) {
			this.orders.set(order.id, order);
			console.log(`[DomModel] Order cached successfully: ID=${order.id}`);
		} else {
			console.log(`[DomModel] Order already in cache: ID=${order.id}`);
		}
	}

	public getOrderById(id: number): Order | null {
		const order = this.orders.get(id) || null;
		console.log(`[DomModel] Order cache lookup: ID=${id}, Found=${!!order}`);
		return order;
	}

	// Invoice methods
	public addInvoice(invoice: Invoice): void {
		console.log(`[DomModel] Adding invoice to cache: ID=${invoice.id}, OrderID=${invoice.orderId}, Amount=${invoice.amount}`);
		if (!this.invoices.has(invoice.id)) {
			this.invoices.set(invoice.id, invoice);
			console.log(`[DomModel] Invoice cached successfully: ID=${invoice.id}`);
		} else {
			console.log(`[DomModel] Invoice already in cache: ID=${invoice.id}`);
		}
	}

	public getInvoiceById(id: number): Invoice | null {
		const invoice = this.invoices.get(id) || null;
		console.log(`[DomModel] Invoice cache lookup: ID=${id}, Found=${!!invoice}`);
		return invoice;
	}

	public getInvoiceByOrderId(orderId: number): Invoice | null {
		console.log(`[DomModel] Looking up invoice by order ID: ${orderId}`);
		for (const invoice of this.invoices.values()) {
			if (invoice.orderId === orderId) {
				console.log(`[DomModel] Found invoice for order: OrderID=${orderId}, InvoiceID=${invoice.id}`);
				return invoice;
			}
		}
		console.log(`[DomModel] No invoice found for order: OrderID=${orderId}`);
		return null;
	}

	// Payment methods
	public addPayment(payment: Payment): void {
		console.log(`[DomModel] Adding payment to cache: ID=${payment.id}, InvoiceID=${payment.invoiceId}, Amount=${payment.amount}`);
		if (!this.payments.has(payment.id)) {
			this.payments.set(payment.id, payment);
			console.log(`[DomModel] Payment cached successfully: ID=${payment.id}`);
		} else {
			console.log(`[DomModel] Payment already in cache: ID=${payment.id}`);
		}
	}

	public getPaymentById(id: number): Payment | null {
		const payment = this.payments.get(id) || null;
		console.log(`[DomModel] Payment cache lookup: ID=${id}, Found=${!!payment}`);
		return payment;
	}

	// Product methods
	public addProduct(product: Product): void {
		console.log(`[DomModel] Adding product to cache: ID=${product.id}, Name=${product.name}, Price=${product.price}`);
		if (!this.products.has(product.id)) {
			this.products.set(product.id, product);
			console.log(`[DomModel] Product cached successfully: ID=${product.id}`);
		} else {
			console.log(`[DomModel] Product already in cache: ID=${product.id}`);
		}
	}

	public getProductById(id: number): Product | undefined {
		const product = this.products.get(id);
		console.log(`[DomModel] Product cache lookup: ID=${id}, Found=${!!product}`);
		return product;
	}
}

export default DomModel.getInstance();
