export interface OrderItem {
	id: number;
	orderId: number;
	productId?: number;
	name: string;
	quantity: number;
	price: number; // Using number for compatibility, but should be handled as Decimal in database
	createdAt: Date;
	updatedAt: Date;
}

export interface OrderData {
	id: number;
	customerId: number;
	customerName: string;
	customerAddress: string;
	customerPhone: string;
	customerBankAccount?: string;
	totalAmount: number;
	status: 'pending' | 'accepted' | 'paid' | 'shipped' | 'closed';
	method: 'bank' | 'card' | 'cash';
	orderDate?: Date;
	createdAt?: Date;
	updatedAt?: Date;
	items: OrderItem[];
}

export class Order {
	id: number;
	customerId: number;
	customerName: string;
	customerAddress: string;
	customerPhone: string;
	customerBankAccount?: string;
	totalAmount: number;
	status: 'pending' | 'accepted' | 'paid' | 'shipped' | 'closed';
	method: 'bank' | 'card' | 'cash';
	orderDate: Date;
	createdAt: Date;
	updatedAt: Date;
	items: OrderItem[];

	constructor(data: OrderData) {
		this.id = data.id;
		this.customerId = data.customerId;
		this.customerName = data.customerName;
		this.customerAddress = data.customerAddress;
		this.customerPhone = data.customerPhone;
		this.customerBankAccount = data.customerBankAccount;
		this.totalAmount = data.totalAmount;
		this.status = data.status;
		this.method = data.method;
		this.orderDate = data.orderDate || new Date();
		this.createdAt = data.createdAt || new Date();
		this.updatedAt = data.updatedAt || new Date();
		this.items = data.items;
	}
}
