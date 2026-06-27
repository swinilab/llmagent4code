// Product Overview Component

import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { apiService } from '../../services/api';

export function ProductOverview() {
  const { setProducts } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getAllProducts();
      if (response.success) {
        setProducts(response.data || []);
      }
    } catch (err) {
      setError('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProducts();
  }, []);

  return (
    <div className="product-overview">
      <h1>Product Management</h1>
      
      {loading && <p>Loading products...</p>}
      {error && <p className="error">{error}</p>}
      
      <div className="overview-actions">
        <button onClick={loadProducts}>Refresh Products</button>
      </div>
    </div>
  );
}

export default ProductOverview;
