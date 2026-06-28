// Main App Component

import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { CustomerOverview } from './components/customer/CustomerOverview';
import { CustomerList } from './components/customer/CustomerList';
import { CustomerForm } from './components/customer/CustomerForm';
import { OrderOverview } from './components/order/OrderOverview';
import { OrderList } from './components/order/OrderList';
import { OrderForm } from './components/order/OrderForm';
import { ProductOverview } from './components/product/ProductOverview';
import { ProductList } from './components/product/ProductList';
import { ProductForm } from './components/product/ProductForm';
import { Customer, Order, Product } from './types';
import { apiService } from './services/api';

function AppContent() {
  const { customers, orders, products, setCustomers, setOrders, setProducts, currentCustomer, setCurrentCustomer, currentOrder, setCurrentOrder, sessionId } = useApp();
  
  const [activeTab, setActiveTab] = useState<'customers' | 'orders' | 'products'>('products');
  const [showForm, setShowForm] = useState<'customer' | 'order' | 'product' | null>(null);
  const [editingItem, setEditingItem] = useState<Customer | Order | Product | null>(null);

  const handleRefreshCustomers = async () => {
    const response = await apiService.getAllCustomers();
    if (response.success) setCustomers(response.data || []);
  };

  const handleRefreshOrders = async () => {
    const response = await apiService.getAllOrders();
    if (response.success) setOrders(response.data || []);
  };

  const handleRefreshProducts = async () => {
    const response = await apiService.getAllProducts();
    if (response.success) setProducts(response.data || []);
  };

  const handleDeleteCustomer = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this customer?')) {
      await apiService.deleteCustomer(id);
      handleRefreshCustomers();
    }
  };

  const handleDeleteProduct = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this product?')) {
      await apiService.deleteProduct(id);
      handleRefreshProducts();
    }
  };

  const handleConfirmOrder = async (id: string) => {
    await apiService.confirmOrder(id);
    handleRefreshOrders();
  };

  const handleCancelOrder = async (id: string) => {
    await apiService.cancelOrder(id);
    handleRefreshOrders();
  };

  const handleFormSuccess = () => {
    setShowForm(null);
    setEditingItem(null);
    handleRefreshCustomers();
    handleRefreshOrders();
    handleRefreshProducts();
  };

  const handleFormCancel = () => {
    setShowForm(null);
    setEditingItem(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Order Processing System</h1>
        <p>Session: {sessionId}</p>
      </header>
      
      <nav className="app-nav">
        <button 
          className={activeTab === 'products' ? 'active' : ''} 
          onClick={() => setActiveTab('products')}
        >
          Products
        </button>
        <button 
          className={activeTab === 'customers' ? 'active' : ''} 
          onClick={() => setActiveTab('customers')}
        >
          Customers
        </button>
        <button 
          className={activeTab === 'orders' ? 'active' : ''} 
          onClick={() => setActiveTab('orders')}
        >
          Orders
        </button>
      </nav>

      <main className="app-main">
        {activeTab === 'products' && (
          <div>
            <ProductOverview />
            <button onClick={() => { setShowForm('product'); setEditingItem(null); }}>Add Product</button>
            <ProductList 
              products={products} 
              onSelectProduct={(p) => { setEditingItem(p); setShowForm('product'); }}
              onDeleteProduct={handleDeleteProduct}
            />
          </div>
        )}

        {activeTab === 'customers' && (
          <div>
            <CustomerOverview />
            <button onClick={() => { setShowForm('customer'); setEditingItem(null); }}>Add Customer</button>
            <CustomerList 
              customers={customers} 
              onSelectCustomer={(c) => { setEditingItem(c); setShowForm('customer'); }}
              onDeleteCustomer={handleDeleteCustomer}
            />
          </div>
        )}

        {activeTab === 'orders' && (
          <div>
            <OrderOverview />
            {currentCustomer && (
              <button onClick={() => { setShowForm('order'); }}>Create Order for {currentCustomer.name}</button>
            )}
            <OrderList 
              orders={orders} 
              onSelectOrder={(o) => setCurrentOrder(o)}
              onConfirmOrder={handleConfirmOrder}
              onCancelOrder={handleCancelOrder}
            />
          </div>
        )}
      </main>

      {showForm === 'customer' && (
        <CustomerForm 
          customer={editingItem as Customer | null} 
          onSuccess={handleFormSuccess} 
          onCancel={handleFormCancel} 
        />
      )}

      {showForm === 'product' && (
        <ProductForm 
          product={editingItem as Product | null} 
          onSuccess={handleFormSuccess} 
          onCancel={handleFormCancel} 
        />
      )}

      {showForm === 'order' && currentCustomer && (
        <OrderForm 
          customerId={currentCustomer.id}
          customerInfo={{
            name: currentCustomer.name,
            email: currentCustomer.email,
            address: currentCustomer.address,
            phone: currentCustomer.phone
          }}
          onSuccess={handleFormSuccess}
          onCancel={handleFormCancel}
        />
      )}
    </div>
  );
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
