import { DataTypes, Model } from 'sequelize';
import sequelize from '../config/database';
import { Invoice as IInvoice } from '../../../shared/domain/Invoice';
import Order from './Order';
import Customer from './Customer';

class Invoice extends Model<IInvoice> implements IInvoice {
  public id!: string;
  public orderId!: string;
  public customerId!: string;
  public customerName!: string;
  public customerEmail!: string;
  public invoiceNumber!: string;
  public lineItems!: Array<{
    description: string;
    quantity: number;
    unitPrice: number;
    totalPrice: number;
  }>;
  public subtotal!: number;
  public tax!: number;
  public total!: number;
  public status!: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  public issueDate!: Date;
  public dueDate!: Date;
  public paidDate!: Date;
  public billingAddress!: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  public notes!: string;
  public createdAt!: Date;
  public updatedAt!: Date;
}

Invoice.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    orderId: {
      type: DataTypes.UUID,
      allowNull: false,
      references: {
        model: Order,
        key: 'id',
      },
    },
    customerId: {
      type: DataTypes.UUID,
      allowNull: false,
      references: {
        model: Customer,
        key: 'id',
      },
    },
    customerName: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    customerEmail: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    invoiceNumber: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
    },
    lineItems: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    subtotal: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
    },
    tax: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
      defaultValue: 0,
    },
    total: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('draft', 'sent', 'paid', 'overdue', 'cancelled'),
      allowNull: false,
      defaultValue: 'draft',
    },
    issueDate: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
    dueDate: {
      type: DataTypes.DATE,
      allowNull: false,
    },
    paidDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    billingAddress: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    notes: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    createdAt: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
    updatedAt: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
  },
  {
    sequelize,
    modelName: 'Invoice',
    tableName: 'invoices',
    timestamps: true,
  }
);

export default Invoice;