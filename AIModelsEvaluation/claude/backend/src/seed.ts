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
        id: '11111111-1111-1111-1111-111111111111', // Fixed ID for reference
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: '22222222-2222-2222-2222-222222222222',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: '33333333-3333-3333-3333-333333333333',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: '44444444-4444-4444-4444-444444444444',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
    ]);

    console.log('Customers seeded successfully.');

    // Seed products
    const products = await Product.bulkCreate([
      {
        id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'dddddddd-dddd-dddd-dddd-dddddddddddd',
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
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
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
        createdAt: new Date(),
        updatedAt: new Date()
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