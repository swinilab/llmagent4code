/**
 * API Module - Handles all HTTP requests to the backend
 * Provides a clean interface for interacting with the REST API
 */

const API_BASE_URL = window.location.origin + '/api';

/**
 * Generic API request handler
 * @param {string} endpoint - API endpoint
 * @param {string} method - HTTP method
 * @param {object} data - Request body data
 * @returns {Promise<any>} Response data
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============================================================================
// Customer API
// ============================================================================

const CustomerAPI = {
    async getAll(skip = 0, limit = 100) {
        return apiRequest(`/customers?skip=${skip}&limit=${limit}`);
    },

    async getById(id) {
        return apiRequest(`/customers/${id}`);
    },

    async getByEmail(email) {
        return apiRequest(`/customers/email/${encodeURIComponent(email)}`);
    },

    async create(data) {
        return apiRequest('/customers', 'POST', data);
    },

    async update(id, data) {
        return apiRequest(`/customers/${id}`, 'PUT', data);
    },

    async delete(id) {
        return apiRequest(`/customers/${id}`, 'DELETE');
    }
};

// ============================================================================
// Product API
// ============================================================================

const ProductAPI = {
    async getAll(skip = 0, limit = 100, search = null) {
        const params = new URLSearchParams({ skip, limit });
        if (search) params.append('search', search);
        return apiRequest(`/products?${params.toString()}`);
    },

    async getById(id) {
        return apiRequest(`/products/${id}`);
    },

    async getBySku(sku) {
        return apiRequest(`/products/sku/${encodeURIComponent(sku)}`);
    },

    async create(data) {
        return apiRequest('/products', 'POST', data);
    },

    async update(id, data) {
        return apiRequest(`/products/${id}`, 'PUT', data);
    },

    async updateStock(id, quantityChange) {
        return apiRequest(`/products/${id}/stock?quantity_change=${quantityChange}`, 'PATCH');
    },

    async delete(id) {
        return apiRequest(`/products/${id}`, 'DELETE');
    }
};

// ============================================================================
// Order API
// ============================================================================

const OrderAPI = {
    async getAll(skip = 0, limit = 100, status = null, customerId = null) {
        const params = new URLSearchParams({ skip, limit });
        if (status) params.append('status', status);
        if (customerId) params.append('customer_id', customerId);
        return apiRequest(`/orders?${params.toString()}`);
    },

    async getById(id) {
        return apiRequest(`/orders/${id}`);
    },

    async create(data) {
        return apiRequest('/orders', 'POST', data);
    },

    async update(id, data) {
        return apiRequest(`/orders/${id}`, 'PUT', data);
    },

    async accept(id) {
        return apiRequest(`/orders/${id}/accept`, 'POST');
    },

    async ship(id) {
        return apiRequest(`/orders/${id}/ship`, 'POST');
    },

    async complete(id) {
        return apiRequest(`/orders/${id}/complete`, 'POST');
    },

    async cancel(id) {
        return apiRequest(`/orders/${id}/cancel`, 'POST');
    },

    async delete(id) {
        return apiRequest(`/orders/${id}`, 'DELETE');
    }
};

// ============================================================================
// Invoice API
// ============================================================================

const InvoiceAPI = {
    async getAll(skip = 0, limit = 100, status = null, customerId = null, overdue = null) {
        const params = new URLSearchParams({ skip, limit });
        if (status) params.append('status', status);
        if (customerId) params.append('customer_id', customerId);
        if (overdue) params.append('overdue', overdue);
        return apiRequest(`/invoices?${params.toString()}`);
    },

    async getById(id) {
        return apiRequest(`/invoices/${id}`);
    },

    async getByOrderId(orderId) {
        return apiRequest(`/invoices/order/${orderId}`);
    },

    async getByNumber(invoiceNumber) {
        return apiRequest(`/invoices/number/${encodeURIComponent(invoiceNumber)}`);
    },

    async create(data) {
        return apiRequest('/invoices', 'POST', data);
    },

    async update(id, data) {
        return apiRequest(`/invoices/${id}`, 'PUT', data);
    },

    async markPaid(id) {
        return apiRequest(`/invoices/${id}/pay`, 'POST');
    },

    async cancel(id) {
        return apiRequest(`/invoices/${id}/cancel`, 'POST');
    },

    async delete(id) {
        return apiRequest(`/invoices/${id}`, 'DELETE');
    },

    async checkOverdue() {
        return apiRequest('/invoices/check-overdue', 'POST');
    }
};

// ============================================================================
// Payment API
// ============================================================================

const PaymentAPI = {
    async getAll(skip = 0, limit = 100, status = null, customerId = null, invoiceId = null) {
        const params = new URLSearchParams({ skip, limit });
        if (status) params.append('status', status);
        if (customerId) params.append('customer_id', customerId);
        if (invoiceId) params.append('invoice_id', invoiceId);
        return apiRequest(`/payments?${params.toString()}`);
    },

    async getById(id) {
        return apiRequest(`/payments/${id}`);
    },

    async create(data) {
        return apiRequest('/payments', 'POST', data);
    },

    async update(id, data) {
        return apiRequest(`/payments/${id}`, 'PUT', data);
    },

    async refund(id) {
        return apiRequest(`/payments/${id}/refund`, 'POST');
    },

    async fail(id, reason = null) {
        const params = new URLSearchParams();
        if (reason) params.append('reason', reason);
        return apiRequest(`/payments/${id}/fail?${params.toString()}`, 'POST');
    },

    async delete(id) {
        return apiRequest(`/payments/${id}`, 'DELETE');
    }
};

// ============================================================================
// Health Check API
// ============================================================================

const HealthAPI = {
    async check() {
        return apiRequest('/health');
    }
};
