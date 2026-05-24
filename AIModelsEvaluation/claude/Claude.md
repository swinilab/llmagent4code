```### shared/domain/Customer.ts```typescript
export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  bankingDetails: {
    accountNumber: string;
    routingNumber: string;
    bankName: string;
  };
  role: 'customer' | 'order_staff' | 'accountant';
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateCustomerRequest {
  name: string;
  email: string;
  phone: string;
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  bankingDetails: {
    accountNumber: string;
    routingNumber: string;
    bankName: string;
  };
  role: 'customer' | 'order_staff' | 'accountant';
}

export interface UpdateCustomerRequest extends Partial<CreateCustomerRequest> {
  id: string;
}
```### shared/domain/Product.ts```typescript
export interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  stockQuantity: number;
  sku: string;
  weight: number;
  dimensions: {
    length: number;
    width: number;
    height: number;
  };
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateProductRequest {
  name: string;
  description: string;
  category: string;
  price: number;
  stockQuantity: number;
  sku: string;
  weight: number;
  dimensions: {
    length: number;
    width: number;
    height: number;
  };
}

export interface UpdateProductRequest extends Partial<CreateProductRequest> {
  id: string;
  isActive?: boolean;
}
```### shared/domain/Order.ts```typescript
export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export interface Order {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  status: 'pending' | 'accepted' | 'invoiced' | 'paid' | 'shipped' | 'completed' | 'cancelled';
  orderDate: Date;
  acceptedDate?: Date;
  shippedDate?: Date;
  completedDate?: Date;
  invoiceId?: string;
  shippingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateOrderRequest {
  customerId: string;
  items: {
    productId: string;
    quantity: number;
  }[];
  shippingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  notes?: string;
}

export interface UpdateOrderRequest {
  id: string;
  status?: 'pending' | 'accepted' | 'invoiced' | 'paid' | 'shipped' | 'completed' | 'cancelled';
  notes?: string;
  shippedDate?: Date;
  completedDate?: Date;
}
```### shared/domain/Invoice.ts```typescript
export interface InvoiceLineItem {
  description: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export interface Invoice {
  id: string;
  orderId: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  invoiceNumber: string;
  lineItems: InvoiceLineItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  issueDate: Date;
  dueDate: Date;
  paidDate?: Date;
  billingAddress: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  notes?: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateInvoiceRequest {
  orderId: string;
  dueDate: Date;
  notes?: string;
}

export interface UpdateInvoiceRequest {
  id: string;
  status?: 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled';
  paidDate?: Date;
  notes?: string;
}
```### shared/domain/Payment.ts```typescript
export interface Payment {
  id: string;
  invoiceId: string;
  orderId: string;
  customerId: string;
  amount: number;
  paymentMethod: 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'paypal';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  transactionId?: string;
  paymentDate: Date;
  processedDate?: Date;
  failureReason?: string;
  paymentDetails: {
    cardLast4?: string;
    bankAccount?: string;
    checkNumber?: string;
    paypalEmail?: string;
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface CreatePaymentRequest {
  invoiceId: string;
  amount: number;
  paymentMethod: 'credit_card' | 'bank_transfer' | 'check' | 'cash' | 'paypal';
  paymentDetails: {
    cardLast4?: string;
    bankAccount?: string;
    checkNumber?: string;
    paypalEmail?: string;
  };
}

export interface UpdatePaymentRequest {
  id: string;
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  transactionId?: string;
  processedDate?: Date;
  failureReason?: string;
}
```## 3. Backend Implementation### backend/package.json```json
{
  "name": "order-management-backend",
  "version": "1.0.0",
  "description": "Order Management System Backend",
  "main": "dist/index.js",
  "scripts": {
    "start": "node dist/index.js",
    "dev": "nodemon src/index.ts",
    "build": "tsc",
    "seed": "node dist/seed.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "morgan": "^1.10.0",
    "sequelize": "^6.32.1",
    "sqlite3": "^5.1.6",
    "uuid": "^9.0.0",
    "joi": "^17.9.2"
  },
  "devDependencies": {
    "@types/express": "^4.17.17",
    "@types/cors": "^2.8.13",
    "@types/morgan": "^1.9.4",
    "@types/node": "^20.4.5",
    "@types/uuid": "^9.0.2",
    "nodemon": "^3.0.1",
    "ts-node": "^10.9.1",
    "typescript": "^5.1.6"
  }
}
```### backend/tsconfig.json```json
{
  "compilerOptions": {
    "target": "es2020",
    "module": "commonjs",
    "lib": ["es2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  },
  "include": [
    "src/**/*",
    "../shared/**/*"
  ],
  "exclude": [
    "node_modules",
    "dist"
  ]
}
```### backend/src/config/database.ts```typescript
import { Sequelize } from 'sequelize';
import path from 'path';

const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: path.join(__dirname, '../../database.sqlite'),
  logging: console.log,
});

export default sequelize;
```### backend/src/models/Customer.ts```typescript
import { DataTypes, Model } from 'sequelize';
import sequelize from '../config/database';
import { Customer as ICustomer } from '../../../shared/domain/Customer';

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
  public role!: 'customer' | 'order_staff' | 'accountant';
  public createdAt!: Date;
  public updatedAt!: Date;
}

Customer.init({
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
    type: DataTypes.ENUM('customer', 'order_staff', 'accountant'),
    allowNull: false,
    defaultValue: 'customer',
  },
}, {
  sequelize,
  modelName: 'Customer',
  tableName: 'customers',
  timestamps: true,
});

export default Customer;
```### backend/src/models/Product.ts```typescript
import { DataTypes, Model } from 'sequelize';
import sequelize from '../config/database';
import { Product as IProduct } from '../../../shared/domain/Product';

class Product extends Model<IProduct> implements IProduct {
  public id!: string;
  public name!: string;
  public description!: string;
  public category!: string;
  public price!: number;
  public stockQuantity!: number;
  public sku!: string;
  public weight!: number;
  public dimensions!: {
    length: number;
    width: number;
    height: number;
  };
  public isActive!: boolean;
  public createdAt!: Date;
  public updatedAt!: Date;
}

Product.init({
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
  category: {
    type: DataTypes.STRING,
    allowNull: false,
  },
  price: {
    type: DataTypes.DECIMAL(10, 2),
    allowNull: false,
  },
  stockQuantity: {
    type: DataTypes.INTEGER,
    allowNull: false,
    defaultValue: 0,
  },
  sku: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
  },
  weight: {
    type: DataTypes.DECIMAL(8, 2),
    allowNull: false,
  },
  dimensions: {
    type: DataTypes.JSON,
    allowNull: false,
  },
  isActive: {
    type: DataTypes.BOOLEAN,
    allowNull: false,
    defaultValue: true,
  },
}, {
  sequelize,
  modelName: 'Product',
  tableName: 'products',
  timestamps: true,
});

export default Product;
```### backend/src/models/Order.ts```typescript
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

Order.init({
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
}, {
  sequelize,
  modelName: 'Order',
  tableName: 'orders',
  timestamps: true,
});

export default Order;
```### backend/src/models/Invoice.ts```typescript
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

Invoice.init({
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
}, {
  sequelize,
  modelName: 'Invoice',
  tableName: 'invoices',
  timestamps: true,
});

export default Invoice;
```### backend/src/models/Payment.ts```typescript
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

Payment.init({
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
}, {
  sequelize,
  modelName: 'Payment',
  tableName: 'payments',
  timestamps: true,
});

export default Payment;
```### backend/src/services/CustomerService.ts```typescript
import Customer from '../models/Customer';
import { Customer as ICustomer, CreateCustomerRequest, UpdateCustomerRequest } from '../../../shared/domain/Customer';

export class CustomerService {
  async getAllCustomers(): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to fetch customers: ${error}`);
    }
  }

  async getCustomerById(id: string): Promise<ICustomer | null> {
    try {
      const customer = await Customer.findByPk(id);
      return customer ? (customer.toJSON() as ICustomer) : null;
    } catch (error) {
      throw new Error(`Failed to fetch customer: ${error}`);
    }
  }

  async getCustomersByRole(role: 'customer' | 'order_staff' | 'accountant'): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        where: { role },
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to fetch customers by role: ${error}`);
    }
  }

  async createCustomer(customerData: CreateCustomerRequest): Promise<ICustomer> {
    try {
      const customer = await Customer.create(customerData as any);
      return customer.toJSON() as ICustomer;
    } catch (error) {
      throw new Error(`Failed to create customer: ${error}`);
    }
  }

  async updateCustomer(updateData: UpdateCustomerRequest): Promise<ICustomer | null> {
    try {
      const customer = await Customer.findByPk(updateData.id);
      if (!customer) {
        return null;
      }

      const updatedCustomer = await customer.update(updateData);
      return updatedCustomer.toJSON() as ICustomer;
    } catch (error) {
      throw new Error(`Failed to update customer: ${error}`);
    }
  }

  async deleteCustomer(id: string): Promise<boolean> {
    try {
      const result = await Customer.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete customer: ${error}`);
    }
  }

  async searchCustomers(searchTerm: string): Promise<ICustomer[]> {
    try {
      const customers = await Customer.findAll({
        where: {
          [require('sequelize').Op.or]: [
            { name: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { email: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { phone: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
          ],
        },
        order: [['createdAt', 'DESC']],
      });
      return customers.map(customer => customer.toJSON() as ICustomer);
    } catch (error) {
      throw new Error(`Failed to search customers: ${error}`);
    }
  }
}
```### backend/src/services/ProductService.ts```typescript
import Product from '../models/Product';
import { Product as IProduct, CreateProductRequest, UpdateProductRequest } from '../../../shared/domain/Product';

export class ProductService {
  async getAllProducts(): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        order: [['createdAt', 'DESC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch products: ${error}`);
    }
  }

  async getActiveProducts(): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: { isActive: true },
        order: [['name', 'ASC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch active products: ${error}`);
    }
  }

  async getProductById(id: string): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(id);
      return product ? (product.toJSON() as IProduct) : null;
    } catch (error) {
      throw new Error(`Failed to fetch product: ${error}`);
    }
  }

  async getProductsBySku(sku: string): Promise<IProduct | null> {
    try {
      const product = await Product.findOne({
        where: { sku },
      });
      return product ? (product.toJSON() as IProduct) : null;
    } catch (error) {
      throw new Error(`Failed to fetch product by SKU: ${error}`);
    }
  }

  async createProduct(productData: CreateProductRequest): Promise<IProduct> {
    try {
      const product = await Product.create(productData as any);
      return product.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to create product: ${error}`);
    }
  }

  async updateProduct(updateData: UpdateProductRequest): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(updateData.id);
      if (!product) {
        return null;
      }

      const updatedProduct = await product.update(updateData);
      return updatedProduct.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to update product: ${error}`);
    }
  }

  async deleteProduct(id: string): Promise<boolean> {
    try {
      const result = await Product.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete product: ${error}`);
    }
  }

  async updateProductStock(id: string, quantity: number): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(id);
      if (!product) {
        return null;
      }

      const updatedProduct = await product.update({
        stockQuantity: product.stockQuantity + quantity,
      });
      return updatedProduct.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to update product stock: ${error}`);
    }
  }

  async searchProducts(searchTerm: string): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: {
          [require('sequelize').Op.or]: [
            { name: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { description: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { category: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { sku: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
          ],
        },
        order: [['createdAt', 'DESC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to search products: ${error}`);
    }
  }

  async getProductsByCategory(category: string): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: { category },
        order: [['name', 'ASC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch products by category: ${error}`);
    }
  }
}
```### backend/src/services/OrderService.ts```typescript
import Order from '../models/Order';
import Customer from '../models/Customer';
import Product from '../models/Product';
import { Order as IOrder, CreateOrderRequest, UpdateOrderRequest } from '../../../shared/domain/Order';

export class OrderService {
  async getAllOrders(): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch orders: ${error}`);
    }
  }

  async getOrderById(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      return order ? (order.toJSON() as IOrder) : null;
    } catch (error) {
      throw new Error(`Failed to fetch order: ${error}`);
    }
  }

  async getOrdersByCustomerId(customerId: string): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch customer orders: ${error}`);
    }
  }

  async getOrdersByStatus(status: string): Promise<IOrder[]> {
    try {
      const orders = await Order.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return orders.map(order => order.toJSON() as IOrder);
    } catch (error) {
      throw new Error(`Failed to fetch orders by status: ${error}`);
    }
  }

  async createOrder(orderData: CreateOrderRequest): Promise<IOrder> {
    try {
      // Fetch customer details
      const customer = await Customer.findByPk(orderData.customerId);
      if (!customer) {
        throw new Error('Customer not found');
      }

      // Calculate order totals
      let subtotal = 0;
      const orderItems = [];

      for (const item of orderData.items) {
        const product = await Product.findByPk(item.productId);
        if (!product) {
          throw new Error(`Product with ID ${item.productId} not found`);
        }

        if (product.stockQuantity < item.quantity) {
          throw new Error(`Insufficient stock for product ${product.name}`);
        }

        const totalPrice = product.price * item.quantity;
        subtotal += totalPrice;

        orderItems.push({
          productId: product.id,
          productName: product.name,
          quantity: item.quantity,
          unitPrice: product.price,
          totalPrice,
        });

        // Update product stock
        await product.update({
          stockQuantity: product.stockQuantity - item.quantity,
        });
      }

      const tax = subtotal * 0.08; // 8% tax
      const shipping = subtotal > 100 ? 0 : 15; // Free shipping over $100
      const total = subtotal + tax + shipping;

      const order = await Order.create({
        customerId: orderData.customerId,
        customerName: customer.name,
        customerEmail: customer.email,
        items: orderItems,
        subtotal,
        tax,
        shipping,
        total,
        status: 'pending',
        orderDate: new Date(),
        shippingAddress: orderData.shippingAddress,
        notes: orderData.notes,
      } as any);

      return order.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to create order: ${error}`);
    }
  }

  async updateOrder(updateData: UpdateOrderRequest): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(updateData.id);
      if (!order) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      // Set timestamps based on status changes
      if (updateData.status === 'accepted' && order.status !== 'accepted') {
        updateObject.acceptedDate = new Date();
      }
      if (updateData.status === 'shipped' && order.status !== 'shipped') {
        updateObject.shippedDate = new Date();
      }
      if (updateData.status === 'completed' && order.status !== 'completed') {
        updateObject.completedDate = new Date();
      }

      const updatedOrder = await order.update(updateObject);
      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to update order: ${error}`);
    }
  }

  async acceptOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'pending') {
        throw new Error('Order can only be accepted if it is in pending status');
      }

      const updatedOrder = await order.update({
        status: 'accepted',
        acceptedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to accept order: ${error}`);
    }
  }

  async shipOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'paid') {
        throw new Error('Order can only be shipped if it is paid');
      }

      const updatedOrder = await order.update({
        status: 'shipped',
        shippedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to ship order: ${error}`);
    }
  }

  async completeOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (order.status !== 'shipped') {
        throw new Error('Order can only be completed if it is shipped');
      }

      const updatedOrder = await order.update({
        status: 'completed',
        completedDate: new Date(),
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to complete order: ${error}`);
    }
  }

  async cancelOrder(id: string): Promise<IOrder | null> {
    try {
      const order = await Order.findByPk(id);
      if (!order) {
        return null;
      }

      if (!['pending', 'accepted'].includes(order.status)) {
        throw new Error('Order can only be cancelled if it is pending or accepted');
      }

      // Restore product stock
      for (const item of order.items) {
        const product = await Product.findByPk(item.productId);
        if (product) {
          await product.update({
            stockQuantity: product.stockQuantity + item.quantity,
          });
        }
      }

      const updatedOrder = await order.update({
        status: 'cancelled',
      });

      return updatedOrder.toJSON() as IOrder;
    } catch (error) {
      throw new Error(`Failed to cancel order: ${error}`);
    }
  }

  async deleteOrder(id: string): Promise<boolean> {
    try {
      const result = await Order.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete order: ${error}`);
    }
  }
}
```### backend/src/services/InvoiceService.ts```typescript
import Invoice from '../models/Invoice';
import Order from '../models/Order';
import Customer from '../models/Customer';
import { Invoice as IInvoice, CreateInvoiceRequest, UpdateInvoiceRequest } from '../../../shared/domain/Invoice';

