/**
 * Customers Module - Handles customer-related UI operations
 * Provides overview, list, and form components for customers
 */

let customersCache = [];

/**
 * Load and display all customers
 */
async function loadCustomers() {
    const container = document.getElementById('customers-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const response = await CustomerAPI.getAll(0, 100);
        customersCache = response.customers || [];
        
        if (customersCache.length === 0) {
            container.innerHTML = '<p class="text-center">No customers found. Add your first customer!</p>';
            return;
        }

        container.innerHTML = customersCache.map(customer => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(customer.name)}</h3>
                    <span class="badge badge-${customer.role}">${customer.role}</span>
                </div>
                <div class="card-body">
                    <p><strong>Email:</strong> ${escapeHtml(customer.email)}</p>
                    <p><strong>Phone:</strong> ${escapeHtml(customer.phone)}</p>
                    <p><strong>Address:</strong> ${escapeHtml(customer.address)}</p>
                    ${customer.banking_details ? `<p><strong>Banking:</strong> ${escapeHtml(customer.banking_details)}</p>` : ''}
                    <p><strong>Orders:</strong> ${customer.order_history ? customer.order_history.length : 0}</p>
                    <p><small>Created: ${formatDate(customer.created_at)}</small></p>
                </div>
                <div class="card-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editCustomer(${customer.id})">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="confirmDeleteCustomer(${customer.id}, '${escapeHtml(customer.name)}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading customers: ${error.message}</div>`;
    }
}

/**
 * Show form for creating a new customer
 */
function showCustomerForm() {
    const container = document.getElementById('customer-form-container');
    container.innerHTML = `
        <h3>${arguments[0] === 'edit' ? 'Edit Customer' : 'Add New Customer'}</h3>
        <form id="customer-form" onsubmit="handleCustomerSubmit(event)">
            <input type="hidden" id="customer-id">
            <div class="form-group">
                <label for="customer-name">Full Name *</label>
                <input type="text" id="customer-name" name="name" required>
            </div>
            <div class="form-group">
                <label for="customer-email">Email *</label>
                <input type="email" id="customer-email" name="email" required>
            </div>
            <div class="form-group">
                <label for="customer-phone">Phone *</label>
                <input type="tel" id="customer-phone" name="phone" required pattern="[0-9\-]{7,20}">
            </div>
            <div class="form-group">
                <label for="customer-address">Address *</label>
                <textarea id="customer-address" name="address" required></textarea>
            </div>
            <div class="form-group">
                <label for="customer-banking">Banking Details</label>
                <textarea id="customer-banking" name="banking_details"></textarea>
            </div>
            <div class="form-group">
                <label for="customer-role">Role *</label>
                <select id="customer-role" name="role" required>
                    <option value="customer">Customer</option>
                    <option value="order_staff">Order Staff</option>
                    <option value="accountant">Accountant</option>
                </select>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">${arguments[0] === 'edit' ? 'Update' : 'Create'} Customer</button>
                <button type="button" class="btn btn-secondary" onclick="hideCustomerForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
    
    if (arguments[0] === 'edit' && arguments[1]) {
        fillCustomerForm(arguments[1]);
    }
}

/**
 * Hide the customer form
 */
function hideCustomerForm() {
    document.getElementById('customer-form-container').style.display = 'none';
    document.getElementById('customer-form')?.reset();
}

/**
 * Fill form with customer data for editing
 */
function fillCustomerForm(customer) {
    document.getElementById('customer-id').value = customer.id;
    document.getElementById('customer-name').value = customer.name;
    document.getElementById('customer-email').value = customer.email;
    document.getElementById('customer-phone').value = customer.phone;
    document.getElementById('customer-address').value = customer.address;
    document.getElementById('customer-banking').value = customer.banking_details || '';
    document.getElementById('customer-role').value = customer.role;
}

/**
 * Handle customer form submission
 */
async function handleCustomerSubmit(event) {
    event.preventDefault();
    
    const id = document.getElementById('customer-id').value;
    const data = {
        name: document.getElementById('customer-name').value,
        email: document.getElementById('customer-email').value,
        phone: document.getElementById('customer-phone').value,
        address: document.getElementById('customer-address').value,
        banking_details: document.getElementById('customer-banking').value || null,
        role: document.getElementById('customer-role').value
    };

    try {
        if (id) {
            await CustomerAPI.update(parseInt(id), data);
            showMessage('Customer updated successfully!', 'success');
        } else {
            await CustomerAPI.create(data);
            showMessage('Customer created successfully!', 'success');
        }
        hideCustomerForm();
        loadCustomers();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Edit an existing customer
 */
async function editCustomer(id) {
    try {
        const customer = await CustomerAPI.getById(id);
        showCustomerForm('edit', customer);
    } catch (error) {
        showMessage(`Error loading customer: ${error.message}`, 'error');
    }
}

/**
 * Confirm and delete a customer
 */
function confirmDeleteCustomer(id, name) {
    showModal(
        'Delete Customer',
        `Are you sure you want to delete customer "${name}"? This action cannot be undone.`,
        async () => {
            try {
                await CustomerAPI.delete(id);
                showMessage('Customer deleted successfully!', 'success');
                loadCustomers();
            } catch (error) {
                showMessage(`Error deleting customer: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * Get customer by ID from cache
 */
function getCustomerById(id) {
    return customersCache.find(c => c.id === id);
}
