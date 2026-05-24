interface IAddress {
  street: string;
  city: string;
  postalCode: string;
  country: string;
}

interface ICustomer {
  uid: string;
  id: number;
  name: string;
  address: IAddress;
  phone: string;
  bankAccount: string;
  orders: Array<IOrder>;
  role: "admin" | "user";
}

class Customer implements ICustomer {
  constructor(
    public uid: string,
    public id: number,
    public name: string,
    public address: IAddress,
    public phone: string,
    public bankAccount: string,
    public orders: Array<IOrder>,
    public role: "admin" | "user"
  ) {}
}