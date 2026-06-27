/**
 * Main Application Module - Handles navigation, initialization, and utility functions
 * Ties together all frontend components
 */

// ============================================================================
// Navigation and View Management
// ============================================================================

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    loadDashboard();
});

/**
 * Set up navigation event listeners
 */
function initializeNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons and views
            navButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.view').forEach(view => view.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Show corresponding view
            const viewName = this.dataset.view;
            document.getElementById(`${viewName}-view`).classList.add('active');
            
            // Load data for the view
            loadView(viewName);
        });
    });
}

/**
 * Load data for a specific view
 */
function loadView(viewName) {
    // Hide all form containers first
    hideAllForms();
    
    switch(viewName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'customers':
            loadCustomers();
            break;
        case 'products':
            loadProducts();
            break;
        case 'orders':
            loadOrders();
            break;
        case 'invoices':
            loadInvoices();
            break;
        case 'payments':
            loadPayments();
            break;
    }
}

/**
 * Hide all form containers
 */
function hideAllForms() {
    const formContainers = document.querySelectorAll('.form-container');
    formContainers.forEach(container => {
        container.style.display = 'none';
        const form = container.querySelector('form');
        if (form) form.reset();
    });
}

// ============================================================================
// Dashboard
// ============================================================================

/**
 * Load dashboard statistics
 */
async function loadDashboard() {
    try {
        // Load all statistics in parallel
        const [customers, products, orders, invoices, payments] = await Promise.all([
            CustomerAPI.getAll(0, 1).catch(() => ({ total: 0 })),
            ProductAPI.getAll(0, 1).catch(() => ({ total: 0 })),
            OrderAPI.getAll(0, 1).catch(() => ({ total: 0 })),
            InvoiceAPI.getAll(0, 1).catch(() => ({ total: 0 })),
            PaymentAPI.getAll(0, 1).catch(() => ({ total: 0 }))
        ]);

        // Update stat numbers with animation
        animateNumber('stat-customers', customers.total || 0);
        animateNumber('stat-products', products.total || 0);
        animateNumber('stat-orders', orders.total || 0);
        animateNumber('stat-invoices', invoices.total || 0);
        animateNumber('stat-payments', payments.total || 0);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

/**
 * Animate number counting
 */
function animateNumber(elementId, target) {
    const element = document.getElementById(elementId);
    const current = parseInt(element.textContent) || 0;
    const increment = Math.ceil(target / 20);
    
    if (current < target) {
        element.textContent = Math.min(current + increment, target);
        setTimeout(() => animateNumber(elementId, target), 50);
    } else {
        element.textContent = target;
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Show a message to the user
 */
function showMessage(message, type = 'info') {
    // Create message element
    const messageEl = document.createElement('div');
    messageEl.className = type === 'error' ? 'error-message' : 'success-message';
    messageEl.textContent = message;
    messageEl.style.position = 'fixed';
    messageEl.style.top = '20px';
    messageEl.style.right = '20px';
    messageEl.style.zIndex = '9999';
    messageEl.style.minWidth = '300px';
    
    document.body.appendChild(messageEl);
    
    // Remove after 5 seconds
    setTimeout(() => {
        messageEl.remove();
    }, 5000);
}

/**
 * Show modal dialog
 */
function showModal(title, message, onConfirm) {
    const modal = document.getElementById('modal');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    
    const confirmBtn = document.getElementById('modal-confirm-btn');
    
    // Remove old event listeners
    const newBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);
    
    // Add new event listener
    newBtn.addEventListener('click', function() {
        closeModal();
        if (onConfirm) onConfirm();
    });
    
    modal.style.display = 'flex';
}

/**
 * Close modal dialog
 */
function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('modal');
    if (event.target === modal) {
        closeModal();
    }
});

// ============================================================================
// Global Functions (exposed to HTML)
// ============================================================================

// Customer functions
window.showCustomerForm = showCustomerForm;
window.hideCustomerForm = hideCustomerForm;
window.editCustomer = editCustomer;
window.confirmDeleteCustomer = confirmDeleteCustomer;
window.handleCustomerSubmit = handleCustomerSubmit;
window.loadCustomers = loadCustomers;

// Product functions
window.showProductForm = showProductForm;
window.hideProductForm = hideProductForm;
window.editProduct = editProduct;
window.adjustStock = adjustStock;
window.confirmDeleteProduct = confirmDeleteProduct;
window.handleProductSubmit = handleProductSubmit;
window.handleStockAdjust = handleStockAdjust;
window.loadProducts = loadProducts;

// Order functions
window.showOrderForm = showOrderForm;
window.hideOrderForm = hideOrderForm;
window.acceptOrder = acceptOrder;
window.shipOrder = shipOrder;
window.completeOrder = completeOrder;
window.cancelOrder = cancelOrder;
window.viewOrderDetails = viewOrderDetails;
window.handleOrderSubmit = handleOrderSubmit;
window.addOrderItem = addOrderItem;
window.removeOrderItem = removeOrderItem;
window.updateItemPrice = updateItemPrice;
window.calculateItemSubtotal = calculateItemSubtotal;
window.calculateOrderTotal = calculateOrderTotal;
window.loadOrders = loadOrders;

// Invoice functions
window.showInvoiceForm = showInvoiceForm;
window.hideInvoiceForm = hideInvoiceForm;
window.markInvoicePaid = markInvoicePaid;
window.cancelInvoice = cancelInvoice;
window.viewInvoiceDetails = viewInvoiceDetails;
window.handleInvoiceSubmit = handleInvoiceSubmit;
window.onOrderSelected = onOrderSelected;
window.loadInvoices = loadInvoices;

// Payment functions
window.showPaymentForm = showPaymentForm;
window.hidePaymentForm = hidePaymentForm;
window.refundPayment = refundPayment;
window.failPayment = failPayment;
window.viewPaymentDetails = viewPaymentDetails;
window.handlePaymentSubmit = handlePaymentSubmit;
window.onInvoiceSelected = onInvoiceSelected;
window.loadPayments = loadPayments;

// Utility functions
window.closeModal = closeModal;
window.showMessage = showMessage;
