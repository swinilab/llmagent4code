import React, { useEffect, useState } from 'react';
import axios from 'axios';

const CustomerList = () => {
  const [customers, setCustomers] = useState([]);

  useEffect(() => {
    axios.get('/customers')
      .then(response => setCustomers(response.data))
      .catch(error => console.error('Error fetching customers', error));
  }, []);

  return <CustomerOverview customers={customers} />;
};