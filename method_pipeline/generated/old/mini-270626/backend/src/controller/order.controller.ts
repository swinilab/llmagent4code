// Order Controller Layer

import { Request, Response } from 'express';
import { OrderService } from '../service/order.service';
import { OrderStatus, CustomerInfo, OrderItem } from '../domain/order/order.entity';

export class OrderController {
  private orderService: OrderService;

  constructor(orderService: OrderService) {
    this.orderService = orderService;
  }

  async createOrder(req: Request, res: Response): Promise<void> {
    try {
      const { customerId, customerInfo, items, sessionId } = req.body;

      if (!customerId || !customerInfo || !items || !sessionId) {
        res.status(400).json({
          success: false,
          error: 'Missing required fields: customerId, customerInfo, items, sessionId'
        });
        return;
      }

      const info: CustomerInfo = {
        name: customerInfo.name || '',
        email: customerInfo.email || '',
        address: customerInfo.address || '',
        phone: customerInfo.phone || ''
      };

      const orderItems: OrderItem[] = items.map((item: any) => ({
        productId: item.productId,
        productName: item.productName || '',
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        totalPrice: item.quantity * item.unitPrice
      }));

      const order = await this.orderService.createOrder(customerId, info, orderItems, sessionId);

      res.status(201).json({
        success: true,
        data: order.toJSON(),
        message: 'Order created successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to create order',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getOrderById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await this.orderService.getOrderById(id);

      if (!order) {
        res.status(404).json({
          success: false,
          error: 'Order not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: order.toJSON()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get order',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getAllOrders(req: Request, res: Response): Promise<void> {
    try {
      const orders = await this.orderService.getAllOrders();

      res.status(200).json({
        success: true,
        data: orders.map(o => o.toJSON()),
        total: orders.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get orders',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getOrdersByCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const orders = await this.orderService.getOrdersByCustomerId(customerId);

      res.status(200).json({
        success: true,
        data: orders.map(o => o.toJSON()),
        total: orders.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get customer orders',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async updateOrderStatus(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const { status } = req.body;

      if (!status) {
        res.status(400).json({
          success: false,
          error: 'Status is required'
        });
        return;
      }

      const order = await this.orderService.updateOrderStatus(id, status as OrderStatus);

      if (!order) {
        res.status(404).json({
          success: false,
          error: 'Order not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: order.toJSON(),
        message: 'Order status updated successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to update order status',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async confirmOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await this.orderService.confirmOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          error: 'Order not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: order.toJSON(),
        message: 'Order confirmed successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to confirm order',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async cancelOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await this.orderService.cancelOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          error: 'Order not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: order.toJSON(),
        message: 'Order cancelled successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to cancel order',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async deleteOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await this.orderService.deleteOrder(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          error: 'Order not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        message: 'Order deleted successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to delete order',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
}
