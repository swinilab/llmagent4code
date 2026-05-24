import { PrismaClient, Prisma } from '@prisma/client';
import { Order, OrderData } from '../../../modules/order/Order';
import { Customer } from '../../../modules/customer/Customer';
import DomModel from '../../../modules/DomModel';

const prisma = new PrismaClient();

class OrderService {
	private createOrderFromRecord(orderRecord: any): Order {
		console.log(`[OrderService] Creating order instance from record: ID=${orderRecord.id}`);
		try {
			const order = new Order({
				...orderRecord,
				// Map customer data from relation
				customerName: orderRecord.customer?.name || '',
				customerAddress: orderRecord.customer?.address || '',
				customerPhone: orderRecord.customer?.phone || '',
				customerBankAccount: orderRecord.customer?.bankAccount || undefined,
				totalAmount: Number(orderRecord.totalAmount),
				items:
					orderRecord.items?.map((item: any) => {
						console.log(`[OrderService] Processing order item: OrderID=${orderRecord.id}, ProductID=${item.productId}`);
						return {
							...item,
							productId: item.productId || undefined,
							// Map product data from relation
							name: item.product?.name || '',
							price: Number(item.unitPrice), // Map unitPrice to price for interface compatibility
						};
					}) || [],
			});
			console.log(`[OrderService] Order instance created successfully: ID=${order.id}, Customer=${order.customerName}, Items=${order.items.length}`);
			DomModel.addOrder(order);
			return order;
		} catch (error) {
			console.error(`[OrderService] Error creating order from record:`, error);
			throw error;
		}
	}

	private async getCustomerFromDatabase(
		customerId: number
	): Promise<Customer | null> {
		const customerRecord = await prisma.customer.findUnique({
			where: { id: customerId },
		});

		if (customerRecord) {
			return new Customer(
				customerRecord.id,
				customerRecord.name,
				customerRecord.address,
				customerRecord.phone,
				customerRecord.bankAccount || undefined,
				customerRecord.createdAt,
				customerRecord.updatedAt
			);
		}
		return null;
	}

	async createOrder(data: OrderData): Promise<Order> {
		console.log(`[OrderService] Creating new order: CustomerID=${data.customerId}, Items=${data.items.length}`);
		
		// Verify customer exists
		let customer = DomModel.getCustomerById(data.customerId);
		if (!customer) {
			console.log(`[OrderService] Customer not found in cache, fetching from database: ID=${data.customerId}`);
			customer = await this.getCustomerFromDatabase(data.customerId);
			if (customer) {
				console.log(`[OrderService] Customer found in database, adding to cache: ID=${customer.id}`);
				DomModel.addCustomer(customer);
			} else {
				console.error(`[OrderService] Customer not found in database: ID=${data.customerId}`);
				throw new Error('Customer not found');
			}
		}

		// Verify all products exist
		const productIds = data.items
			.map(item => item.productId)
			.filter(id => id !== undefined);
		
		if (productIds.length > 0) {
			console.log(`[OrderService] Verifying products exist: ProductIDs=${productIds.join(',')}`);
			const products = await prisma.product.findMany({
				where: { id: { in: productIds as number[] } },
			});

			if (products.length !== productIds.length) {
				console.error(`[OrderService] Some products not found. Expected=${productIds.length}, Found=${products.length}`);
				throw new Error('One or more products not found');
			}
			console.log(`[OrderService] All products verified successfully`);
		}

		const {
			id,
			items,
			createdAt,
			updatedAt,
			customerName,
			customerAddress,
			customerPhone,
			customerBankAccount,
			...orderCreateData
		} = data;

		// Ensure totalAmount is present and converted to Prisma.Decimal
		const computedTotal =
			(orderCreateData as any).totalAmount ?? data.totalAmount ??
			items.reduce((total, item) => total + Number(item.price || 0) * Number(item.quantity || 0), 0);

		// Explicitly build the create payload so required DB fields are always provided
		const orderCreatePayload: any = {
			customerId: data.customerId,
			totalAmount: new Prisma.Decimal(computedTotal.toFixed ? computedTotal.toFixed(2) : String(computedTotal)),
			status: 'pending',
			orderDate: data.orderDate || new Date(),
			// `method` in Prisma schema. Prefer `method` from data, but fall back to any incoming `paymentMethod`
			method: (data as any).method ?? (orderCreateData as any).method ?? (orderCreateData as any).paymentMethod ?? (data as any).paymentMethod,
		};

		const orderRecord = await prisma.order.create({
			data: orderCreatePayload,
			include: {
				customer: true,
			},
		});

		const orderItems = await Promise.all(
			data.items.map(item => {
				const {
					id: itemId,
					orderId: existingOrderId,
					createdAt: itemCreatedAt,
					updatedAt: itemUpdatedAt,
					name,
					price,
					...itemCreateData
				} = item;
				return prisma.orderItem.create({
					data: {
						orderId: orderRecord.id,
						productId: item.productId || 0, // Handle case where productId might be undefined
						quantity: item.quantity,
						unitPrice: item.price, // Map price to unitPrice for database
					},
					include: {
						product: true,
					},
				});
			})
		);

		return this.createOrderFromRecord({
			...orderRecord,
			items: orderItems,
		});
	}

	async getOrder(orderId: number): Promise<Order | null> {
		let order = DomModel.getOrderById(orderId);
		if (!order) {
			const orderRecord = await prisma.order.findUnique({
				where: { id: orderId },
				include: {
					customer: true,
					items: {
						include: {
							product: true,
						},
					},
				},
			});
			if (orderRecord) {
				order = this.createOrderFromRecord(orderRecord);
			}
		}
		return order || null;
	}

	async getOrdersByCustomer(customerId: number): Promise<Order[]> {
		const orderRecords = await prisma.order.findMany({
			where: { customerId },
			include: {
				customer: true,
				items: {
					include: {
						product: true,
					},
				},
			},
			orderBy: { createdAt: 'desc' },
		});
		return orderRecords.map(record => this.createOrderFromRecord(record));
	}

	async updateOrder(
		orderId: number,
		update: Partial<OrderData>
	): Promise<Order | null> {
		try {
			const {
				id,
				items,
				createdAt,
				updatedAt,
				customerName,
				customerAddress,
				customerPhone,
				customerBankAccount,
				...updateData
			} = update;
			const orderRecord = await prisma.order.update({
				where: { id: orderId },
				data: updateData,
				include: {
					customer: true,
					items: {
						include: {
							product: true,
						},
					},
				},
			});
			return this.createOrderFromRecord(orderRecord);
		} catch (error) {
			console.error('Error updating order:', error);
			return null;
		}
	}

	async deleteOrder(orderId: number): Promise<boolean> {
		try {
			await prisma.order.delete({
				where: { id: orderId },
			});
			return true;
		} catch (error) {
			console.error('Error deleting order:', error);
			return false;
		}
	}

	async updateOrderStatus(
		orderId: number,
		status: string
	): Promise<Order | null> {
		try {
			const orderRecord = await prisma.order.update({
				where: { id: orderId },
				data: { status: status as any },
				include: { items: true },
			});
			return this.createOrderFromRecord(orderRecord);
		} catch (error) {
			console.error('Error updating order status:', error);
			return null;
		}
	}

	async getAllOrders(): Promise<Order[]> {
		const orderRecords = await prisma.order.findMany({
			include: { items: true },
			orderBy: { createdAt: 'desc' },
		});
		return orderRecords.map(record => this.createOrderFromRecord(record));
	}
}

export default OrderService;
