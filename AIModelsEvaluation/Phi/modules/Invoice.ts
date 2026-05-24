interface IInvoice {
  id: number;
  orderId: number;
  amount: number;
  date: string;
  status: "issued" | "paid";
}

class Invoice implements IInvoice {
  constructor(
    public id: number,
    public orderId: number,
    public amount: number,
    public date: string,
    public status: "issued" | "paid"
  ) {}
}