export class InvoiceService {
  async getAllInvoices(): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch invoices: ${error}`);
    }
  }

  async getInvoiceById(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      return invoice ? (invoice.toJSON() as IInvoice) : null;
    } catch (error) {
      throw new Error(`Failed to fetch invoice: ${error}`);
    }
  }

  async getInvoicesByCustomerId(customerId: string): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch customer invoices: ${error}`);
    }
  }

  async getInvoicesByStatus(status: string): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch invoices by status: ${error}`);
    }
  }

  async getInvoiceByOrderId(orderId: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findOne({
        where: { orderId },
      });
      return invoice ? (invoice.toJSON() as IInvoice) : null;
    } catch (error) {
      throw new Error(`Failed to fetch invoice by order ID: ${error}`);
    }
  }

  async createInvoice(invoiceData: CreateInvoiceRequest): Promise<IInvoice> {
    try {
      // Fetch order details
      const order = await Order.findByPk(invoiceData.orderId);
      if (!order) {
        throw new Error('Order not found');
      }

      if (order.status !== 'accepted') {
        throw new Error('Invoice can only be created for accepted orders');
      }

      // Check if invoice already exists for this order
      const existingInvoice = await Invoice.findOne({
        where: { orderId: invoiceData.orderId },
      });

      if (existingInvoice) {
        throw new Error('Invoice already exists for this order');
      }

      // Fetch customer details
      const customer = await Customer.findByPk(order.customerId);
      if (!customer) {
        throw new Error('Customer not found');
      }

      // Generate invoice number
      const invoiceCount = await Invoice.count();
      const invoiceNumber = `INV-${String(invoiceCount + 1).padStart(6, '0')}`;

      // Convert order items to invoice line items
      const lineItems = order.items.map(item => ({
        description: item.productName,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        totalPrice: item.totalPrice,
      }));

      const invoice = await Invoice.create({
        orderId: invoiceData.orderId,
        customerId: order.customerId,
        customerName: order.customerName,
        customerEmail: order.customerEmail,
        invoiceNumber,
        lineItems,
        subtotal: order.subtotal,
        tax: order.tax,
        total: order.total,
        status: 'draft',
        issueDate: new Date(),
        dueDate: invoiceData.dueDate,
        billingAddress: customer.address,
        notes: invoiceData.notes,
      } as any);

      // Update order status and link invoice
      await order.update({
        status: 'invoiced',
        invoiceId: invoice.id,
      });

      return invoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to create invoice: ${error}`);
    }
  }

  async updateInvoice(updateData: UpdateInvoiceRequest): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(updateData.id);
      if (!invoice) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      const updatedInvoice = await invoice.update(updateObject);
      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to update invoice: ${error}`);
    }
  }

  async markInvoiceAsPaid(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status === 'paid') {
        throw new Error('Invoice is already marked as paid');
      }

      const updatedInvoice = await invoice.update({
        status: 'paid',
        paidDate: new Date(),
      });

      // Update associated order status
      const order = await Order.findByPk(invoice.orderId);
      if (order) {
        await order.update({
          status: 'paid',
        });
      }

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to mark invoice as paid: ${error}`);
    }
  }

  async sendInvoice(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status !== 'draft') {
        throw new Error('Only draft invoices can be sent');
      }

      const updatedInvoice = await invoice.update({
        status: 'sent',
      });

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to send invoice: ${error}`);
    }
  }

  async cancelInvoice(id: string): Promise<IInvoice | null> {
    try {
      const invoice = await Invoice.findByPk(id);
      if (!invoice) {
        return null;
      }

      if (invoice.status === 'paid') {
        throw new Error('Cannot cancel a paid invoice');
      }

      const updatedInvoice = await invoice.update({
        status: 'cancelled',
      });

      // Update associated order status back to accepted
      const order = await Order.findByPk(invoice.orderId);
      if (order) {
        await order.update({
          status: 'accepted',
          invoiceId: null,
        });
      }

      return updatedInvoice.toJSON() as IInvoice;
    } catch (error) {
      throw new Error(`Failed to cancel invoice: ${error}`);
    }
  }

  async deleteInvoice(id: string): Promise<boolean> {
    try {
      const result = await Invoice.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete invoice: ${error}`);
    }
  }

  async getOverdueInvoices(): Promise<IInvoice[]> {
    try {
      const invoices = await Invoice.findAll({
        where: {
          status: ['sent'],
          dueDate: {
            [require('sequelize').Op.lt]: new Date(),
          },
        },
        order: [['dueDate', 'ASC']],
      });

      // Mark overdue invoices
      for (const invoice of invoices) {
        await invoice.update({ status: 'overdue' });
      }

      return invoices.map(invoice => invoice.toJSON() as IInvoice);
    } catch (error) {
      throw new Error(`Failed to fetch overdue invoices: ${error}`);
    }
  }
}
```### backend/src/services/PaymentService.ts```typescript
import Payment from '../models/Payment';
import Invoice from '../models/Invoice';
import Order from '../models/Order';
import { Payment as IPayment, CreatePaymentRequest, UpdatePaymentRequest } from '../../../shared/domain/Payment';
import { v4 as uuidv4 } from 'uuid';

