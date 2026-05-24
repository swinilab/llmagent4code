import { Order, OrderData } from '../../../modules/order/Order';
import OrderService from './OrderService';

class OrderController {
	private orderService: OrderService;

	constructor() {
		this.orderService = new OrderService();
	}

	async createOrder(data: OrderData): Promise<Order> {
		return this.orderService.createOrder(data);
	}

	async getOrder(orderId: number): Promise<Order | null> {
		return this.orderService.getOrder(orderId);
	}

	async getOrdersByCustomer(customerId: number): Promise<Order[]> {
		return this.orderService.getOrdersByCustomer(customerId);
	}

	async updateOrder(
		orderId: number,
		update: Partial<OrderData>
	): Promise<Order | null> {
		return this.orderService.updateOrder(orderId, update);
	}

	async deleteOrder(orderId: number): Promise<boolean> {
		return this.orderService.deleteOrder(orderId);
	}

	async receiveOrder(orderId: number): Promise<Order | null> {
		return this.orderService.updateOrderStatus(orderId, 'accepted');
	}

	async shipOrder(orderId: number): Promise<Order | null> {
		return this.orderService.updateOrderStatus(orderId, 'shipped');
	}

	async closeOrder(orderId: number): Promise<Order | null> {
		return this.orderService.updateOrderStatus(orderId, 'closed');
	}

	async getAllOrders(): Promise<Order[]> {
		return this.orderService.getAllOrders();
	}
}

export default OrderController;
