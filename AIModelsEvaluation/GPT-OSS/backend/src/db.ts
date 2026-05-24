import "reflect-metadata";
import { DataSource } from "typeorm";
import {
  Customer,
  Product,
  Order,
  OrderItem,
  Invoice,
  Payment,
} from "./domain";

export const AppDataSource = new DataSource({
  type: "sqlite",
  database: "order_mgmt.sqlite",
  synchronize: true, // In production use migrations
  logging: false,
  entities: [Customer, Product, Order, OrderItem, Invoice, Payment],
});