import { Request, Response } from 'express';
import { CustomerService } from '../services/CustomerService';
import Joi from 'joi';

const customerService = new CustomerService();

const customerValidationSchema = Joi.object({
  name: Joi.string().required().min(2).max(100),
  email: Joi.string().email().required(),
  phone: Joi.string().required().min(10).max(20),
  address: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zipCode: Joi.string().required(),
    country: Joi.string().required(),
  }).required(),
  bankingDetails: Joi.object({
    accountNumber: Joi.string().required(),
    routingNumber: Joi.string().required(),
    bankName: Joi.string().required(),
  }).required(),
  role: Joi.string().valid('customer', 'order_staff', 'accountant').default('customer'),
});

export class CustomerController {
  async getAllCustomers(req: Request, res: Response): Promise<void> {
    try {
      const customers = await customerService.getAllCustomers();
      res.json({
        success: true,
        data: customers,
        message: 'Customers retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customers',
      });
    }
  }

  async getCustomerById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const customer = await customerService.getCustomerById(id);

      if (!customer) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        data: customer,
        message: 'Customer retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer',
      });
    }
  }

  async getCustomersByRole(req: Request, res: Response): Promise<void> {
    try {
      const { role } = req.params;
      
      if (!['customer', 'order_staff', 'accountant'].includes(role)) {
        res.status(400).json({
          success: false,
          message: 'Invalid role specified',
        });
        return;
      }

      const customers = await customerService.getCustomersByRole(role as any);
      res.json({
        success: true,
        data: customers,
        message: `${role} customers retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customers by role',
      });
    }
  }

  async createCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = customerValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const customer = await customerService.createCustomer(value);
      res.status(201).json({
        success: true,
        data: customer,
        message: 'Customer created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create customer',
      });
    }
  }

  async updateCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const customer = await customerService.updateCustomer(updateData);

      if (!customer) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        data: customer,
        message: 'Customer updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update customer',
      });
    }
  }

  async deleteCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await customerService.deleteCustomer(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Customer deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete customer',
      });
    }
  }

  async searchCustomers(req: Request, res: Response): Promise<void> {
    try {
      const { q } = req.query;

      if (!q || typeof q !== 'string') {
        res.status(400).json({
          success: false,
          message: 'Search query parameter "q" is required',
        });
        return;
      }

      const customers = await customerService.searchCustomers(q);
      res.json({
        success: true,
        data: customers,
        message: 'Customer search completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to search customers',
      });
    }
  }
}