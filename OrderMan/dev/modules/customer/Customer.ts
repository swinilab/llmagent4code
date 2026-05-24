export class Customer {
  id: number;
  name: string;
  address: string;
  phone: string;
  bankAccount?: string;
  createdAt: Date;
  updatedAt: Date;
  orders: number[];

  constructor(
    id: number,
    name: string,
    address: string,
    phone: string,
    bankAccount?: string,
    createdAt?: Date,
    updatedAt?: Date
  ) {
    this.id = id;
    this.name = name;
    this.address = address;
    this.phone = phone;
    this.bankAccount = bankAccount;
    this.createdAt = createdAt || new Date();
    this.updatedAt = updatedAt || new Date();
    this.orders = [];
  }
}

export default Customer;
