// Demo script to test the complete workflow
// This script demonstrates the API calls for the complete workflow

const API_BASE = 'http://localhost:3000/api';

// Helper function to make API calls
async function apiCall(method, endpoint, data = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, options);
  const result = await response.json();
  
  console.log(`${method} ${endpoint}:`, result);
  return result;
}

async function demonstrateWorkflow() {
  console.log('=== COMPLETE WORKFLOW DEMONSTRATION ===\n');
  
  try {
    // 1. Create a customer (Staff action)
    console.log('1. Creating customer...');
    const customer = await apiCall('POST', '/customers', {
      name: 'John Doe',
      address: '123 Main St',
      phone: '555-0123',
      bankAccount: '1234567890'
    });
    const customerId = customer.id;
    
    // 2. Create an order (Customer action)
    console.log('\n2. Creating order...');
    const order = await apiCall('POST', '/orders', {
      customerId: customerId,
      customerName: customer.name,
      customerAddress: customer.address,
      customerPhone: customer.phone,
      customerBankAccount: customer.bankAccount,
      totalAmount: 99.99,
      method: 'card',
      items: [{
        name: 'Test Product',
        quantity: 1,
        price: 99.99
      }]
    });
    const orderId = order.id;
    
    // 3. Accept order (Staff action)
    console.log('\n3. Accepting order...');
    const acceptedOrder = await apiCall('POST', `/orders/${orderId}/receive`);
    
    // 4. Create and send invoice (Accountant action)
    console.log('\n4. Creating invoice...');
    const invoice = await apiCall('POST', '/invoices', {
      orderId: orderId,
      amount: 99.99,
      method: 'card'
    });
    const invoiceId = invoice.id;
    
    console.log('\n5. Sending invoice...');
    const sentInvoice = await apiCall('POST', `/invoices/send/${orderId}`);
    
    // 6. Make payment (Customer action)
    console.log('\n6. Making payment...');
    const payment = await apiCall('POST', '/payments', {
      invoiceId: invoiceId,
      amount: 99.99,
      method: 'card'
    });
    const paymentId = payment.id;
    
    console.log(`   Payment created with status: ${payment.status} (should be "pending")`);
    
    // 7. Accept payment (Accountant action) - THE KEY MISSING STEP
    console.log('\n7. Accepting payment (Accountant action)...');
    const acceptedPayment = await apiCall('POST', `/payments/accept/${paymentId}`);
    
    console.log('   Payment acceptance result:');
    console.log(`   - Payment status: ${acceptedPayment.payment.status}`);
    console.log(`   - Invoice status: ${acceptedPayment.invoice.status}`);
    console.log(`   - Order status: ${acceptedPayment.order.status}`);
    
    // 8. Ship order (Staff action)
    console.log('\n8. Shipping order...');
    const shippedOrder = await apiCall('POST', `/orders/${orderId}/ship`);
    
    // 9. Close order (Staff action)
    console.log('\n9. Closing order...');
    const closedOrder = await apiCall('POST', `/orders/${orderId}/close`);
    
    console.log('\n=== WORKFLOW COMPLETED SUCCESSFULLY ===');
    console.log('Final statuses:');
    console.log(`- Order: ${closedOrder.status}`);
    console.log(`- Invoice: ${acceptedPayment.invoice.status}`);
    console.log(`- Payment: ${acceptedPayment.payment.status}`);
    
  } catch (error) {
    console.error('Workflow failed:', error);
  }
}

// Run the demonstration
if (typeof window === 'undefined') {
  // Node.js environment
  const fetch = require('node-fetch');
  demonstrateWorkflow();
} else {
  // Browser environment
  console.log('Run demonstrateWorkflow() in the browser console');
}

module.exports = { demonstrateWorkflow };