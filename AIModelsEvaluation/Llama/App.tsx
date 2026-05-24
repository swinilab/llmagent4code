// App.tsx

import React from 'react';
import { BrowserRouter, Route, Switch } from 'react-router-dom';
import CustomerList from './components/customer-list';
import OrderList from './components/order-list';
import ProductList from './components/product-list';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Switch>
        <Route path="/customers" component={CustomerList} />
        <Route path="/orders" component={OrderList} />
        <Route path="/products" component={ProductList} />
      </Switch>
    </BrowserRouter>
  );
};

export default App;