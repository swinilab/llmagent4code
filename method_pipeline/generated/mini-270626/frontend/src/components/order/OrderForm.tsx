// Order Form Component - Create New Order

import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { apiService } from '../../services/api';
import { Product, OrderItem } from '../../types';

interface OrderFormProps {
  customerId: string;
  customerInfo: { name: string; email: string; address: string; phone: string };
  onSuccess: () => void;
  onCancel: () => void;
}

export function OrderForm({ customerId, customerInfo, onSuccess, onCancel }: OrderFormProps) {
  const { sessionId } = useApp();
  const [products, setProducts] = useState<Product[]>([]);
  const [cartItems, setCartItems] = useState<OrderItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [quantity, setQuantity] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const response = await apiService.getAllProducts();
      if (response.success) {
        setProducts(response.data || []);
      }
    } catch (err) {
      setError('Failed to load products');
    }
  };

  const addToCart = () => {
    const product = products.find(p => p.id === selectedProduct);
    if (!product) return;

    const existingItem = cartItems.find(item => item.productId === product.id);
    if (existingItem) {
      setCartItems(cartItems.map(item =>
        item.productId === product.id
          ? { ...item, quantity: item.quantity + quantity, totalPrice: (item.quantity + quantity) * item.unitPrice }
          : item
      ));
    } else {
      setCartItems([...cartItems, {
        productId: product.id,
        productName: product.name,
        quantity,
        unitPrice: product.price,
        totalPrice: quantity * product.price
      }]);
    }
    setSelectedProduct('');
    setQuantity(1);
  };

  const removeFromCart = (productId: string) => {
    setCartItems(cartItems.filter(item => item.productId !== productId));
  };

  const calculateTotal = () => {
    const subtotal = cartItems.reduce((sum, item) => sum + item.totalPrice, 0);
    const tax = subtotal * 0.1;
    return { subtotal, tax, total: subtotal + tax };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (cartItems.length === 0) {
      setError('Please add at least one item to the order');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await apiService.createOrder({
        customerId,
        customerInfo,
        items: cartItems,
        sessionId
      });
      onSuccess();
    } catch (err) {
      setError('Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  const totals = calculateTotal();

  return (
    <div className="order-form">
      <h2>Create New Order</h2>
      <p>Customer: {customerInfo.name}</p>
      {error && <p className="error">{error}</p>}
      
      <div className="add-to-cart">
        <h3>Add Products</h3>
        <select value={selectedProduct} onChange={(e) => setSelectedProduct(e.target.value)}>
          <option value="">Select a product</option>
          {products.map(product => (
            <option key={product.id} value={product.id}>
              {product.name} - ${product.price} (Stock: {product.stock})
            </option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          value={quantity}
          onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
        />
        <button type="button" onClick={addToCart} disabled={!selectedProduct}>Add to Cart</button>
      </div>

      <div className="cart-items">
        <h3>Cart Items</h3>
        {cartItems.length === 0 ? (
          <p>Cart is empty</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Price</th>
                <th>Quantity</th>
                <th>Total</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {cartItems.map(item => (
                <tr key={item.productId}>
                  <td>{item.productName}</td>
                  <td>${item.unitPrice.toFixed(2)}</td>
                  <td>{item.quantity}</td>
                  <td>${item.totalPrice.toFixed(2)}</td>
                  <td>
                    <button onClick={() => removeFromCart(item.productId)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="order-totals">
        <p>Subtotal: ${totals.subtotal.toFixed(2)}</p>
        <p>Tax (10%): ${totals.tax.toFixed(2)}</p>
        <p><strong>Total: ${totals.total.toFixed(2)}</strong></p>
      </div>

      <div className="form-actions">
        <button onClick={handleSubmit} disabled={loading || cartItems.length === 0}>
          {loading ? 'Creating...' : 'Place Order'}
        </button>
        <button type="button" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default OrderForm;
