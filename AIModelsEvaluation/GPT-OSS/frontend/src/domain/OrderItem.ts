import { Product } from "./Product";

export interface OrderItem {
  id: string;
  quantity: number;
  unitPrice: number;
  product: Product;
}