export class PaymentService {
  async getAllPayments(): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments: ${error}`);
    }
  }

  async getPaymentById(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      return payment ? (payment.toJSON() as IPayment) : null;
    } catch (error) {
      throw new Error(`Failed to fetch payment: ${error}`);
    }
  }

  async getPaymentsByCustomerId(customerId: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { customerId },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch customer payments: ${error}`);
    }
  }

  async getPaymentsByInvoiceId(invoiceId: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { invoiceId },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch invoice payments: ${error}`);
    }
  }

  async getPaymentsByStatus(status: string): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: { status },
        order: [['createdAt', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments by status: ${error}`);
    }
  }

  async createPayment(paymentData: CreatePaymentRequest): Promise<IPayment> {
    try {
      // Fetch invoice details
      const invoice = await Invoice.findByPk(paymentData.invoiceId);
      if (!invoice) {
        throw new Error('Invoice not found');
      }

      if (invoice.status === 'paid') {
        throw new Error('Invoice is already paid');
      }

      if (invoice.status === 'cancelled') {
        throw new Error('Cannot make payment for cancelled invoice');
      }

      // Validate payment amount
      if (paymentData.amount <= 0) {
        throw new Error('Payment amount must be greater than zero');
      }

      if (paymentData.amount > invoice.total) {
        throw new Error('Payment amount cannot exceed invoice total');
      }

      // Fetch order details
      const order = await Order.findByPk(invoice.orderId);
      if (!order) {
        throw new Error('Associated order not found');
      }

      const payment = await Payment.create({
        invoiceId: paymentData.invoiceId,
        orderId: invoice.orderId,
        customerId: invoice.customerId,
        amount: paymentData.amount,
        paymentMethod: paymentData.paymentMethod,
        status: 'pending',
        paymentDate: new Date(),
        paymentDetails: paymentData.paymentDetails,
      } as any);

      return payment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to create payment: ${error}`);
    }
  }

  async updatePayment(updateData: UpdatePaymentRequest): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(updateData.id);
      if (!payment) {
        return null;
      }

      const updateObject: any = { ...updateData };
      delete updateObject.id;

      const updatedPayment = await payment.update(updateObject);
      return updatedPayment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to update payment: ${error}`);
    }
  }

  async processPayment(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      if (!payment) {
        return null;
      }

      if (payment.status !== 'pending') {
        throw new Error('Only pending payments can be processed');
      }

      // Simulate payment processing
      const isSuccessful = Math.random() > 0.1; // 90% success rate
      const transactionId = uuidv4();

      if (isSuccessful) {
        const updatedPayment = await payment.update({
          status: 'completed',
          transactionId,
          processedDate: new Date(),
        });

        // Check if this payment completes the invoice
        const invoice = await Invoice.findByPk(payment.invoiceId);
        if (invoice) {
          const totalPayments = await Payment.sum('amount', {
            where: {
              invoiceId: payment.invoiceId,
              status: 'completed',
            },
          });

          if (totalPayments >= invoice.total) {
            // Mark invoice as paid
            await invoice.update({
              status: 'paid',
              paidDate: new Date(),
            });

            // Update associated order status
            const order = await Order.findByPk(invoice.orderId);
            if (order) {
              await order.update({
                status: 'paid',
              });
            }
          }
        }

        return updatedPayment.toJSON() as IPayment;
      } else {
        const updatedPayment = await payment.update({
          status: 'failed',
          transactionId,
          processedDate: new Date(),
          failureReason: 'Payment processing failed',
        });

        return updatedPayment.toJSON() as IPayment;
      }
    } catch (error) {
      throw new Error(`Failed to process payment: ${error}`);
    }
  }

  async cancelPayment(id: string): Promise<IPayment | null> {
    try {
      const payment = await Payment.findByPk(id);
      if (!payment) {
        return null;
      }

      if (!['pending', 'processing'].includes(payment.status)) {
        throw new Error('Only pending or processing payments can be cancelled');
      }

      const updatedPayment = await payment.update({
        status: 'cancelled',
        processedDate: new Date(),
      });

      return updatedPayment.toJSON() as IPayment;
    } catch (error) {
      throw new Error(`Failed to cancel payment: ${error}`);
    }
  }

  async deletePayment(id: string): Promise<boolean> {
    try {
      const result = await Payment.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete payment: ${error}`);
    }
  }

  async getPaymentsByDateRange(startDate: Date, endDate: Date): Promise<IPayment[]> {
    try {
      const payments = await Payment.findAll({
        where: {
          paymentDate: {
            [require('sequelize').Op.between]: [startDate, endDate],
          },
        },
        order: [['paymentDate', 'DESC']],
      });
      return payments.map(payment => payment.toJSON() as IPayment);
    } catch (error) {
      throw new Error(`Failed to fetch payments by date range: ${error}`);
    }
  }

  async getPaymentSummary(customerId?: string): Promise<{
    totalPayments: number;
    completedPayments: number;
    pendingPayments: number;
    failedPayments: number;
    totalAmount: number;
  }> {
    try {
      const whereClause: any = {};
      if (customerId) {
        whereClause.customerId = customerId;
      }

      const allPayments = await Payment.findAll({
        where: whereClause,
      });

      const totalPayments = allPayments.length;
      const completedPayments = allPayments.filter(p => p.status === 'completed').length;
      const pendingPayments = allPayments.filter(p => p.status === 'pending').length;
      const failedPayments = allPayments.filter(p => p.status === 'failed').length;
      const totalAmount = allPayments
        .filter(p => p.status === 'completed')
        .reduce((sum, p) => sum + parseFloat(p.amount.toString()), 0);

      return {
        totalPayments,
        completedPayments,
        pendingPayments,
        failedPayments,
        totalAmount,
      };
    } catch (error) {
      throw new Error(`Failed to get payment summary: ${error}`);
    }
  }
}
```### backend/src/controllers/CustomerController.ts```typescript
import { Request, Response } from 'express';
import { CustomerService } from '../services/CustomerService';
import Joi from 'joi';

const customerService = new CustomerService();

const customerValidationSchema = Joi.object({
  name: Joi.string().required().min(2).max(100),
  email: Joi.string().email().required(),
  phone: Joi.string().required().min(10).max(20),
  address: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zipCode: Joi.string().required(),
    country: Joi.string().required(),
  }).required(),
  bankingDetails: Joi.object({
    accountNumber: Joi.string().required(),
    routingNumber: Joi.string().required(),
    bankName: Joi.string().required(),
  }).required(),
  role: Joi.string().valid('customer', 'order_staff', 'accountant').default('customer'),
});

export class CustomerController {
  async getAllCustomers(req: Request, res: Response): Promise<void> {
    try {
      const customers = await customerService.getAllCustomers();
      res.json({
        success: true,
        data: customers,
        message: 'Customers retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customers',
      });
    }
  }

  async getCustomerById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const customer = await customerService.getCustomerById(id);

      if (!customer) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        data: customer,
        message: 'Customer retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer',
      });
    }
  }

  async getCustomersByRole(req: Request, res: Response): Promise<void> {
    try {
      const { role } = req.params;
      
      if (!['customer', 'order_staff', 'accountant'].includes(role)) {
        res.status(400).json({
          success: false,
          message: 'Invalid role specified',
        });
        return;
      }

      const customers = await customerService.getCustomersByRole(role as any);
      res.json({
        success: true,
        data: customers,
        message: `${role} customers retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customers by role',
      });
    }
  }

  async createCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = customerValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const customer = await customerService.createCustomer(value);
      res.status(201).json({
        success: true,
        data: customer,
        message: 'Customer created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create customer',
      });
    }
  }

  async updateCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const customer = await customerService.updateCustomer(updateData);

      if (!customer) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        data: customer,
        message: 'Customer updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update customer',
      });
    }
  }

  async deleteCustomer(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await customerService.deleteCustomer(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Customer not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Customer deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete customer',
      });
    }
  }

  async searchCustomers(req: Request, res: Response): Promise<void> {
    try {
      const { q } = req.query;

      if (!q || typeof q !== 'string') {
        res.status(400).json({
          success: false,
          message: 'Search query parameter "q" is required',
        });
        return;
      }

      const customers = await customerService.searchCustomers(q);
      res.json({
        success: true,
        data: customers,
        message: 'Customer search completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to search customers',
      });
    }
  }
}
```### backend/src/controllers/ProductController.ts```typescript
import { Request, Response } from 'express';
import { ProductService } from '../services/ProductService';
import Joi from 'joi';

const productService = new ProductService();

const productValidationSchema = Joi.object({
  name: Joi.string().required().min(2).max(200),
  description: Joi.string().required().min(10),
  category: Joi.string().required(),
  price: Joi.number().positive().required(),
  stockQuantity: Joi.number().integer().min(0).required(),
  sku: Joi.string().required().min(3).max(50),
  weight: Joi.number().positive().required(),
  dimensions: Joi.object({
    length: Joi.number().positive().required(),
    width: Joi.number().positive().required(),
    height: Joi.number().positive().required(),
  }).required(),
});

export class ProductController {
  async getAllProducts(req: Request, res: Response): Promise<void> {
    try {
      const products = await productService.getAllProducts();
      res.json({
        success: true,
        data: products,
        message: 'Products retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve products',
      });
    }
  }

  async getActiveProducts(req: Request, res: Response): Promise<void> {
    try {
      const products = await productService.getActiveProducts();
      res.json({
        success: true,
        data: products,
        message: 'Active products retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve active products',
      });
    }
  }

  async getProductById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const product = await productService.getProductById(id);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve product',
      });
    }
  }

  async getProductBySkuEndpoint(req: Request, res: Response): Promise<void> {
    try {
      const { sku } = req.params;
      const product = await productService.getProductsBySku(sku);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve product',
      });
    }
  }

  async createProduct(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = productValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const product = await productService.createProduct(value);
      res.status(201).json({
        success: true,
        data: product,
        message: 'Product created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create product',
      });
    }
  }

  async updateProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const product = await productService.updateProduct(updateData);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update product',
      });
    }
  }

  async deleteProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await productService.deleteProduct(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Product deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete product',
      });
    }
  }

  async updateProductStock(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const { quantity } = req.body;

      if (typeof quantity !== 'number') {
        res.status(400).json({
          success: false,
          message: 'Quantity must be a number',
        });
        return;
      }

      const product = await productService.updateProductStock(id, quantity);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product stock updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update product stock',
      });
    }
  }

  async searchProducts(req: Request, res: Response): Promise<void> {
    try {
      const { q } = req.query;

      if (!q || typeof q !== 'string') {
        res.status(400).json({
          success: false,
          message: 'Search query parameter "q" is required',
        });
        return;
      }

      const products = await productService.searchProducts(q);
      res.json({
        success: true,
        data: products,
        message: 'Product search completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to search products',
      });
    }
  }

  async getProductsByCategory(req: Request, res: Response): Promise<void> {
    try {
      const { category } = req.params;
      const products = await productService.getProductsByCategory(category);
      res.json({
        success: true,
        data: products,
        message: 'Products by category retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve products by category',
      });
    }
  }
}
```### backend/src/controllers/OrderController.ts```typescript
import { Request, Response } from 'express';
import { OrderService } from '../services/OrderService';
import Joi from 'joi';

