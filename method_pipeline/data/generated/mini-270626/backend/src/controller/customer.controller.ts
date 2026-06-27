// Customer Controller Layer

import { Request, Response } from 'express';
import { CustomerService } from '../service/customer.service';
import { BankingDetails, CustomerRole } from '../domain/customer/customer.entity';

export class CustomerController {
  private customerService: CustomerService;

  constructor(customerService: CustomerService) {
    this.customerService = customerService;
  }

  async createCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { name, email, address, phone, bankingDetails, role } = req.body;

      if (!name || !email || !address || !phone) {
        res.status(400).json({
          success: false,
          error: 'Missing required fields: name, email, address, phone'
        });
        return;
      }

      const banking: BankingDetails = bankingDetails || {
        accountNumber: '',
        bankName: '',
        routingNumber: ''
      };

      const customer = await this.customerService.createCustomer(
        name,
        email,
        address,
        phone,
        banking,
        role as CustomerRole || 'guest'
      );

      res.status(201).json({
        success: true,
        data: customer.toJSON(),
        message: 'Customer created successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to create customer',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getCustomerById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const customer = await this.customerService.getCustomerById(id);

      if (!customer) {
        res.status(404).json({
          success: false,
          error: 'Customer not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: customer.toJSON()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get customer',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getAllCustomers(req: Request, res: Response): Promise<void> {
    try {
      const customers = await this.customerService.getAllCustomers();

      res.status(200).json({
        success: true,
        data: customers.map(c => c.toJSON()),
        total: customers.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get customers',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async updateCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updates = req.body;

      const customer = await this.customerService.updateCustomer(id, updates);

      if (!customer) {
        res.status(404).json({
          success: false,
          error: 'Customer not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: customer.toJSON(),
        message: 'Customer updated successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to update customer',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async deleteCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await this.customerService.deleteCustomer(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          error: 'Customer not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        message: 'Customer deleted successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to delete customer',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
}
