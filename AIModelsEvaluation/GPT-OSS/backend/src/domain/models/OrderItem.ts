import { Entity, PrimaryGeneratedColumn, Column, ManyToOne } from "typeorm";
import { Order } from "./Order";
import { Product } from "./Product";

@Entity()
export class OrderItem {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column('int')
  quantity!: number;

  @Column('decimal', { precision: 10, scale: 2 })
  unitPrice!: number;

  @ManyToOne(() => Order, order => order.items, { onDelete: 'CASCADE' })
  order!: Order;

  @ManyToOne(() => Product, product => product.orderItems, { eager: true })
  product!: Product;
}