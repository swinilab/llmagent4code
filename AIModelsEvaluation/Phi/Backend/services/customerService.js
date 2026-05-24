class CustomerService {
  constructor(customerModel) {
    this.customerModel = customerModel;
  }

  async createCustomer(data) {
    return await this.customerModel.create(data);
  }

  async getAllCustomers() {
    return await this.customerModel.findAll();
  }
}

module.exports = CustomerService;