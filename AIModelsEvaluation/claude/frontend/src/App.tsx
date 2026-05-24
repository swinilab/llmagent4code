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