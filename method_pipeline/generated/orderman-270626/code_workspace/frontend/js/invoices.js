/**
 * Invoices Module - Handles invoice-related UI operations
 * Provides overview, list, and form components for invoices
 */

let invoicesCache = [];

/**
 * Load and display all invoices
 */
async function loadInvoices() {
    const container = document.getElementById('invoices-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const statusFilter = document.getElementById('invoice-status-filter').value;
        const response = await InvoiceAPI.getAll(0, 100, statusFilter || null);
        invoicesCache = response.invoices || [];
        
        if (invoicesCache.length === 0) {
            container.innerHTML = '<p class="text-center">No invoices found. Create your first invoice!</p>';
            return;
        }

        container.innerHTML = invoicesCache.map(invoice => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(invoice.invoice_number)}</h3>
                    <span class="badge badge-${invoice.status}">${invoice.status}</span>
                </div>
                <div class="card-body">
                    <p><strong>Order ID:</strong> ${invoice.order_id}</p>
                    <p><strong>Customer ID:</strong> ${invoice.customer_id}</p>
                    <p><strong>Amount:</strong> $${invoice.amount.toFixed(2)}</p>
                    <p><strong>Billing Address:</strong> ${escapeHtml(invoice.billing_address)}</p>
                    <p><strong>Due Date:</strong> ${formatDate(invoice.due_date)}</p>
                    ${invoice.paid_at ? `<p><strong>Paid At:</strong> ${formatDate(invoice.paid_at)}</p>` : ''}
                    <p><small>Created: ${formatDate(invoice.created_at)}</small></p>
                </div>
                <div class="card-actions">
                    ${invoice.status === 'issued' || invoice.status === 'overdue' ? `
                        <button class="btn btn-sm btn-success" onclick="markInvoicePaid(${invoice.id})">Mark as Paid</button>
                    ` : ''}
                    ${invoice.status === 'issued' ? `
                        <button class="btn btn-sm btn-danger" onclick="cancelInvoice(${invoice.id})">Cancel Invoice</button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="viewInvoiceDetails(${invoice.id})">View Details</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading invoices: ${error.message}</div>`;
    }
}

/**
 * Show form for creating a new invoice
 */
function showInvoiceForm() {
    const container = document.getElementById('invoice-form-container');
    container.innerHTML = `
        <h3>Create New Invoice (Accountant Action)</h3>
        <form id="invoice-form" onsubmit="handleInvoiceSubmit(event)">
            <div class="form-group">
                <label for="invoice-order">Order *</label>
                <select id="invoice-order" name="order_id" required onchange="onOrderSelected(this.value)">
                    <option value="">Select Order</option>
                </select>
            </div>
            <div class="form-group">
                <label for="invoice-customer">Customer *</label>
                <select id="invoice-customer" name="customer_id" required>
                    <option value="">Select Customer</option>
                </select>
            </div>
            <div class="form-group">
                <label for="invoice-amount">Amount ($) *</label>
                <input type="number" id="invoice-amount" name="amount" required step="0.01" min="0.01">
            </div>
            <div class="form-group">
                <label for="invoice-due-date">Due Date *</label>
                <input type="date" id="invoice-due-date" name="due_date" required>
            </div>
            <div class="form-group">
                <label for="invoice-billing">Billing Address *</label>
                <textarea id="invoice-billing" name="billing_address" required></textarea>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Create Invoice</button>
                <button type="button" class="btn btn-secondary" onclick="hideInvoiceForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
    
    // Set default due date to 30 days from now
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 30);
    document.getElementById('invoice-due-date').value = dueDate.toISOString().split('T')[0];
    
    populatePendingOrdersDropdown();
    populateCustomersDropdown();
}

/**
 * Hide the invoice form
 */
function hideInvoiceForm() {
    document.getElementById('invoice-form-container').style.display = 'none';
    document.getElementById('invoice-form')?.reset();
}

/**
 * Populate pending orders dropdown (orders that can be invoiced)
 * Only ACCEPTED orders can be invoiced per business workflow
 */
async function populatePendingOrdersDropdown() {
    try {
        const response = await OrderAPI.getAll(0, 100);
        const select = document.getElementById('invoice-order');
        // FIX: Only show accepted orders for invoicing (per business workflow)
        const acceptedOrders = response.orders.filter(o => o.status === 'accepted');
        
        select.innerHTML = '<option value="">Select Order</option>' + 
            acceptedOrders.map(o => `<option value="${o.id}" data-amount="${o.total_amount}" data-customer="${o.customer_id}">Order #${o.id} - $${o.total_amount.toFixed(2)} (${o.status})</option>`).join('');
    } catch (error) {
        console.error('Error loading orders:', error);
    }
}

/**
 * Populate customers dropdown
 */
async function populateCustomersDropdown() {
    try {
        const response = await CustomerAPI.getAll(0, 100);
        const select = document.getElementById('invoice-customer');
        select.innerHTML = '<option value="">Select Customer</option>' + 
            response.customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${escapeHtml(c.email)})</option>`).join('');
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

/**
 * Handle order selection - auto-fill customer and amount
 */
async function onOrderSelected(orderId) {
    if (!orderId) return;
    
    try {
        const order = await OrderAPI.getById(parseInt(orderId));
        const select = document.getElementById('invoice-order');
        const option = select.options[select.selectedIndex];
        
        // Auto-fill amount from order total
        document.getElementById('invoice-amount').value = order.total_amount.toFixed(2);
        
        // Auto-fill customer from order
        const customerSelect = document.getElementById('invoice-customer');
        customerSelect.value = order.customer_id;
        
        // Auto-fill billing address from order shipping address
        document.getElementById('invoice-billing').value = order.shipping_address;
    } catch (error) {
        console.error('Error loading order:', error);
    }
}

/**
 * Handle invoice form submission
 */
async function handleInvoiceSubmit(event) {
    event.preventDefault();
    
    const data = {
        order_id: parseInt(document.getElementById('invoice-order').value),
        customer_id: parseInt(document.getElementById('invoice-customer').value),
        amount: parseFloat(document.getElementById('invoice-amount').value),
        due_date: new Date(document.getElementById('invoice-due-date').value).toISOString(),
        billing_address: document.getElementById('invoice-billing').value
    };

    try {
        await InvoiceAPI.create(data);
        showMessage('Invoice created successfully!', 'success');
        hideInvoiceForm();
        loadInvoices();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Mark invoice as paid
 */
async function markInvoicePaid(id) {
    try {
        await InvoiceAPI.markPaid(id);
        showMessage('Invoice marked as paid!', 'success');
        loadInvoices();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Cancel an invoice
 */
function cancelInvoice(id) {
    showModal(
        'Cancel Invoice',
        'Are you sure you want to cancel this invoice? This action cannot be undone.',
        async () => {
            try {
                await InvoiceAPI.cancel(id);
                showMessage('Invoice cancelled!', 'success');
                loadInvoices();
            } catch (error) {
                showMessage(`Error: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * View invoice details
 */
async function viewInvoiceDetails(id) {
    try {
        const invoice = await InvoiceAPI.getById(id);
        alert(`Invoice: ${invoice.invoice_number}\nStatus: ${invoice.status}\nAmount: $${invoice.amount.toFixed(2)}\nDue: ${formatDate(invoice.due_date)}`);
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Get invoice by ID from cache
 */
function getInvoiceById(id) {
    return invoicesCache.find(i => i.id === id);
}
