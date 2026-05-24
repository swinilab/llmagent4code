import { DataTypes, Model } from 'sequelize';
import sequelize from '../config/database';
import { Payment as IPayment } from '../../../shared/domain/Payment';
import Invoice from './Invoice';
import Order from './Order';
import Customer from './Customer';

class Payment extends Model<IPayment> implements IPayment {
  public id!: string;
  public invoiceId!: string;
  public orderId!: string;
  public customerId!: string;
  public amount!: number;
  public paymentMethod!: 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'paypal';
  public status!: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  public transactionId!: string;
  public paymentDate!: Date;
  public processedDate!: Date;
  public failureReason!: string;
  public paymentDetails!: {
    cardLast4?: string;
    bankAccount?: string;
    checkNumber?: string;
    paypalEmail?: string;
  };
  public createdAt!: Date;
  public updatedAt!: Date;
}

Payment.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    invoiceId: {
      type: DataTypes.UUID,
      allowNull: false,
      references: {
        model: Invoice,
        key: 'id',
      },
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
    amount: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: false,
    },
    paymentMethod: {
      type: DataTypes.ENUM('credit_card', 'bank_transfer', 'check', 'cash', 'paypal'),
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM('pending', 'processing', 'completed', 'failed', 'cancelled'),
      allowNull: false,
      defaultValue: 'pending',
    },
    transactionId: {
      type: DataTypes.STRING,
      allowNull: true,
    },
    paymentDate: {
      type: DataTypes.DATE,
      allowNull: false,
      defaultValue: DataTypes.NOW,
    },
    processedDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    failureReason: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    paymentDetails: {
      type: DataTypes.JSON,
      allowNull: false,
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
    modelName: 'Payment',
    tableName: 'payments',
    timestamps: true,
  }
);

export default Payment;