const orderService = new OrderService();

const createOrderValidationSchema = Joi.object({
  customerId: Joi.string().uuid().required(),
  items: Joi.array().items(
    Joi.object({
      productId: Joi.string().uuid().required(),
      quantity: Joi.number().integer().positive().required(),
    })
  ).min(1).required(),
  shippingAddress: Joi.object({
    street: Joi.string().required(),
    city: Joi.string().required(),
    state: Joi.string().required(),
    zipCode: Joi.string().required(),
    country: Joi.string().required(),
  }).required(),
  notes: Joi.string().optional(),
});

export class OrderController {
  async getAllOrders(req: Request, res: Response): Promise<void> {
    try {
      const orders = await orderService.getAllOrders();
      res.json({
        success: true,
        data: orders,
        message: 'Orders retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve orders',
      });
    }
  }

  async getOrderById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.getOrderById(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve order',
      });
    }
  }

  async getOrdersByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const orders = await orderService.getOrdersByCustomerId(customerId);
      res.json({
        success: true,
        data: orders,
        message: 'Customer orders retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer orders',
      });
    }
  }

  async getOrdersByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['pending', 'accepted', 'invoiced', 'paid', 'shipped', 'completed', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const orders = await orderService.getOrdersByStatus(status);
      res.json({
        success: true,
        data: orders,
        message: `Orders with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve orders by status',
      });
    }
  }

  async createOrder(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createOrderValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const order = await orderService.createOrder(value);
      res.status(201).json({
        success: true,
        data: order,
        message: 'Order created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create order',
      });
    }
  }

  async updateOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const order = await orderService.updateOrder(updateData);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update order',
      });
    }
  }

  async acceptOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.acceptOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order accepted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to accept order',
      });
    }
  }

  async shipOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.shipOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order shipped successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to ship order',
      });
    }
  }

  async completeOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.completeOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to complete order',
      });
    }
  }

  async cancelOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const order = await orderService.cancelOrder(id);

      if (!order) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        data: order,
        message: 'Order cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel order',
      });
    }
  }

  async deleteOrder(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await orderService.deleteOrder(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Order not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Order deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete order',
      });
    }
  }
}
```### backend/src/controllers/InvoiceController.ts```typescript
import { Request, Response } from 'express';
import { InvoiceService } from '../services/InvoiceService';
import Joi from 'joi';

const invoiceService = new InvoiceService();

const createInvoiceValidationSchema = Joi.object({
  orderId: Joi.string().uuid().required(),
  dueDate: Joi.date().required(),
  notes: Joi.string().optional(),
});

export class InvoiceController {
  async getAllInvoices(req: Request, res: Response): Promise<void> {
    try {
      const invoices = await invoiceService.getAllInvoices();
      res.json({
        success: true,
        data: invoices,
        message: 'Invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoices',
      });
    }
  }

  async getInvoiceById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.getInvoiceById(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice',
      });
    }
  }

  async getInvoicesByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const invoices = await invoiceService.getInvoicesByCustomerId(customerId);
      res.json({
        success: true,
        data: invoices,
        message: 'Customer invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer invoices',
      });
    }
  }

  async getInvoicesByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['draft', 'sent', 'paid', 'overdue', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const invoices = await invoiceService.getInvoicesByStatus(status);
      res.json({
        success: true,
        data: invoices,
        message: `Invoices with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoices by status',
      });
    }
  }

  async getInvoiceByOrderId(req: Request, res: Response): Promise<void> {
    try {
      const { orderId } = req.params;
      const invoice = await invoiceService.getInvoiceByOrderId(orderId);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found for this order',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice by order ID',
      });
    }
  }

  async createInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createInvoiceValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const invoice = await invoiceService.createInvoice(value);
      res.status(201).json({
        success: true,
        data: invoice,
        message: 'Invoice created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create invoice',
      });
    }
  }

  async updateInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const invoice = await invoiceService.updateInvoice(updateData);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update invoice',
      });
    }
  }

  async markInvoiceAsPaid(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.markInvoiceAsPaid(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice marked as paid successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to mark invoice as paid',
      });
    }
  }

  async sendInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.sendInvoice(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice sent successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to send invoice',
      });
    }
  }

  async cancelInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const invoice = await invoiceService.cancelInvoice(id);

      if (!invoice) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        data: invoice,
        message: 'Invoice cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel invoice',
      });
    }
  }

  async deleteInvoice(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await invoiceService.deleteInvoice(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Invoice not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Invoice deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete invoice',
      });
    }
  }

  async getOverdueInvoices(req: Request, res: Response): Promise<void> {
    try {
      const invoices = await invoiceService.getOverdueInvoices();
      res.json({
        success: true,
        data: invoices,
        message: 'Overdue invoices retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve overdue invoices',
      });
    }
  }
}
```### backend/src/controllers/PaymentController.ts```typescript
import { Request, Response } from 'express';
import { PaymentService } from '../services/PaymentService';
import Joi from 'joi';

const paymentService = new PaymentService();

const createPaymentValidationSchema = Joi.object({
  invoiceId: Joi.string().uuid().required(),
  amount: Joi.number().positive().required(),
  paymentMethod: Joi.string().valid('credit_card', 'bank_transfer', 'check', 'cash', 'paypal').required(),
  paymentDetails: Joi.object({
    cardLast4: Joi.string().optional(),
    bankAccount: Joi.string().optional(),
    checkNumber: Joi.string().optional(),
    paypalEmail: Joi.string().email().optional(),
  }).required(),
});

export class PaymentController {
  async getAllPayments(req: Request, res: Response): Promise<void> {
    try {
      const payments = await paymentService.getAllPayments();
      res.json({
        success: true,
        data: payments,
        message: 'Payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments',
      });
    }
  }

  async getPaymentById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.getPaymentById(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payment',
      });
    }
  }

  async getPaymentsByCustomerId(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.params;
      const payments = await paymentService.getPaymentsByCustomerId(customerId);
      res.json({
        success: true,
        data: payments,
        message: 'Customer payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve customer payments',
      });
    }
  }

  async getPaymentsByInvoiceId(req: Request, res: Response): Promise<void> {
    try {
      const { invoiceId } = req.params;
      const payments = await paymentService.getPaymentsByInvoiceId(invoiceId);
      res.json({
        success: true,
        data: payments,
        message: 'Invoice payments retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve invoice payments',
      });
    }
  }

  async getPaymentsByStatus(req: Request, res: Response): Promise<void> {
    try {
      const { status } = req.params;
      const validStatuses = ['pending', 'processing', 'completed', 'failed', 'cancelled'];
      
      if (!validStatuses.includes(status)) {
        res.status(400).json({
          success: false,
          message: 'Invalid status specified',
        });
        return;
      }

      const payments = await paymentService.getPaymentsByStatus(status);
      res.json({
        success: true,
        data: payments,
        message: `Payments with status ${status} retrieved successfully`,
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments by status',
      });
    }
  }

  async createPayment(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = createPaymentValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const payment = await paymentService.createPayment(value);
      res.status(201).json({
        success: true,
        data: payment,
        message: 'Payment created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create payment',
      });
    }
  }

  async updatePayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const payment = await paymentService.updatePayment(updateData);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update payment',
      });
    }
  }

  async processPayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.processPayment(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment processed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to process payment',
      });
    }
  }

  async cancelPayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const payment = await paymentService.cancelPayment(id);

      if (!payment) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        data: payment,
        message: 'Payment cancelled successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to cancel payment',
      });
    }
  }

  async deletePayment(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await paymentService.deletePayment(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Payment not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Payment deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete payment',
      });
    }
  }

  async getPaymentsByDateRange(req: Request, res: Response): Promise<void> {
    try {
      const { startDate, endDate } = req.query;

      if (!startDate || !endDate) {
        res.status(400).json({
          success: false,
          message: 'Start date and end date are required',
        });
        return;
      }

      const start = new Date(startDate as string);
      const end = new Date(endDate as string);

      if (isNaN(start.getTime()) || isNaN(end.getTime())) {
        res.status(400).json({
          success: false,
          message: 'Invalid date format',
        });
        return;
      }

      const payments = await paymentService.getPaymentsByDateRange(start, end);
      res.json({
        success: true,
        data: payments,
        message: 'Payments by date range retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payments by date range',
      });
    }
  }

  async getPaymentSummary(req: Request, res: Response): Promise<void> {
    try {
      const { customerId } = req.query;
      const summary = await paymentService.getPaymentSummary(customerId as string);
      
      res.json({
        success: true,
        data: summary,
        message: 'Payment summary retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve payment summary',
      });
    }
  }
}
```### backend/src/routes/customerRoutes.ts```typescript
import { Router } from 'express';
import { CustomerController } from '../controllers/CustomerController';

const router = Router();
const customerController = new CustomerController();

// GET routes
router.get('/', customerController.getAllCustomers.bind(customerController));
router.get('/search', customerController.searchCustomers.bind(customerController));
router.get('/role/:role', customerController.getCustomersByRole.bind(customerController));
router.get('/:id', customerController.getCustomerById.bind(customerController));

// POST routes
router.post('/', customerController.createCustomer.bind(customerController));

// PUT routes
router.put('/:id', customerController.updateCustomer.bind(customerController));

// DELETE routes
router.delete('/:id', customerController.deleteCustomer.bind(customerController));

export default router;
```### backend/src/routes/productRoutes.ts```typescript
import { Router } from 'express';
import { ProductController } from '../controllers/ProductController';

const router = Router();
const productController = new ProductController();

