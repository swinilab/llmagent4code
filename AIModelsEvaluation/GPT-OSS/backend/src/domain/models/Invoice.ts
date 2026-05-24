import { Entity, PrimaryGeneratedColumn, Column, ManyToOne, CreateDateColumn, UpdateDateColumn } from "typeorm";
import { Order } from "./Order";
import { Payment } from "./Payment";

export enum InvoiceStatus {
  DRAFT = "DRAFT",
  ISSUED = "ISSUED",
  PAID = "PAID",
  CANCELLED = "CANCELLED",
}

@Entity()
export class Invoice {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @ManyToOne(() => Order, order => order.invoices, { eager: true })
  order!: Order;

  @Column('decimal', { precision: 10, scale: 2 })
  amount!: number;

  @Column()
  billingAddress!: string;

  @Column({
    type: "enum",
    enum: InvoiceStatus,
    default: InvoiceStatus.DRAFT
  })
  status!: InvoiceStatus;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;

  @OneToMany(() => Payment, payment => payment.invoice, { cascade: true })
  payments!: Payment[];
}