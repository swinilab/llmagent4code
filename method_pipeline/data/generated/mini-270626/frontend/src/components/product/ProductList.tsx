// Product List Component

import React from 'react';
import { Product } from '../../types';

interface ProductListProps {
  products: Product[];
  onSelectProduct: (product: Product) => void;
  onDeleteProduct: (id: string) => void;
}

export function ProductList({ products, onSelectProduct, onDeleteProduct }: ProductListProps) {
  return (
    <div className="product-list">
      <h2>Product List</h2>
      {products.length === 0 ? (
        <p>No products found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Category</th>
              <th>Price</th>
              <th>Stock</th>
              <th>Description</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {products.map(product => (
              <tr key={product.id}>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>${product.price.toFixed(2)}</td>
                <td>{product.stock}</td>
                <td>{product.description}</td>
                <td>
                  <button onClick={() => onSelectProduct(product)}>View</button>
                  <button onClick={() => onDeleteProduct(product.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default ProductList;