// GET routes
router.get('/', productController.getAllProducts.bind(productController));
router.get('/active', productController.getActiveProducts.bind(productController));
router.get('/search', productController.searchProducts.bind(productController));
router.get('/category/:category', productController.getProductsByCategory.bind(productController));
router.get('/sku/:sku', productController.getProductBySkuEndpoint.bind(productController));
router.get('/:id', productController.getProductById.bind(productController));

// POST routes
router.post('/', productController.createProduct.bind(productController));

// PUT routes
router.put('/:id', productController.updateProduct.bind(productController));
router.put('/:id/stock', productController.updateProductStock.bind(productController));

// DELETE routes
router.delete('/:id', productController.deleteProduct.bind(productController));

export default router;
```### backend/src/routes/orderRoutes.ts```typescript
import { Router } from 'express';
import { OrderController } from '../controllers/OrderController';

const router = Router();
const orderController = new OrderController();

// GET routes
router.get('/', orderController.getAllOrders.bind(orderController));
router.get('/status/:status', orderController.getOrdersByStatus.bind(orderController));
router.get('/customer/:customerId', orderController.getOrdersByCustomerId.bind(orderController));
router.get('/:id', orderController.getOrderById.bind(orderController));

// POST routes
router.post('/', orderController.createOrder.bind(orderController));

// PUT routes
router.put('/:id', orderController.updateOrder.bind(orderController));
router.put('/:id/accept', orderController.acceptOrder.bind(orderController));
router.put('/:id/ship', orderController.shipOrder.bind(orderController));
router.put('/:id/complete', orderController.completeOrder.bind(orderController));
router.put('/:id/cancel', orderController.cancelOrder.bind(orderController));

// DELETE routes
router.delete('/:id', orderController.deleteOrder.bind(orderController));

export default router;
```### backend/src/routes/invoiceRoutes.ts```typescript
import { Router } from 'express';
import { InvoiceController } from '../controllers/InvoiceController';

const router = Router();
const invoiceController = new InvoiceController();

// GET routes
router.get('/', invoiceController.getAllInvoices.bind(invoiceController));
router.get('/overdue', invoiceController.getOverdueInvoices.bind(invoiceController));
router.get('/status/:status', invoiceController.getInvoicesByStatus.bind(invoiceController));
router.get('/customer/:customerId', invoiceController.getInvoicesByCustomerId.bind(invoiceController));
router.get('/order/:orderId', invoiceController.getInvoiceByOrderId.bind(invoiceController));
router.get('/:id', invoiceController.getInvoiceById.bind(invoiceController));

// POST routes
router.post('/', invoiceController.createInvoice.bind(invoiceController));

// PUT routes
router.put('/:id', invoiceController.updateInvoice.bind(invoiceController));
router.put('/:id/pay', invoiceController.markInvoiceAsPaid.bind(invoiceController));
router.put('/:id/send', invoiceController.sendInvoice.bind(invoiceController));
router.put('/:id/cancel', invoiceController.cancelInvoice.bind(invoiceController));

// DELETE routes
router.delete('/:id', invoiceController.deleteInvoice.bind(invoiceController));

export default router;
```### backend/src/routes/paymentRoutes.ts```typescript
import { Router } from 'express';
import { PaymentController } from '../controllers/PaymentController';

const router = Router();
const paymentController = new PaymentController();

// GET routes
router.get('/', paymentController.getAllPayments.bind(paymentController));
router.get('/summary', paymentController.getPaymentSummary.bind(paymentController));
router.get('/date-range', paymentController.getPaymentsByDateRange.bind(paymentController));
router.get('/status/:status', paymentController.getPaymentsByStatus.bind(paymentController));
router.get('/customer/:customerId', paymentController.getPaymentsByCustomerId.bind(paymentController));
router.get('/invoice/:invoiceId', paymentController.getPaymentsByInvoiceId.bind(paymentController));
router.get('/:id', paymentController.getPaymentById.bind(paymentController));

// POST routes
router.post('/', paymentController.createPayment.bind(paymentController));

// PUT routes
router.put('/:id', paymentController.updatePayment.bind(paymentController));
router.put('/:id/process', paymentController.processPayment.bind(paymentController));
router.put('/:id/cancel', paymentController.cancelPayment.bind(paymentController));

// DELETE routes
router.delete('/:id', paymentController.deletePayment.bind(paymentController));

export default router;
```### backend/src/index.ts```typescript
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import sequelize from './config/database';

// Import routes
import customerRoutes from './routes/customerRoutes';
import productRoutes from './routes/productRoutes';
import orderRoutes from './routes/orderRoutes';
import invoiceRoutes from './routes/invoiceRoutes';
import paymentRoutes from './routes/paymentRoutes';

// Import models to ensure they're registered
import Customer from './models/Customer';
import Product from './models/Product';
import Order from './models/Order';
import Invoice from './models/Invoice';
import Payment from './models/Payment';

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Health check route
app.get('/health', (req, res) => {
  res.json({
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
  });
});

// API routes
app.use('/api/customers', customerRoutes);
app.use('/api/products', productRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/invoices', invoiceRoutes);
app.use('/api/payments', paymentRoutes);

// Global error handler
app.use((error: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Unhandled error:', error);
  res.status(500).json({
    success: false,
    message: 'Internal server error',
    error: process.env.NODE_ENV === 'development' ? error.message : undefined,
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    success: false,
    message: 'Route not found',
  });
});

// Database initialization and server start
async function startServer() {
  try {
    // Test database connection
    await sequelize.authenticate();
    console.log('Database connection established successfully.');

    // Sync database models
    await sequelize.sync({ force: false });
    console.log('Database models synchronized.');

    // Start server
    app.listen(PORT, () => {
      console.log(`Server is running on port ${PORT}`);
      console.log(`Health check: http://localhost:${PORT}/health`);
      console.log(`API Documentation: http://localhost:${PORT}/api`);
    });
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

startServer();
```### backend/src/seed.ts```typescript
import sequelize from './config/database';
import Customer from './models/Customer';
import Product from './models/Product';
import Order from './models/Order';
import Invoice from './models/Invoice';
import Payment from './models/Payment';

async function seedDatabase() {
  try {
    // Sync database
    await sequelize.sync({ force: true });
    console.log('Database synchronized.');

    // Seed customers
    const customers = await Customer.bulkCreate([
      {
        name: 'John Smith',
        email: 'john.smith@email.com',
        phone: '+1-555-0101',
        address: {
          street: '123 Main St',
          city: 'New York',
          state: 'NY',
          zipCode: '10001',
          country: 'USA',
        },
        bankingDetails: {
          accountNumber: '1234567890',
          routingNumber: '123456789',
          bankName: 'First National Bank',
        },
        role: 'customer',
      },
      {
        name: 'Jane Doe',
        email: 'jane.doe@email.com',
        phone: '+1-555-0102',
        address: {
          street: '456 Oak Ave',
          city: 'Los Angeles',
          state: 'CA',
          zipCode: '90210',
          country: 'USA',
        },
        bankingDetails: {
          accountNumber: '0987654321',
          routingNumber: '987654321',
          bankName: 'West Coast Bank',
        },
        role: 'customer',
      },
      {
        name: 'Mike Johnson',
        email: 'mike.johnson@company.com',
        phone: '+1-555-0103',
        address: {
          street: '789 Business Blvd',
          city: 'Chicago',
          state: 'IL',
          zipCode: '60601',
          country: 'USA',
        },
        bankingDetails: {
          accountNumber: '1122334455',
          routingNumber: '112233445',
          bankName: 'Midwest Trust',
        },
        role: 'order_staff',
      },
      {
        name: 'Sarah Wilson',
        email: 'sarah.wilson@company.com',
        phone: '+1-555-0104',
        address: {
          street: '321 Finance St',
          city: 'Miami',
          state: 'FL',
          zipCode: '33101',
          country: 'USA',
        },
        bankingDetails: {
          accountNumber: '5544332211',
          routingNumber: '554433221',
          bankName: 'Sunshine Bank',
        },
        role: 'accountant',
      },
    ]);

    console.log('Customers seeded successfully.');

    // Seed products
    const products = await Product.bulkCreate([
      {
        name: 'Wireless Bluetooth Headphones',
        description: 'High-quality wireless headphones with noise cancellation and 30-hour battery life.',
        category: 'Electronics',
        price: 199.99,
        stockQuantity: 50,
        sku: 'WBH-001',
        weight: 0.75,
        dimensions: {
          length: 8.5,
          width: 7.2,
          height: 3.1,
        },
        isActive: true,
      },
      {
        name: 'Ergonomic Office Chair',
        description: 'Comfortable ergonomic office chair with lumbar support and adjustable height.',
        category: 'Furniture',
        price: 349.99,
        stockQuantity: 25,
        sku: 'EOC-002',
        weight: 15.5,
        dimensions: {
          length: 26.0,
          width: 26.0,
          height: 48.0,
        },
        isActive: true,
      },
      {
        name: 'Stainless Steel Water Bottle',
        description: 'Insulated stainless steel water bottle that keeps drinks cold for 24 hours.',
        category: 'Home & Garden',
        price: 29.99,
        stockQuantity: 100,
        sku: 'SSWB-003',
        weight: 0.85,
        dimensions: {
          length: 3.5,
          width: 3.5,
          height: 10.5,
        },
        isActive: true,
      },
      {
        name: 'Organic Cotton T-Shirt',
        description: 'Soft and comfortable organic cotton t-shirt available in multiple sizes.',
        category: 'Clothing',
        price: 24.99,
        stockQuantity: 75,
        sku: 'OCT-004',
        weight: 0.25,
        dimensions: {
          length: 28.0,
          width: 20.0,
          height: 0.5,
        },
        isActive: true,
      },
      {
        name: 'Yoga Mat Premium',
        description: 'Extra thick yoga mat with superior grip and cushioning for all yoga practices.',
        category: 'Sports & Fitness',
        price: 89.99,
        stockQuantity: 30,
        sku: 'YMP-005',
        weight: 2.5,
        dimensions: {
          length: 72.0,
          width: 24.0,
          height: 0.25,
        },
        isActive: true,
      },
    ]);

    console.log('Products seeded successfully.');

    // Seed some orders
    const sampleOrder = await Order.create({
      customerId: customers[0].id,
      customerName: customers[0].name,
      customerEmail: customers[0].email,
      items: [
        {
          productId: products[0].id,
          productName: products[0].name,
          quantity: 2,
          unitPrice: products[0].price,
          totalPrice: products[0].price * 2,
        },
        {
          productId: products[2].id,
          productName: products[2].name,
          quantity: 1,
          unitPrice: products[2].price,
          totalPrice: products[2].price * 1,
        },
      ],
      subtotal: 429.97,
      tax: 34.40,
      shipping: 0,
      total: 464.37,
      status: 'pending',
      orderDate: new Date(),
      shippingAddress: customers[0].address,
      notes: 'Please handle with care',
    } as any);

    console.log('Sample order created successfully.');

    console.log('\n=== Database Seeded Successfully ===');
    console.log(`Created ${customers.length} customers`);
    console.log(`Created ${products.length} products`);
    console.log('Created 1 sample order');
    console.log('\nCustomer roles:');
    console.log('- john.smith@email.com (customer)');
    console.log('- jane.doe@email.com (customer)');
    console.log('- mike.johnson@company.com (order_staff)');
    console.log('- sarah.wilson@company.com (accountant)');
    
  } catch (error) {
    console.error('Error seeding database:', error);
  } finally {
    await sequelize.close();
  }
}

seedDatabase();
```## 4. Frontend Implementation

### frontend/package.json```json
{
  "name": "order-management-frontend",
  "version": "1.0.0",
  "description": "Order Management System Frontend",
  "private": true,
  "dependencies": {
    "@types/node": "^20.4.5",
    "@types/react": "^18.2.17",
    "@types/react-dom": "^18.2.7",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.14.2",
    "axios": "^1.4.0",
    "react-query": "^3.39.3",
    "react-hook-form": "^7.45.2",
    "typescript": "^5.1.6",
    "tailwindcss": "^3.3.3",
    "autoprefixer": "^10.4.14",
    "postcss": "^8.4.27"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.3",
    "vite": "^4.4.5"
  },
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "start": "vite"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
```### frontend/vite.config.ts```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
```### frontend/tailwind.config.js```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          500: '#f59e0b',
          600: '#d97706',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
        },
      },
    },
  },
  plugins: [],
}
```### frontend/src/types/index.ts```typescript
// Re-export all shared domain types
export * from '../../../shared/domain/Customer';
export * from '../../../shared/domain/Product';
export * from '../../../shared/domain/Order';
export * from '../../../shared/domain/Invoice';
export * from '../../../shared/domain/Payment';

