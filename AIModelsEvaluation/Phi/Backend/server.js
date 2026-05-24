const express = require('express');
const { Sequelize } = require('sequelize');

const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: './database.sqlite'
});

const app = express();
app.use(express.json());

// Import models and sync database
require('./Backend/models')(sequelize);

// Set up routes
app.use('/customers', require('./routes/customerRoutes'));
app.use('/orders', require('./routes/orderRoutes'));
app.use('/products', require('./routes/productRoutes'));
app.use('/payments', require('./routes/paymentRoutes'));
app.use('/invoices', require('./routes/invoiceRoutes'));

sequelize.sync().then(() => {
  app.listen(3000, () => {
    console.log('Server is running on port 3000');
  });
});