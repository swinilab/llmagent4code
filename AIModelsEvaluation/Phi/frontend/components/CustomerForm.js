import React, { useState } from 'react';
import axios from 'axios';

const CustomerForm = () => {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      await axios.post('/customers', { name, address, phone });
      alert('Customer created successfully!');
    } catch (error) {
      console.error('Error creating customer', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Name: <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <br/>
      <label>
        Address: <input type="text" value={address} onChange={(e) => setAddress(e.target.value)} />
      </label>
      <br/>
      <label>
        Phone: <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} />
      </label>
      <br/>
      <button type="submit">Create Customer</button>
    </form>
  );
};

export default CustomerForm;