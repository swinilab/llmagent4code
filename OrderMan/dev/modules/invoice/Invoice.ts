export interface InvoiceData {
	id: number;
	orderId: number;
	date: Date;
	amount: number;
	status: 'pending' | 'issued' | 'paid';
	method: 'bank' | 'card' | 'cash';
	createdAt?: Date;
	updatedAt?: Date;
}

export class Invoice {
	id: number;
	orderId: number;
	date: Date;
	amount: number;
	status: 'pending' | 'issued' | 'paid';
	method: 'bank' | 'card' | 'cash';
	createdAt: Date;
	updatedAt: Date;

	constructor(data: InvoiceData) {
		this.id = data.id;
		this.orderId = data.orderId;
		this.date = data.date;
		this.amount = data.amount;
		this.status = data.status;
		this.method = data.method;
		this.createdAt = data.createdAt || new Date();
		this.updatedAt = data.updatedAt || new Date();
	}
}
