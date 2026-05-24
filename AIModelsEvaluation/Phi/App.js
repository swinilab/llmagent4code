import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import CustomerList from './components/CustomerList';
import CustomerForm from './components/CustomerForm';

function App() {
  return (
    <Router>
      <Switch>
        <Route path="/customers" exact component={CustomerList} />
        <Route path="/create-customer" exact component={CustomerForm} />
        {/* Repeat similar structures for Order, Product, Payment, Invoice */}
      </Switch>
    </Router>
  );
}

export default App;