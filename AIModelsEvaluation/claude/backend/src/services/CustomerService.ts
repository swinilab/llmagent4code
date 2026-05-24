import Customer from '../models/Customer';
import { Customer as ICustomer, CreateCustomerRequest, UpdateCustomerRequest } from '../../../shared/domain/Customer';

export class CustomerService {
  async getAllCustomers(): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to fetch customers: ${error}`);
    }
  }

  async getCustomerById(id: string): Promise<ICustomer | null> {
    try {
      const customer = await Customer.findByPk(id);
      return customer ? (customer.toJSON() as ICustomer) : null;
    } catch (error) {
      throw new Error(`Failed to fetch customer: ${error}`);
    }
  }

  async getCustomersByRole(role: 'customer' | 'order_staff' | 'accountant'): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        where: { role },
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to fetch customers by role: ${error}`);
    }
  }

  async createCustomer(customerData: CreateCustomerRequest): Promise<ICustomer> {
    try {
      const customer = await Customer.create(customerData as any);
      return customer.toJSON() as ICustomer;
    } catch (error) {
      throw new Error(`Failed to create customer: ${error}`);
    }
  }

  async updateCustomer(updateData: UpdateCustomerRequest): Promise<ICustomer | null> {
    try {
      const customer = await Customer.findByPk(updateData.id);
      if (!customer) {
        return null;
      }

      const updatedCustomer = await customer.update(updateData);
      return updatedCustomer.toJSON() as ICustomer;
    } catch (error) {
      throw new Error(`Failed to update customer: ${error}`);
    }
  }

  async deleteCustomer(id: string): Promise<boolean> {
    try {
      const result = await Customer.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete customer: ${error}`);
    }
  }

  async searchCustomers(searchTerm: string): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        where: {
          [require('sequelize').Op.or]: [
            { name: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { email: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { phone: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
          ],
        },
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to search customers: ${error}`);
    }
  }
}