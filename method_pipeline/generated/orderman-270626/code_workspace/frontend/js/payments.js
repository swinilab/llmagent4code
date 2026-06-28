/**
 * Payments Module - Handles payment-related UI operations
 * Provides overview, list, and form components for payments
 */

let paymentsCache = [];

/**
 * Load and display all payments
 */
async function loadPayments() {
    const container = document.getElementById('payments-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const statusFilter = document.getElementById('payment-status-filter').value;
        const response = await PaymentAPI.getAll(0, 100, statusFilter || null);
        paymentsCache = response.payments || [];
        
        if (paymentsCache.length === 0) {
            container.innerHTML = '<p class="text-center">No payments found. Make your first payment!</p>';
            return;
        }

        container.innerHTML = paymentsCache.map(payment => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Payment #${payment.id}</h3>
                    <span class="badge badge-${payment.status}">${payment.status}</span>
                </div>
                <div class="card-body">
                    <p><strong>Invoice ID:</strong> ${payment.invoice_id}</p>
                    <p><strong>Customer ID:</strong> ${payment.customer_id}</p>
                    <p><strong>Amount:</strong> $${payment.amount.toFixed(2)}</p>
                    <p><strong>Payment Method:</strong> ${escapeHtml(payment.payment_method)}</p>
                    ${payment.transaction_id ? `<p><strong>Transaction ID:</strong> ${escapeHtml(payment.transaction_id)}</p>` : ''}
                    ${payment.processed_at ? `<p><strong>Processed At:</strong> ${formatDate(payment.processed_at)}</p>` : ''}
                    <p><small>Created: ${formatDate(payment.created_at)}</small></p>
                </div>
                <div class="card-actions">
                    ${payment.status === 'completed' ? `
                        <button class="btn btn-sm btn-warning" onclick="refundPayment(${payment.id})">Refund</button>
                    ` : ''}
                    ${payment.status === 'pending' || payment.status === 'processing' ? `
                        <button class="btn btn-sm btn-danger" onclick="failPayment(${payment.id})">Mark as Failed</button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="viewPaymentDetails(${payment.id})">View Details</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading payments: ${error.message}</div>`;
    }
}

/**
 * Show form for creating a new payment
 */
function showPaymentForm() {
    const container = document.getElementById('payment-form-container');
    container.innerHTML = `
        <h3>Make Payment (Customer Action)</h3>
        <form id="payment-form" onsubmit="handlePaymentSubmit(event)">
            <div class="form-group">
                <label for="payment-invoice">Invoice *</label>
                <select id="payment-invoice" name="invoice_id" required onchange="onInvoiceSelected(this.value)">
                    <option value="">Select Invoice</option>
                </select>
            </div>
            <div class="form-group">
                <label for="payment-customer">Customer *</label>
                <select id="payment-customer" name="customer_id" required>
                    <option value="">Select Customer</option>
                </select>
            </div>
            <div class="form-group">
                <label for="payment-amount">Amount ($) *</label>
                <input type="number" id="payment-amount" name="amount" required step="0.01" min="0.01" readonly>
            </div>
            <div class="form-group">
                <label for="payment-method">Payment Method *</label>
                <select id="payment-method" name="payment_method" required>
                    <option value="">Select Method</option>
                    <option value="credit_card">Credit Card</option>
                    <option value="debit_card">Debit Card</option>
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="paypal">PayPal</option>
                    <option value="cash">Cash</option>
                    <option value="check">Check</option>
                </select>
            </div>
            <div class="form-group">
                <label for="payment-transaction">Transaction ID (Optional)</label>
                <input type="text" id="payment-transaction" name="transaction_id">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Make Payment</button>
                <button type="button" class="btn btn-secondary" onclick="hidePaymentForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
    
    populateIssuedInvoicesDropdown();
    populateCustomersDropdown();
}

/**
 * Hide the payment form
 */
function hidePaymentForm() {
    document.getElementById('payment-form-container').style.display = 'none';
    document.getElementById('payment-form')?.reset();
}

/**
 * Populate issued invoices dropdown (invoices that can be paid)
 */
async function populateIssuedInvoicesDropdown() {
    try {
        const response = await InvoiceAPI.getAll(0, 100);
        const select = document.getElementById('payment-invoice');
        const issuedInvoices = response.invoices.filter(i => ['issued', 'overdue'].includes(i.status));
        
        select.innerHTML = '<option value="">Select Invoice</option>' + 
            issuedInvoices.map(i => `<option value="${i.id}" data-amount="${i.amount}" data-customer="${i.customer_id}">${i.invoice_number} - $${i.amount.toFixed(2)} (${i.status})</option>`).join('');
    } catch (error) {
        console.error('Error loading invoices:', error);
    }
}

/**
 * Populate customers dropdown
 */
async function populateCustomersDropdown() {
    try {
        const response = await CustomerAPI.getAll(0, 100);
        const select = document.getElementById('payment-customer');
        select.innerHTML = '<option value="">Select Customer</option>' + 
            response.customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${escapeHtml(c.email)})</option>`).join('');
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

/**
 * Handle invoice selection - auto-fill amount and customer
 */
async function onInvoiceSelected(invoiceId) {
    if (!invoiceId) return;
    
    try {
        const invoice = await InvoiceAPI.getById(parseInt(invoiceId));
        
        // Auto-fill amount from invoice
        document.getElementById('payment-amount').value = invoice.amount.toFixed(2);
        
        // Auto-fill customer from invoice
        const customerSelect = document.getElementById('payment-customer');
        customerSelect.value = invoice.customer_id;
    } catch (error) {
        console.error('Error loading invoice:', error);
    }
}

/**
 * Handle payment form submission
 */
async function handlePaymentSubmit(event) {
    event.preventDefault();
    
    const data = {
        invoice_id: parseInt(document.getElementById('payment-invoice').value),
        customer_id: parseInt(document.getElementById('payment-customer').value),
        amount: parseFloat(document.getElementById('payment-amount').value),
        payment_method: document.getElementById('payment-method').value,
        transaction_id: document.getElementById('payment-transaction').value || null
    };

    try {
        await PaymentAPI.create(data);
        showMessage('Payment processed successfully!', 'success');
        hidePaymentForm();
        loadPayments();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Refund a payment
 */
function refundPayment(id) {
    showModal(
        'Refund Payment',
        'Are you sure you want to refund this payment? This will also revert the invoice status.',
        async () => {
            try {
                await PaymentAPI.refund(id);
                showMessage('Payment refunded!', 'success');
                loadPayments();
            } catch (error) {
                showMessage(`Error: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * Mark payment as failed
 */
function failPayment(id) {
    showModal(
        'Mark Payment as Failed',
        'Are you sure you want to mark this payment as failed?',
        async () => {
            try {
                await PaymentAPI.fail(id);
                showMessage('Payment marked as failed!', 'success');
                loadPayments();
            } catch (error) {
                showMessage(`Error: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * View payment details
 */
async function viewPaymentDetails(id) {
    try {
        const payment = await PaymentAPI.getById(id);
        alert(`Payment #${payment.id}\nStatus: ${payment.status}\nAmount: $${payment.amount.toFixed(2)}\nMethod: ${payment.payment_method}`);
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Get payment by ID from cache
 */
function getPaymentById(id) {
    return paymentsCache.find(p => p.id === id);
}
