// Customer service

import { Customer } from '../entities/customer.entity';

class CustomerService {
  private customers: Customer[] = [];

  async getCustomers(): Promise<Customer[]> {
    return this.customers;
  }

  async createCustomer(customer: Customer): Promise<Customer> {
    this.customers.push(customer);
    return customer;
  }

  async updateCustomer(id: number, customer: Customer): Promise<Customer> {
    const index = this.customers.findIndex((c) => c.id === id);
    if (index !== -1) {
      this.customers[index] = customer;
    }
    return customer;
  }

  async deleteCustomer(id: number): Promise<void> {
    this.customers = this.customers.filter((c) => c.id !== id);
  }
}

export { CustomerService };