// Customer Service Layer

import { Customer, CustomerData, BankingDetails, CustomerRole } from '../domain/customer/customer.entity';
import { MemoryRepository } from '../repository/memory-repository';

export class CustomerService {
  private repository: MemoryRepository<CustomerData>;

  constructor() {
    this.repository = new MemoryRepository<CustomerData>();
  }

  async createCustomer(name: string, email: string, address: string, phone: string, bankingDetails: BankingDetails, role: CustomerRole = 'guest'): Promise<Customer> {
    const customer = new Customer({
      name,
      email,
      address,
      phone,
      bankingDetails,
      role
    });
    const saved = await this.repository.create(customer.toJSON());
    return new Customer(saved);
  }

  async getCustomerById(id: string): Promise<Customer | null> {
    const data = await this.repository.findById(id);
    return data ? new Customer(data) : null;
  }

  async getAllCustomers(): Promise<Customer[]> {
    const data = await this.repository.findAll();
    return data.map(d => new Customer(d));
  }

  async updateCustomer(id: string, updates: Partial<{ name: string; email: string; address: string; phone: string; bankingDetails: BankingDetails; role: CustomerRole }>): Promise<Customer | null> {
    const existing = await this.repository.findById(id);
    if (!existing) return null;

    const customer = new Customer(existing);
    if (updates.name !== undefined) customer.name = updates.name;
    if (updates.email !== undefined) customer.email = updates.email;
    if (updates.address !== undefined) customer.address = updates.address;
    if (updates.phone !== undefined) customer.phone = updates.phone;
    if (updates.bankingDetails !== undefined) customer.bankingDetails = updates.bankingDetails;
    if (updates.role !== undefined) customer.role = updates.role;

    const updated = await this.repository.update(id, customer.toJSON());
    return updated ? new Customer(updated) : null;
  }

  async deleteCustomer(id: string): Promise<boolean> {
    return this.repository.delete(id);
  }

  async addOrderToHistory(customerId: string, orderId: string): Promise<Customer | null> {
    const existing = await this.repository.findById(customerId);
    if (!existing) return null;

    const customer = new Customer(existing);
    customer.addOrder(orderId);
    const updated = await this.repository.update(customerId, customer.toJSON());
    return updated ? new Customer(updated) : null;
  }

  async findByEmail(email: string): Promise<Customer | null> {
    const customers = await this.repository.findByQuery({ email } as Partial<CustomerData>);
    return customers.length > 0 ? new Customer(customers[0]) : null;
  }
}
