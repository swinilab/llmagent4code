import { Request, Response } from 'express';
import { OrderService } from '../services/OrderService';
import Joi from 'joi';

const orderService = new OrderService();

const createOrderValidationSchema = Joi.object({
  customerId: Joi.string().uuid().required(),
  items: Joi.array().items(
    Joi.object({
      productId: Joi.string().uuid().required(),
      quantity: Joi.number().integer().positive().required(),
    })
  ).min(1).required(),
  shippingAddress: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zipCode: Joi.string().required(),
    country: Joi.string().required(),
  }).required(),
  notes: Joi.string().optional(),
});

export class OrderController {
  async getAllOrders(req: Request, res: Response): Promise<void> {
    try {
      const orders = await orderService.getAllOrders();
      res.json({
        success: true,
        data: orders,
        message: 'Orders retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve orders',
      });
    }
  }

  async getOrderById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.getOrderById(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve order',
      });
    }
  }

  async getOrdersByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const orders = await orderService.getOrdersByCustomerId(customerId);
      res.json({
        success: true,
        data: orders,
        message: 'Customer orders retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer orders',
      });
    }
  }

  async getOrdersByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['pending', 'accepted', 'invoiced', 'paid', 'shipped', 'completed', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const orders = await orderService.getOrdersByStatus(status);
      res.json({
        success: true,
        data: orders,
        message: `Orders with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve orders by status',
      });
    }
  }

  async createOrder(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createOrderValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const order = await orderService.createOrder(value);
      res.status(201).json({
        success: true,
        data: order,
        message: 'Order created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create order',
      });
    }
  }

  async updateOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const order = await orderService.updateOrder(updateData);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update order',
      });
    }
  }

  async acceptOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.acceptOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order accepted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to accept order',
      });
    }
  }

  async shipOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.shipOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order shipped successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to ship order',
      });
    }
  }

  async completeOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.completeOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to complete order',
      });
    }
  }

  async cancelOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.cancelOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel order',
      });
    }
  }

  async deleteOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await orderService.deleteOrder(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Order deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete order',
      });
    }
  }
}