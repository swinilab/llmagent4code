import { DataTypes, Model } from 'sequelize';
import sequelize from '../config/database';
import { Order as IOrder } from '../../../shared/domain/Order';
import Customer from './Customer';

class Order extends Model<IOrder> implements IOrder {
  public id!: string;
  public customerId!: string;
  public customerName!: string;
  public customerEmail!: string;
  public items!: Array<{
    productId: string;
    productName: string;
    quantity: number;
    unitPrice: number;
    totalPrice: number;
  }>;
  public subtotal!: number;
  public tax!: number;
  public shipping!: number;
  public total!: number;
  public status!: 'pending' | 'accepted' | 'invoiced' | 'paid' | 'shipped' | 'completed' | 'cancelled';
  public orderDate!: Date;
  public acceptedDate!: Date;
  public shippedDate!: Date;
  public completedDate!: Date;
  public invoiceId!: string;
  public shippingAddress!: {
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

Order.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
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
    items: {
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
    shipping: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
      defaultValue: 0,
    },
    total: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('pending', 'accepted', 'invoiced', 'paid', 'shipped', 'completed', 'cancelled'),
      allowNull: false,
      defaultValue: 'pending',
    },
    orderDate: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
    acceptedDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    shippedDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    completedDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    invoiceId: {
      type: DataTypes.UUID,
      allowNull: true,
    },
    shippingAddress: {
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
    modelName: 'Order',
    tableName: 'orders',
    timestamps: true,
  }
);

export default Order;