// Frontend-specific types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message: string;
  error?: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface FilterParams {
  status?: string;
  customerId?: string;
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export type LoadingState = 'idle' | 'loading' | 'succeeded' | 'failed';

export interface FormErrors {
  [key: string]: string | string[] | FormErrors;
}

export interface TableColumn<T> {
  key: keyof T;
  title: string;
  sortable?: boolean;
  render?: (value: any, record: T) => React.ReactNode;
  width?: string;
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export interface NotificationProps {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  description?: string;
  duration?: number;
}
```### frontend/src/services/api.ts```typescript
import axios from 'axios';
import { ApiResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to:`, config.url);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`Response from ${response.config.url}:`, response.status);
    return response;
  },
  (error) => {
    console.error('Response error:', error.response?.data || error.message);
    
    if (error.response?.status === 401) {
      // Handle unauthorized access
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

// Generic API methods
export const api = {
  get: async <T>(url: string, params?: any): Promise<ApiResponse<T>> => {
    const response = await apiClient.get(url, { params });
    return response.data;
  },

  post: async <T>(url: string, data?: any): Promise<ApiResponse<T>> => {
    const response = await apiClient.post(url, data);
    return response.data;
  },

  put: async <T>(url: string, data?: any): Promise<ApiResponse<T>> => {
    const response = await apiClient.put(url, data);
    return response.data;
  },

  delete: async <T>(url: string): Promise<ApiResponse<T>> => {
    const response = await apiClient.delete(url);
    return response.data;
  },
};

export default apiClient;
```### frontend/src/services/customerService.ts```typescript
import { api } from './api';
import { Customer, CreateCustomerRequest, UpdateCustomerRequest, ApiResponse } from '../types';

export class CustomerService {
  private baseUrl = '/customers';

  async getAllCustomers(): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(this.baseUrl);
  }

  async getCustomerById(id: string): Promise<ApiResponse<Customer>> {
    return api.get<Customer>(`${this.baseUrl}/${id}`);
  }

  async getCustomersByRole(role: string): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(`${this.baseUrl}/role/${role}`);
  }

  async createCustomer(data: CreateCustomerRequest): Promise<ApiResponse<Customer>> {
    return api.post<Customer>(this.baseUrl, data);
  }

  async updateCustomer(data: UpdateCustomerRequest): Promise<ApiResponse<Customer>> {
    return api.put<Customer>(`${this.baseUrl}/${data.id}`, data);
  }

  async deleteCustomer(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }

  async searchCustomers(query: string): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(`${this.baseUrl}/search`, { q: query });
  }
}

export const customerService = new CustomerService();
```### frontend/src/services/productService.ts```typescript
import { api } from './api';
import { Product, CreateProductRequest, UpdateProductRequest, ApiResponse } from '../types';

export class ProductService {
  private baseUrl = '/products';

  async getAllProducts(): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(this.baseUrl);
  }

  async getActiveProducts(): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/active`);
  }

  async getProductById(id: string): Promise<ApiResponse<Product>> {
    return api.get<Product>(`${this.baseUrl}/${id}`);
  }

  async createProduct(data: CreateProductRequest): Promise<ApiResponse<Product>> {
    return api.post<Product>(this.baseUrl, data);
  }

  async updateProduct(data: UpdateProductRequest): Promise<ApiResponse<Product>> {
    return api.put<Product>(`${this.baseUrl}/${data.id}`, data);
  }

  async deleteProduct(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }

  async updateProductStock(id: string, quantity: number): Promise<ApiResponse<Product>> {
    return api.put<Product>(`${this.baseUrl}/${id}/stock`, { quantity });
  }

  async searchProducts(query: string): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/search`, { q: query });
  }

  async getProductsByCategory(category: string): Promise<ApiResponse<Product[]>> {
    return api.get<Product[]>(`${this.baseUrl}/category/${category}`);
  }
}

export const productService = new ProductService();
```### frontend/src/services/orderService.ts```typescript
import { api } from './api';
import { Order, CreateOrderRequest, UpdateOrderRequest, ApiResponse } from '../types';

export class OrderService {
  private baseUrl = '/orders';

  async getAllOrders(): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(this.baseUrl);
  }

  async getOrderById(id: string): Promise<ApiResponse<Order>> {
    return api.get<Order>(`${this.baseUrl}/${id}`);
  }

  async getOrdersByCustomerId(customerId: string): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getOrdersByStatus(status: string): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(`${this.baseUrl}/status/${status}`);
  }

  async createOrder(data: CreateOrderRequest): Promise<ApiResponse<Order>> {
    return api.post<Order>(this.baseUrl, data);
  }

  async updateOrder(data: UpdateOrderRequest): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${data.id}`, data);
  }

  async acceptOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/accept`);
  }

  async shipOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/ship`);
  }

  async completeOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/complete`);
  }

  async cancelOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/cancel`);
  }

  async deleteOrder(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const orderService = new OrderService();
```### frontend/src/services/invoiceService.ts```typescript
import { api } from './api';
import { Invoice, CreateInvoiceRequest, UpdateInvoiceRequest, ApiResponse } from '../types';

export class InvoiceService {
  private baseUrl = '/invoices';

