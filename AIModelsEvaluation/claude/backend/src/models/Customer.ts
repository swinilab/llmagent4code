import { DataTypes, Model } from "sequelize";
import sequelize from "../config/database";
import { Customer as ICustomer } from "../../../shared/domain/Customer";

class Customer extends Model<ICustomer> implements ICustomer {
  public id!: string;
  public name!: string;
  public email!: string;
  public phone!: string;
  public address!: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  public bankingDetails!: {
    accountNumber: string;
    routingNumber: string;
    bankName: string;
  };
  public role!: "customer" | "order_staff" | "accountant";
  public createdAt!: Date;
  public updatedAt!: Date;
}

Customer.init(
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    name: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    email: {
      type: DataTypes.STRING,
      allowNull: false,
      unique: true,
    },
    phone: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    address: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    bankingDetails: {
      type: DataTypes.JSON,
      allowNull: false,
    },
    role: {
      type: DataTypes.ENUM("customer", "order_staff", "accountant"),
      allowNull: false,
      defaultValue: "customer",
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
    modelName: "Customer",
    tableName: "customers",
    timestamps: true,
  }
);

export default Customer;
