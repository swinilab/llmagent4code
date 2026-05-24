import Customer from '../../../modules/customer/Customer';
import { OrderItem } from '../../../modules/order/Order';
import CustomerService from './CustomerService';

class CustomerController {
	public customerService: CustomerService;

	constructor(customer: Customer) {
		this.customerService = new CustomerService(customer);
	}

	async createOrder(
		orderItems: OrderItem[],
		paymentMethod: 'bank' | 'card' | 'cash'
	) {
		return this.customerService.createOrder(orderItems, paymentMethod);
	}
	async getOrders() {
		return this.customerService.getOrders();
	}

	async deleteOrder(orderId: number) {
		return this.customerService.deleteOrder(orderId);
	}
}

export default CustomerController;