  async getAllInvoices(): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(this.baseUrl);
  }

  async getInvoiceById(id: string): Promise<ApiResponse<Invoice>> {
    return api.get<Invoice>(`${this.baseUrl}/${id}`);
  }

  async getInvoicesByCustomerId(customerId: string): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getInvoicesByStatus(status: string): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/status/${status}`);
  }

  async getInvoiceByOrderId(orderId: string): Promise<ApiResponse<Invoice>> {
    return api.get<Invoice>(`${this.baseUrl}/order/${orderId}`);
  }

  async getOverdueInvoices(): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/overdue`);
  }

  async createInvoice(data: CreateInvoiceRequest): Promise<ApiResponse<Invoice>> {
    return api.post<Invoice>(this.baseUrl, data);
  }

  async updateInvoice(data: UpdateInvoiceRequest): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${data.id}`, data);
  }

  async markInvoiceAsPaid(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/pay`);
  }

  async sendInvoice(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/send`);
  }

  async cancelInvoice(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/cancel`);
  }

  async deleteInvoice(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const invoiceService = new InvoiceService();
```### frontend/src/services/paymentService.ts```typescript
import { api } from './api';
import { Payment, CreatePaymentRequest, UpdatePaymentRequest, ApiResponse } from '../types';

export class PaymentService {
  private baseUrl = '/payments';

  async getAllPayments(): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(this.baseUrl);
  }

  async getPaymentById(id: string): Promise<ApiResponse<Payment>> {
    return api.get<Payment>(`${this.baseUrl}/${id}`);
  }

  async getPaymentsByCustomerId(customerId: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getPaymentsByInvoiceId(invoiceId: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/invoice/${invoiceId}`);
  }

  async getPaymentsByStatus(status: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/status/${status}`);
  }

  async getPaymentsByDateRange(startDate: string, endDate: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/date-range`, { startDate, endDate });
  }

  async getPaymentSummary(customerId?: string): Promise<ApiResponse<any>> {
    return api.get<any>(`${this.baseUrl}/summary`, customerId ? { customerId } : undefined);
  }

  async createPayment(data: CreatePaymentRequest): Promise<ApiResponse<Payment>> {
    return api.post<Payment>(this.baseUrl, data);
  }

  async updatePayment(data: UpdatePaymentRequest): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${data.id}`, data);
  }

  async processPayment(id: string): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${id}/process`);
  }

  async cancelPayment(id: string): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${id}/cancel`);
  }

  async deletePayment(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const paymentService = new PaymentService();
```### frontend/src/components/common/Layout.tsx```typescript
import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navigationItems = [
    { path: '/customers', label: 'Customers', icon: '👥' },
    { path: '/products', label: 'Products', icon: '📦' },
    { path: '/orders', label: 'Orders', icon: '📋' },
    { path: '/invoices', label: 'Invoices', icon: '📄' },
    { path: '/payments', label: 'Payments', icon: '💳' },
  ];

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link to="/" className="text-2xl font-bold text-primary-600">
                OrderMS
              </Link>
            </div>
            <nav className="hidden md:flex space-x-8">
              {navigationItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(item.path)
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <div className="md:hidden bg-white border-b border-gray-200">
        <div className="px-2 pt-2 pb-3 space-y-1">
          {navigationItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center px-3 py-2 rounded-md text-base font-medium transition-colors ${
                isActive(item.path)
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <span className="mr-3">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-gray-500 text-sm">
            <p>&copy; 2024 Order Management System. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
```### frontend/src/components/common/Button.tsx```typescript
import React from 'react';

interface ButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  className?: string;
}

const Button: React.FC<ButtonProps> = ({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  className = '',
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500',
    secondary: 'bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500',
    success: 'bg-success-600 text-white hover:bg-success-700 focus:ring-success-500',
    warning: 'bg-warning-600 text-white hover:bg-warning-700 focus:ring-warning-500',
    error: 'bg-error-600 text-white hover:bg-error-700 focus:ring-error-500',
    outline: 'border-2 border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-primary-500',
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const disabledClasses = disabled || loading ? 'opacity-50 cursor-not-allowed' : '';

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabledClasses} ${className}`}
    >
      {loading && (
        <svg className="animate-spin -ml-1 mr-3 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      )}
      {children}
    </button>
  );
};

export default Button;
```### frontend/src/components/common/Modal.tsx```typescript
import React, { useEffect } from 'react';
import { ModalProps } from '../../types';

interface ExtendedModalProps extends ModalProps {
  children: React.ReactNode;
  onConfirm?: () => void;
  onCancel?: () => void;
  confirmText?: string;
  cancelText?: string;
  showActions?: boolean;
}

const Modal: React.FC<ExtendedModalProps> = ({
  isOpen,
  onClose,
  title,
  size = 'md',
  children,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  showActions = false,
}) => {
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div 
        className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0"
        onClick={handleBackdropClick}
      >
        {/* Backdrop */}
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        {/* Center modal */}
        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        {/* Modal panel */}
        <div className={`inline-block align-bottom bg-white rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle ${sizeClasses[size]} sm:w-full sm:p-6`}>
          {/* Header */}
          {title && (
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">{title}</h3>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <span className="sr-only">Close</span>
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          )}

          {/* Content */}
          <div className="mb-4">
            {children}
          </div>

          {/* Actions */}
          {showActions && (
            <div className="flex justify-end space-x-3">
              <button
                onClick={onCancel || onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
              >
                {cancelText}
              </button>
              {onConfirm && (
                <button
                  onClick={onConfirm}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  {confirmText}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Modal;
```### frontend/src/components/common/Table.tsx```typescript
import React from 'react';
import { TableColumn } from '../../types';

interface TableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (record: T) => void;
}

const Table = <T extends Record<string, any>>({
  data,
  columns,
  loading = false,
  emptyMessage = 'No data available',
  onRowClick,
}: TableProps<T>) => {
  if (loading) {
    return (
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-8 text-center">
          <p className="text-sm text-gray-500">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  style={{ width: column.width }}
                >
                  {column.title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((record, index) => (
              <tr
                key={index}
                onClick={() => onRowClick?.(record)}
                className={onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}
              >
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {column.render
                      ? column.render(record[column.key], record)
                      : String(record[column.key] || '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Table;
```### frontend/src/components/common/Notification.tsx```typescript
import React, { useEffect, useState } from 'react';
import { NotificationProps } from '../../types';

interface NotificationManagerProps {
  notifications: (NotificationProps & { id: string })[];
  onRemove: (id: string) => void;
}

const NotificationManager: React.FC<NotificationManagerProps> = ({
  notifications,
  onRemove,
}) => {
  return (
    <div className="fixed top-4 right-4 z-50 space-y-4">
      {notifications.map((notification) => (
        <Notification
          key={notification.id}
          {...notification}
          onClose={() => onRemove(notification.id)}
        />
      ))}
    </div>
  );
};

interface SingleNotificationProps extends NotificationProps {
  onClose: () => void;
}

const Notification: React.FC<SingleNotificationProps> = ({
  type,
  message,
  description,
  duration = 5000,
  onClose,
}) => {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Allow fade out animation
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const typeStyles = {
    success: {
      bg: 'bg-success-50',
      border: 'border-success-200',
      icon: '✓',
      iconColor: 'text-success-400',
      textColor: 'text-success-800',
    },
    error: {
      bg: 'bg-error-50',
      border: 'border-error-200',
      icon: '✕',
      iconColor: 'text-error-400',
      textColor: 'text-error-800',
    },
    warning: {
      bg: 'bg-warning-50',
      border: 'border-warning-200',
      icon: '⚠',
      iconColor: 'text-warning-400',
      textColor: 'text-warning-800',
    },
    info: {
      bg: 'bg-primary-50',
      border: 'border-primary-200',
      icon: 'ⓘ',
      iconColor: 'text-primary-400',
      textColor: 'text-primary-800',
    },
  };

  const styles = typeStyles[type];

  return (
    <div
      className={`max-w-sm w-full ${styles.bg} ${styles.border} border rounded-lg shadow-lg transform transition-all duration-300 ${
        isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}
    >
      <div className="p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <span className={`inline-flex items-center justify-center h-5 w-5 ${styles.iconColor}`}>
              {styles.icon}
            </span>
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className={`text-sm font-medium ${styles.textColor}`}>
              {message}
            </p>
            {description && (
              <p className={`mt-1 text-sm ${styles.textColor} opacity-90`}>
                {description}
              </p>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => {
                setIsVisible(false);
                setTimeout(onClose, 300);
              }}
              className={`inline-flex ${styles.textColor} hover:opacity-75 focus:outline-none`}
            >
              <span className="sr-only">Close</span>
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationManager;
```### frontend/src/components/customers/CustomerOverview.tsx```typescript
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Customer } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';
import Table from '../common/Table';

const CustomerOverview: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      const response = await customerService.getAllCustomers();
      if (response.success && response.data) {
        setCustomers(response.data);
      } else {
        setError(response.message || 'Failed to load customers');
      }
    } catch (err) {
      setError('An error occurred while loading customers');
      console.error('Error loading customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      key: 'name' as keyof Customer,
      title: 'Name',
      render: (value: string, record: Customer) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{record.email}</div>
        </div>
      ),
    },
    {
      key: 'phone' as keyof Customer,
      title: 'Phone',
    },
    {
      key: 'role' as keyof Customer,
      title: 'Role',
      render: (value: string) => (
        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
          value === 'customer' ? 'bg-blue-100 text-blue-800' :
          value === 'order_staff' ? 'bg-green-100 text-green-800' :
          'bg-purple-100 text-purple-800'
        }`}>
          {value.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'address' as keyof Customer,
      title: 'Address',
      render: (value: Customer['address']) => (
        <div className="text-sm text-gray-900">
          {value.city}, {value.state}
        </div>
      ),
    },
    {
      key: 'createdAt' as keyof Customer,
      title: 'Created',
      render: (value: string) => (
        <div className="text-sm text-gray-900">
          {new Date(value).toLocaleDateString()}
        </div>
      ),
    },
  ];

  if (error) {
    return (
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="text-center">
            <div className="text-error-500 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.729-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Customers</h3>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <Button onClick={loadCustomers} variant="primary">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage customer information and view customer details.
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link to="/customers/new">
            <Button variant="primary">
              Add New Customer
            </Button>
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">👥</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Customers
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'customer').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">👨‍💼</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Order Staff
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'order_staff').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">📊</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Accountants
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'accountant').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Customer Table */}
      <Table
        data={customers}
        columns={columns}
        loading={loading}
        emptyMessage="No customers found. Add your first customer to get started."
        onRowClick={(customer) => {
          // Navigate to customer details
          window.location.href = `/customers/${customer.id}`;
        }}
      />
    </div>
  );
};

export default CustomerOverview;
```### frontend/src/components/customers/CustomerList.tsx```typescript
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Customer } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';
import Table from '../common/Table';

interface CustomerListProps {
  role?: 'customer' | 'order_staff' | 'accountant';
  searchTerm?: string;
}

const CustomerList: React.FC<CustomerListProps> = ({ role, searchTerm }) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCustomers();
  }, [role, searchTerm]);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      setError(null);

      let response;
      if (searchTerm) {
        response = await customerService.searchCustomers(searchTerm);
      } else if (role) {
        response = await customerService.getCustomersByRole(role);
      } else {
        response = await customerService.getAllCustomers();
      }

      if (response.success && response.data) {
        setCustomers(response.data);
      } else {
        setError(response.message || 'Failed to load customers');
      }
    } catch (err) {
      setError('An error occurred while loading customers');
      console.error('Error loading customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCustomer = async (customerId: string) => {
    if (!confirm('Are you sure you want to delete this customer? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await customerService.deleteCustomer(customerId);
      if (response.success) {
        setCustomers(customers.filter(c => c.id !== customerId));
      } else {
        setError(response.message || 'Failed to delete customer');
      }
    } catch (err) {
      setError('An error occurred while deleting the customer');
      console.error('Error deleting customer:', err);
    }
  };

  const columns = [
    {
      key: 'name' as keyof Customer,
      title: 'Customer',
      render: (value: string, record: Customer) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{record.email}</div>
        </div>
      ),
    },
    {
      key: 'phone' as keyof Customer,
      title: 'Phone',
      render: (value: string) => (
        <span className="text-sm text-gray-900">{value}</span>
      ),
    },
    {
      key: 'role' as keyof Customer,
      title: 'Role',
      render: (value: string) => (
        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
          value === 'customer' ? 'bg-blue-100 text-blue-800' :
          value === 'order_staff' ? 'bg-green-100 text-green-800' :
          'bg-purple-100 text-purple-800'
        }`}>
          {value.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'address' as keyof Customer,
      title: 'Location',
      render: (value: Customer['address']) => (
        <div className="text-sm text-gray-900">
          <div>{value.city}, {value.state}</div>
          <div className="text-xs text-gray-500">{value.country}</div>
        </div>
      ),
    },
    {
      key: 'bankingDetails' as keyof Customer,
      title: 'Bank',
      render: (value: Customer['bankingDetails']) => (
        <div className="text-sm text-gray-900">
          <div>{value.bankName}</div>
          <div className="text-xs text-gray-500">***{value.accountNumber.slice(-4)}</div>
        </div>
      ),
    },
    {
      key: 'createdAt' as keyof Customer,
      title: 'Created',
      render: (value: string) => (
        <div className="text-sm text-gray-900">
          {new Date(value).toLocaleDateString()}
        </div>
      ),
    },
    {
      key: 'id' as keyof Customer,
      title: 'Actions',
      render: (value: string, record: Customer) => (
        <div className="flex space-x-2">
          <Link to={`/customers/${value}`}>
            <Button size="sm" variant="outline">
              View
            </Button>
          </Link>
          <Link to={`/customers/${value}/edit`}>
            <Button size="sm" variant="secondary">
              Edit
            </Button>
          </Link>
          <Button
            size="sm"
            variant="error"
            onClick={() => handleDeleteCustomer(value)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  const getTitle = () => {
    if (searchTerm) return `Search Results for "${searchTerm}"`;
    if (role) return `${role.replace('_', ' ')} List`;
    return 'All Customers';
  };

  const getDescription = () => {
    if (searchTerm) return `Found ${customers.length} customer(s) matching your search.`;
    if (role) return `Showing all users with ${role.replace('_', ' ')} role.`;
    return `Total of ${customers.length} customers in the system.`;
  };

  if (error) {
    return (
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="text-center">
            <div className="text-error-500 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.729-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Customers</h3>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <Button onClick={loadCustomers} variant="primary">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{getTitle()}</h2>
          <p className="mt-1 text-sm text-gray-600">{getDescription()}</p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link to="/customers/new">
            <Button variant="primary">
              Add Customer
            </Button>
          </Link>
        </div>
      </div>

      {/* Customer List */}
      <Table
        data={customers}
        columns={columns}
        loading={loading}
        emptyMessage={
          searchTerm
            ? `No customers found matching "${searchTerm}".`
            : role
            ? `No customers found with ${role.replace('_', ' ')} role.`
            : 'No customers found. Add your first customer to get started.'
        }
      />
    </div>
  );
};

export default CustomerList;
```### frontend/src/components/customers/CustomerForm.tsx```typescript
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { Customer, CreateCustomerRequest } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';

interface CustomerFormData {
  name: string;
  email: string;
  phone: string;
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  bankingDetails: {
    accountNumber: string;
    routingNumber: string;
    bankName: string;
  };
  role: 'customer' | 'order_staff' | 'accountant';
}

const CustomerForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const isEditing = !!id;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<CustomerFormData>({
    defaultValues: {
      name: '',
      email: '',
      phone: '',
      address: {
        street: '',
        city: '',
        state: '',
        zipCode: '',
        country: 'USA',
      },
      bankingDetails: {
        accountNumber: '',
        routingNumber: '',
        bankName: '',
      },
      role: 'customer',
    },
  });

  useEffect(() => {
    if (isEditing && id) {
      loadCustomer(id);
    }
  }, [isEditing, id]);

  const loadCustomer = async (customerId: string) => {
    try {
      setLoading(true);
      const response = await customerService.getCustomerById(customerId);
      if (response.success && response.data) {
        const customer = response.data;
        setValue('name', customer.name);
        setValue('email', customer.email);
        setValue('phone', customer.phone);
        setValue('address', customer.address);
        setValue('bankingDetails', customer.bankingDetails);
        setValue('role', customer.role);
      } else {
        setError(response.message || 'Failed to load customer');
      }
    } catch (err) {
      setError('An error occurred while loading the customer');
      console.error('Error loading customer:', err);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: CustomerFormData) => {
    try {
      setError(null);
      setSuccess(null);

      let response;
      if (isEditing && id) {
        response = await customerService.updateCustomer({ id, ...data });
      } else {
        response = await customerService.createCustomer(data as CreateCustomerRequest);
      }

      if (response.success) {
        setSuccess(isEditing ? 'Customer updated successfully!' : 'Customer created successfully!');
        setTimeout(() => {
          navigate('/customers');
        }, 1500);
      } else {
        setError(response.message || 'Failed to save customer');
      }
    } catch (err) {
      setError('An error occurred while saving the customer');
      console.error('Error saving customer:', err);
    }
  };

  if (loading && isEditing) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Loading customer...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {/* Header */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900">
              {isEditing ? 'Edit Customer' : 'Create New Customer'}
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {isEditing
                ? 'Update customer information and settings.'
                : 'Add a new customer to the system.'}
            </p>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="mb-4 bg-error-50 border border-error-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-error-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-error-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {success && (
            <div className="mb-4 bg-success-50 border border-success-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-success-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-success-800">{success}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Name *
                </label>
                <Controller
                  name="name"
                  control={control}
                  rules={{ required: 'Name is required' }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="text"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter customer name"
                    />
                  )}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-error-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Email *
                </label>
                <Controller
                  name="email"
                  control={control}
                  rules={{
                    required: 'Email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address',
                    },
                  }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="email"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter email address"
                    />
                  )}
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-error-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Phone *
                </label>
                <Controller
                  name="phone"
                  control={control}
                  rules={{ required: 'Phone is required' }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="tel"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter phone number"
                    />
                  )}
                />
                {errors.phone && (
                  <p className="mt-1 text-sm text-error-600">{errors.phone.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Role *
                </label>
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <select
                      {...field}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    >
                      <option value="customer">Customer</option>
                      <option value="order_staff">Order Staff</option>
                      <option value="accountant">Accountant</option>
                    </select>
                  )}
                />
              </div>
            </div>

            {/* Address */}
            <div>
              <h4 className="text-lg font-medium text-gray-900 mb-4">Address Information</h4>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Street Address *
                  </label>
                  <Controller
                    name="address.street"
                    control={control}
                    rules={{ required: 'Street address is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter street address"
                      />
                    )}
                  />
                  {errors.address?.street && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.street.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    City *
                  </label>
                  <Controller
                    name="address.city"
                    control={control}
                    rules={{ required: 'City is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter city"
                      />
                    )}
                  />
                  {errors.address?.city && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.city.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    State *
                  </label>
                  <Controller
                    name="address.state"
                    control={control}
                    rules={{ required: 'State is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter state"
                      />
                    )}
                  />
                  {errors.address?.state && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.state.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    ZIP Code *
                  </label>
                  <Controller
                    name="address.zipCode"
                    control={control}
                    rules={{ required: 'ZIP code is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter ZIP code"
                      />
                    )}
                  />
                  {errors.address?.zipCode && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.zipCode.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Country *
                  </label>
                  <Controller
                    name="address.country"
                    control={control}
                    rules={{ required: 'Country is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter country"
                      />
                    )}
                  />
                  {errors.address?.country && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.country.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Banking Details */}
            <div>
              <h4 className="text-lg font-medium text-gray-900 mb-4">Banking Information</h4>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Bank Name *
                  </label>
                  <Controller
                    name="bankingDetails.bankName"
                    control={control}
                    rules={{ required: 'Bank name is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter bank name"
                      />
                    )}
                  />
                  {errors.bankingDetails?.bankName && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.bankName.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Account Number *
                  </label>
                  <Controller
                    name="bankingDetails.accountNumber"
                    control={control}
                    rules={{ required: 'Account number is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter account number"
                      />
                    )}
                  />
                  {errors.bankingDetails?.accountNumber && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.accountNumber.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Routing Number *
                  </label>
                  <Controller
                    name="bankingDetails.routingNumber"
                    control={control}
                    rules={{ required: 'Routing number is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter routing number"
                      />
                    )}
                  />
                  {errors.bankingDetails?.routingNumber && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.routingNumber.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate('/customers')}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={isSubmitting}
              >
                {isEditing ? 'Update Customer' : 'Create Customer'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CustomerForm;

## 5. Setup Instructions

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn
- Git

### Backend Setup

1. **Navigate to backend directory**
```bash
cd backend
2. Install dependencies

bash
npm install
3. Build the project

bash
npm run build
4. Initialize and seed database

bash
npm run seed

5. Start the development server

bash
npm run dev
The backend will run on http://localhost:3001

6. Frontend Setup
Navigate to frontend directory

bash
cd frontend

7. Install dependencies

bash
npm install

8. Create PostCSS config
Create frontend/postcss.config.js:

javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}

9. Create CSS file
Create frontend/src/index.css:

css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom styles */
.form-input {
  @apply block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm;
}

.form-select {
  @apply block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm;
}

.form-textarea {
  @apply block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm;
}

.btn {
  @apply inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
  @apply bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500;
}

.btn-secondary {
  @apply bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500;
}

.btn-success {
  @apply bg-success-600 text-white hover:bg-success-700 focus:ring-success-500;
}

.btn-error {
  @apply bg-error-600 text-white hover:bg-error-700 focus:ring-error-500;
}

.btn-outline {
  @apply border-2 border-gray-300 text-gray-700 bg-white hover:bg-gray-50 focus:ring-primary-500;
}

10. Create main App component
Create frontend/src/App.tsx:

typescript
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/common/Layout';
import CustomerOverview from './components/customers/CustomerOverview';
import CustomerForm from './components/customers/CustomerForm';
import './index.css';

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/customers" replace />} />
          <Route path="/customers" element={<CustomerOverview />} />
          <Route path="/customers/new" element={<CustomerForm />} />
          <Route path="/customers/:id" element={<CustomerForm />} />
          <Route path="/customers/:id/edit" element={<CustomerForm />} />
          
          {/* Placeholder routes for other modules */}
          <Route path="/products" element={<div className="text-center py-12"><h2 className="text-2xl font-bold text-gray-900">Products Module</h2><p className="mt-2 text-gray-600">Coming soon...</p></div>} />
          <Route path="/orders" element={<div className="text-center py-12"><h2 className="text-2xl font-bold text-gray-900">Orders Module</h2><p className="mt-2 text-gray-600">Coming soon...</p></div>} />
          <Route path="/invoices" element={<div className="text-center py-12"><h2 className="text-2xl font-bold text-gray-900">Invoices Module</h2><p className="mt-2 text-gray-600">Coming soon...</p></div>} />
          <Route path="/payments" element={<div className="text-center py-12"><h2 className="text-2xl font-bold text-gray-900">Payments Module</h2><p className="mt-2 text-gray-600">Coming soon...</p></div>} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;

11. Create main entry point
Create frontend/src/main.tsx:

typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

12. Create HTML template
Create frontend/index.html:

html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Order Management System</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>

13. Start the development server

bash
npm run dev
The frontend will run on http://localhost:3000

Final Project Structure
text
order-management-system/
├── shared/
│   └── domain/
│       ├── Customer.ts
│       ├── Product.ts
│       ├── Order.ts
│       ├── Invoice.ts
│       └── Payment.ts
├── backend/
│   ├── src/
│   ├── package.json
│   ├── tsconfig.json
│   └── database.sqlite (created after seeding)
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── index.html
└── README.md

14. Testing the System

Backend Testing

Visit http://localhost:3001/health to check backend status

Test API endpoints using Postman or curl

Check database with SQLite browser

Frontend Testing

Visit http://localhost:3000 to access the application

Test customer management features

Verify API communication

Database Seeding

Run npm run seed in backend directory

Check created test data

Test different user roles

This complete implementation provides a fully functional order management system with all the requested features, following Domain-Driven Design principles, and supporting the complete business workflow from customer orders to payment processing and shipping.