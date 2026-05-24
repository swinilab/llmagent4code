import dotenv from 'dotenv';
import express from 'express';
import bodyParser from 'body-parser';
import paymentRoutes from './src/payment/PaymentRoutes';
import orderRoutes from './src/order/OrderRoutes';
import productRoutes from './src/product/ProductRoutes';
import customerRoutes from './src/customer/CustomerRoutes';
import invoiceRoutes from './src/invoice/InvoiceRoutes';
import cors from 'cors';

// Load environment variables
dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

app.use(
	cors({
		origin: [
			'http://localhost:5172',
			'http://localhost:5173',
			'http://localhost:5174',
		],
		credentials: true,
	})
);

app.use(bodyParser.json());

// Health check endpoint
app.get('/api/ping', (req, res) => {
    res.status(200).json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        message: 'Server is healthy'
    });
});

app.use('/api/payments', paymentRoutes);
app.use('/api/orders', orderRoutes);
app.use('/api/products', productRoutes);
app.use('/api/customers', customerRoutes);
app.use('/api/invoices', invoiceRoutes);

app.listen(port, () => {
	console.log(`Server is running at http://localhost:${port}/api/`);
});
