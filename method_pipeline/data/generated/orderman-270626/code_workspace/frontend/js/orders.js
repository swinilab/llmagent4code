/**
 * Orders Module - Handles order-related UI operations
 * Provides overview, list, and form components for orders
 * Implements the complete order workflow
 */

let ordersCache = [];

/**
 * Load and display all orders
 */
async function loadOrders() {
    const container = document.getElementById('orders-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const statusFilter = document.getElementById('order-status-filter').value;
        const response = await OrderAPI.getAll(0, 100, statusFilter || null);
        ordersCache = response.orders || [];
        
        if (ordersCache.length === 0) {
            container.innerHTML = '<p class="text-center">No orders found. Place your first order!</p>';
            return;
        }

        container.innerHTML = ordersCache.map(order => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">Order #${order.id}</h3>
                    <span class="badge badge-${order.status}">${order.status}</span>
                </div>
                <div class="card-body">
                    <p><strong>Customer ID:</strong> ${order.customer_id}</p>
                    <p><strong>Shipping Address:</strong> ${escapeHtml(order.shipping_address)}</p>
                    <p><strong>Total Amount:</strong> $${order.total_amount.toFixed(2)}</p>
                    <p><strong>Items:</strong> ${order.items.length}</p>
                    ${order.notes ? `<p><strong>Notes:</strong> ${escapeHtml(order.notes)}</p>` : ''}
                    ${order.invoice_id ? `<p><strong>Invoice ID:</strong> ${order.invoice_id}</p>` : ''}
                    <p><small>Created: ${formatDate(order.created_at)}</small></p>
                    ${order.accepted_at ? `<p><small>Accepted: ${formatDate(order.accepted_at)}</small></p>` : ''}
                    ${order.shipped_at ? `<p><small>Shipped: ${formatDate(order.shipped_at)}</small></p>` : ''}
                    ${order.completed_at ? `<p><small>Completed: ${formatDate(order.completed_at)}</small></p>` : ''}
                    
                    <div class="mt-2">
                        <strong>Order Items:</strong>
                        <ul class="mt-1">
                            ${order.items.map(item => `
                                <li>${escapeHtml(item.product_name)} - ${item.quantity} x $${item.unit_price.toFixed(2)} = $${item.subtotal.toFixed(2)}</li>
                            `).join('')}
                        </ul>
                    </div>
                </div>
                <div class="card-actions">
                    ${order.status === 'pending' ? `
                        <button class="btn btn-sm btn-success" onclick="acceptOrder(${order.id})">Accept Order</button>
                    ` : ''}
                    ${order.status === 'paid' ? `
                        <button class="btn btn-sm btn-primary" onclick="shipOrder(${order.id})">Ship Order</button>
                    ` : ''}
                    ${order.status === 'shipped' ? `
                        <button class="btn btn-sm btn-success" onclick="completeOrder(${order.id})">Complete Order</button>
                    ` : ''}
                    ${['pending', 'accepted', 'invoiced'].includes(order.status) ? `
                        <button class="btn btn-sm btn-danger" onclick="cancelOrder(${order.id})">Cancel Order</button>
                    ` : ''}
                    <button class="btn btn-sm btn-secondary" onclick="viewOrderDetails(${order.id})">View Details</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading orders: ${error.message}</div>`;
    }
}

/**
 * Show form for creating a new order
 */
function showOrderForm() {
    const container = document.getElementById('order-form-container');
    container.innerHTML = `
        <h3>${arguments[0] === 'edit' ? 'Edit Order' : 'Place New Order'}</h3>
        <form id="order-form" onsubmit="handleOrderSubmit(event)">
            <input type="hidden" id="order-id">
            <div class="form-group">
                <label for="order-customer">Customer *</label>
                <select id="order-customer" name="customer_id" required>
                    <option value="">Select Customer</option>
                </select>
            </div>
            <div class="form-group">
                <label for="order-shipping">Shipping Address *</label>
                <textarea id="order-shipping" name="shipping_address" required></textarea>
            </div>
            <div class="form-group">
                <label>Order Items *</label>
                <div id="order-items-container" class="order-items-container">
                    <div class="order-item-row">
                        <select class="item-product" onchange="updateItemPrice(this)">
                            <option value="">Select Product</option>
                        </select>
                        <input type="number" class="item-quantity" placeholder="Qty" min="1" value="1" onchange="calculateItemSubtotal(this)">
                        <input type="number" class="item-price" placeholder="Price" min="0.01" step="0.01" onchange="calculateItemSubtotal(this)">
                        <input type="number" class="item-subtotal" placeholder="Subtotal" readonly>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removeOrderItem(this)">×</button>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-secondary" onclick="addOrderItem()">+ Add Item</button>
            </div>
            <div class="form-group">
                <label for="order-notes">Notes</label>
                <textarea id="order-notes" name="notes"></textarea>
            </div>
            <div class="form-group">
                <label>Total Amount</label>
                <input type="number" id="order-total" readonly step="0.01">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">${arguments[0] === 'edit' ? 'Update' : 'Place'} Order</button>
                <button type="button" class="btn btn-secondary" onclick="hideOrderForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
    
    // Populate customer and product dropdowns
    populateCustomerDropdown();
    populateProductDropdown();
    
    if (arguments[0] === 'edit' && arguments[1]) {
        fillOrderForm(arguments[1]);
    }
}

/**
 * Hide the order form
 */
function hideOrderForm() {
    document.getElementById('order-form-container').style.display = 'none';
    document.getElementById('order-form')?.reset();
}

/**
 * Populate customer dropdown
 */
async function populateCustomerDropdown() {
    try {
        const response = await CustomerAPI.getAll(0, 100);
        const select = document.getElementById('order-customer');
        select.innerHTML = '<option value="">Select Customer</option>' + 
            response.customers.map(c => `<option value="${c.id}">${escapeHtml(c.name)} (${escapeHtml(c.email)})</option>`).join('');
    } catch (error) {
        console.error('Error loading customers:', error);
    }
}

/**
 * Populate product dropdown in order items
 */
async function populateProductDropdown() {
    try {
        const response = await ProductAPI.getAll(0, 100);
        const selects = document.querySelectorAll('.item-product');
        const options = '<option value="">Select Product</option>' + 
            response.products.map(p => `<option value="${p.id}" data-price="${p.price}" data-name="${escapeHtml(p.name)}">${escapeHtml(p.name)} - $${p.price.toFixed(2)}</option>`).join('');
        selects.forEach(select => select.innerHTML = options);
    } catch (error) {
        console.error('Error loading products:', error);
    }
}

/**
 * Add a new order item row
 */
function addOrderItem() {
    const container = document.getElementById('order-items-container');
    const row = document.createElement('div');
    row.className = 'order-item-row';
    row.innerHTML = `
        <select class="item-product" onchange="updateItemPrice(this)">
            <option value="">Select Product</option>
        </select>
        <input type="number" class="item-quantity" placeholder="Qty" min="1" value="1" onchange="calculateItemSubtotal(this)">
        <input type="number" class="item-price" placeholder="Price" min="0.01" step="0.01" onchange="calculateItemSubtotal(this)">
        <input type="number" class="item-subtotal" placeholder="Subtotal" readonly>
        <button type="button" class="btn btn-sm btn-danger" onclick="removeOrderItem(this)">×</button>
    `;
    container.appendChild(row);
    populateProductDropdown();
}

/**
 * Remove an order item row
 */
function removeOrderItem(button) {
    const container = document.getElementById('order-items-container');
    if (container.children.length > 1) {
        button.parentElement.remove();
        calculateOrderTotal();
    }
}

/**
 * Update item price when product is selected
 */
function updateItemPrice(select) {
    const option = select.options[select.selectedIndex];
    const row = select.parentElement;
    const priceInput = row.querySelector('.item-price');
    const nameInput = row.querySelector('.item-product-name');
    
    if (option.dataset.price) {
        priceInput.value = option.dataset.price;
        calculateItemSubtotal(priceInput);
    }
}

/**
 * Calculate item subtotal
 */
function calculateItemSubtotal(input) {
    const row = input.parentElement;
    const quantity = parseFloat(row.querySelector('.item-quantity').value) || 0;
    const price = parseFloat(row.querySelector('.item-price').value) || 0;
    const subtotal = quantity * price;
    row.querySelector('.item-subtotal').value = subtotal.toFixed(2);
    calculateOrderTotal();
}

/**
 * Calculate order total
 */
function calculateOrderTotal() {
    const subtotals = document.querySelectorAll('.item-subtotal');
    let total = 0;
    subtotals.forEach(input => {
        total += parseFloat(input.value) || 0;
    });
    document.getElementById('order-total').value = total.toFixed(2);
}

/**
 * Handle order form submission
 */
async function handleOrderSubmit(event) {
    event.preventDefault();
    
    // Collect order items
    const items = [];
    const itemRows = document.querySelectorAll('.order-item-row');
    itemRows.forEach(row => {
        const productSelect = row.querySelector('.item-product');
        const quantity = parseInt(row.querySelector('.item-quantity').value);
        const unitPrice = parseFloat(row.querySelector('.item-price').value);
        const subtotal = parseFloat(row.querySelector('.item-subtotal').value);
        
        if (productSelect.value && quantity > 0 && unitPrice > 0) {
            items.push({
                product_id: parseInt(productSelect.value),
                product_name: productSelect.options[productSelect.selectedIndex].text.split(' - ')[0],
                quantity: quantity,
                unit_price: unitPrice,
                subtotal: subtotal
            });
        }
    });
    
    if (items.length === 0) {
        showMessage('Please add at least one item to the order', 'error');
        return;
    }
    
    const data = {
        customer_id: parseInt(document.getElementById('order-customer').value),
        shipping_address: document.getElementById('order-shipping').value,
        items: items,
        total_amount: parseFloat(document.getElementById('order-total').value),
        notes: document.getElementById('order-notes').value || null
    };

    try {
        await OrderAPI.create(data);
        showMessage('Order placed successfully!', 'success');
        hideOrderForm();
        loadOrders();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Accept an order (Order Staff action)
 */
async function acceptOrder(id) {
    try {
        await OrderAPI.accept(id);
        showMessage('Order accepted!', 'success');
        loadOrders();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Ship an order (Order Staff action after payment)
 */
async function shipOrder(id) {
    try {
        await OrderAPI.ship(id);
        showMessage('Order shipped!', 'success');
        loadOrders();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Complete an order (Order Staff action after shipping)
 */
async function completeOrder(id) {
    try {
        await OrderAPI.complete(id);
        showMessage('Order completed!', 'success');
        loadOrders();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Cancel an order
 */
async function cancelOrder(id) {
    showModal(
        'Cancel Order',
        'Are you sure you want to cancel this order? This action cannot be undone.',
        async () => {
            try {
                await OrderAPI.cancel(id);
                showMessage('Order cancelled!', 'success');
                loadOrders();
            } catch (error) {
                showMessage(`Error: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * View order details
 */
async function viewOrderDetails(id) {
    try {
        const order = await OrderAPI.getById(id);
        alert(`Order #${order.id}\nStatus: ${order.status}\nTotal: $${order.total_amount.toFixed(2)}\nItems: ${order.items.length}`);
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}
