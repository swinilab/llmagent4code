import { PrismaClient } from '@prisma/client';
import Customer from '../../../modules/customer/Customer';
import OrderService from '../order/OrderService';
import { Order, OrderData, OrderItem } from '../../../modules/order/Order';
import DomModel from '../../../modules/DomModel';

const prisma = new PrismaClient();

class CustomerService {
	private orderService: OrderService;
	private customer: Customer;

	constructor(customer: Customer) {
		this.orderService = new OrderService();
		this.customer = customer;
	}

	private createCustomerFromRecord(record: any): Customer {
		console.log(`[CustomerService] Creating customer instance from record: ID=${record.id}`);
		try {
			const customer = new Customer(
				record.id,
				record.name,
				record.address,
				record.phone,
				record.bankAccount || undefined,
				record.createdAt,
				record.updatedAt
			);
			console.log(`[CustomerService] Customer instance created successfully: ID=${customer.id}, Name=${customer.name}`);
			DomModel.addCustomer(customer);
			return customer;
		} catch (error) {
			console.error(`[CustomerService] Error creating customer from record:`, error);
			throw error;
		}
	}

	async createCustomer(data: {
		name: string;
		address: string;
		phone: string;
		bankAccount?: string;
	}): Promise<Customer> {
		console.log(`[CustomerService] Creating new customer in database:`, data);
		try {
			const customerRecord = await prisma.customer.create({ data });
			console.log(`[CustomerService] Customer created in database successfully: ID=${customerRecord.id}`);
			return this.createCustomerFromRecord(customerRecord);
		} catch (error) {
			console.error(`[CustomerService] Error creating customer in database:`, error);
			throw error;
		}
	}

	async getCustomer(customerId: number): Promise<Customer | null> {
		let customer = DomModel.getCustomerById(customerId);
		if (!customer) {
			const customerRecord = await prisma.customer.findUnique({
				where: { id: customerId },
			});
			if (customerRecord) {
				customer = this.createCustomerFromRecord(customerRecord);
			}
		}
		return customer || null;
	}

	async updateCustomer(
		customerId: number,
		data: Partial<{
			name: string;
			address: string;
			phone: string;
			bankAccount: string;
		}>
	): Promise<Customer | null> {
		const customerRecord = await prisma.customer.update({
			where: { id: customerId },
			data,
		});
		return this.createCustomerFromRecord(customerRecord);
	}

	async createOrder(
		items: OrderItem[],
		paymentMethod: 'bank' | 'card' | 'cash'
	): Promise<Order> {
		const totalAmount = items.reduce(
			(total, item) => total + item.price * item.quantity,
			0
		);
		const orderData: OrderData = {
			id: Date.now(),
			customerId: this.customer.id,
			customerName: this.customer.name,
			customerAddress: this.customer.address,
			customerPhone: this.customer.phone,
			customerBankAccount: this.customer.bankAccount,
			items,
			totalAmount,
			status: 'pending',
			method: paymentMethod,
			orderDate: new Date(),
		};
		return await this.orderService.createOrder(orderData);
	}

	async getOrders(): Promise<Order[]> {
		return await this.orderService.getOrdersByCustomer(this.customer.id);
	}

	async deleteOrder(orderId: number): Promise<boolean> {
		return await this.orderService.deleteOrder(orderId);
	}

	async getCustomers(): Promise<Customer[]> {
		const customerRecords = await prisma.customer.findMany({
			orderBy: { createdAt: 'desc' },
		});
		return customerRecords.map(record =>
			this.createCustomerFromRecord(record)
		);
	}

	async deleteCustomer(customerId: number): Promise<boolean> {
		try {
			await prisma.customer.delete({
				where: { id: customerId },
			});
			return true;
		} catch (error) {
			console.error('Error deleting customer:', error);
			return false;
		}
	}
}

export default CustomerService;
