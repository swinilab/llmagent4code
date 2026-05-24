import Order from '../models/Order';
import Customer from '../models/Customer';
import Product from '../models/Product';
import { Order as IOrder, CreateOrderRequest, UpdateOrderRequest } from '../../../shared/domain/Order';

export class OrderService {
  async getAllOrders(): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch orders: ${error}`);
    }
  }

  async getOrderById(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      return order ? (order.toJSON() as IOrder) : null;
    } catch (error) {
      throw new Error(`Failed to fetch order: ${error}`);
    }
  }

  async getOrdersByCustomerId(customerId: string): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch customer orders: ${error}`);
    }
  }

  async getOrdersByStatus(status: string): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch orders by status: ${error}`);
    }
  }

  async createOrder(orderData: CreateOrderRequest): Promise<IOrder> {
    try {
      // Fetch customer details
      const customer = await Customer.findByPk(orderData.customerId);
      if (!customer) {
        throw new Error('Customer not found');
      }

      // Calculate order totals
      let subtotal = 0;
      const orderItems = [];

      for (const item of orderData.items) {
        const product = await Product.findByPk(item.productId);
        if (!product) {
          throw new Error(`Product with ID ${item.productId} not found`);
        }

        if (product.stockQuantity < item.quantity) {
          throw new Error(`Insufficient stock for product ${product.name}`);
        }

        const totalPrice = product.price * item.quantity;
        subtotal += totalPrice;

        orderItems.push({
          productId: product.id,
          productName: product.name,
          quantity: item.quantity,
          unitPrice: product.price,
          totalPrice,
        });

        // Update product stock
        await product.update({
          stockQuantity: product.stockQuantity - item.quantity,
        });
      }

      const tax = subtotal * 0.08; // 8% tax
      const shipping = subtotal > 100 ? 0 : 15; // Free shipping over $100
      const total = subtotal + tax + shipping;

      const order = await Order.create({
        customerId: orderData.customerId,
        customerName: customer.name,
        customerEmail: customer.email,
        items: orderItems,
        subtotal,
        tax,
        shipping,
        total,
        status: 'pending',
        orderDate: new Date(),
        shippingAddress: orderData.shippingAddress,
        notes: orderData.notes,
      } as any);

      return order.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to create order: ${error}`);
    }
  }

  async updateOrder(updateData: UpdateOrderRequest): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(updateData.id);
      if (!order) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      // Set timestamps based on status changes
      if (updateData.status === 'accepted' && order.status !== 'accepted') {
        updateObject.acceptedDate = new Date();
      }
      if (updateData.status === 'shipped' && order.status !== 'shipped') {
        updateObject.shippedDate = new Date();
      }
      if (updateData.status === 'completed' && order.status !== 'completed') {
        updateObject.completedDate = new Date();
      }

      const updatedOrder = await order.update(updateObject);
      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to update order: ${error}`);
    }
  }

  async acceptOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'pending') {
        throw new Error('Order can only be accepted if it is in pending status');
      }

      const updatedOrder = await order.update({
        status: 'accepted',
        acceptedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to accept order: ${error}`);
    }
  }

  async shipOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'paid') {
        throw new Error('Order can only be shipped if it is paid');
      }

      const updatedOrder = await order.update({
        status: 'shipped',
        shippedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to ship order: ${error}`);
    }
  }

  async completeOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'shipped') {
        throw new Error('Order can only be completed if it is shipped');
      }

      const updatedOrder = await order.update({
        status: 'completed',
        completedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to complete order: ${error}`);
    }
  }

  async cancelOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (!['pending', 'accepted'].includes(order.status)) {
        throw new Error('Order can only be cancelled if it is pending or accepted');
      }

      // Restore product stock
      for (const item of order.items) {
        const product = await Product.findByPk(item.productId);
        if (product) {
          await product.update({
            stockQuantity: product.stockQuantity + item.quantity,
          });
        }
      }

      const updatedOrder = await order.update({
        status: 'cancelled',
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to cancel order: ${error}`);
    }
  }

  async deleteOrder(id: string): Promise<boolean> {
    try {
      const result = await Order.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete order: ${error}`);
    }
  }
}