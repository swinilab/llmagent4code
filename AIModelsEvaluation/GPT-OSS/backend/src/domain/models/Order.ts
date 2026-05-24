import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, OneToMany, CreateDateColumn, UpdateDateColumn } from "typeorm";
import { Customer } from "./Customer";
import { OrderItem } from "./OrderItem";
import { Invoice } from "./Invoice";

export enum OrderStatus {
  NEW = "NEW",
  ACCEPTED = "ACCEPTED",
  SHIPPED = "SHIPPED",
  CLOSED = "CLOSED",
}

@Entity()
export class Order {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @ManyToOne(() => Customer, customer => customer.orders, { eager: true })
  customer!: Customer;

  @OneToMany(() => OrderItem, item => item.order, { cascade: true })
  items!: OrderItem[];

  @Column('decimal', { precision: 10, scale: 2 })
  totalAmount!: number;

  @Column({
    type: "enum",
    enum: OrderStatus,
    default: OrderStatus.NEW
  })
  status!: OrderStatus;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;

  @Column({ nullable: true })
  invoiceId?: string;

  @OneToMany(() => Invoice, invoice => invoice.order, { cascade: true })
  invoices!: Invoice[];
}