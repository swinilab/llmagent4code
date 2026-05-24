interface IPayment {
  id: number;
  orderId: number;
  amount: number;
  date: string;
  status: "pending" | "completed";
  method: "credit_card" | "paypal" | "bank_transfer";
}

class Payment implements IPayment {
  constructor(
    public id: number,
    public orderId: number,
    public amount: number,
    public date: string,
    public status: "pending" | "completed",
    public method: "credit_card" | "paypal" | "bank_transfer"
  ) {}
}