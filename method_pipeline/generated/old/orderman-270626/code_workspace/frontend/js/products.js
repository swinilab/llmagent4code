/**
 * Products Module - Handles product-related UI operations
 * Provides overview, list, and form components for products
 */

let productsCache = [];

/**
 * Load and display all products
 */
async function loadProducts() {
    const container = document.getElementById('products-list');
    container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const response = await ProductAPI.getAll(0, 100);
        productsCache = response.products || [];
        
        if (productsCache.length === 0) {
            container.innerHTML = '<p class="text-center">No products found. Add your first product!</p>';
            return;
        }

        container.innerHTML = productsCache.map(product => `
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(product.name)}</h3>
                    <span class="badge badge-issued">SKU: ${escapeHtml(product.sku)}</span>
                </div>
                <div class="card-body">
                    <p><strong>Description:</strong> ${escapeHtml(product.description)}</p>
                    <p><strong>Price:</strong> $${product.price.toFixed(2)}</p>
                    <p><strong>Stock:</strong> 
                        <span style="color: ${product.stock_quantity > 10 ? '#28a745' : product.stock_quantity > 0 ? '#ffc107' : '#dc3545'}">
                            ${product.stock_quantity} units
                        </span>
                    </p>
                    <p><small>Created: ${formatDate(product.created_at)}</small></p>
                </div>
                <div class="card-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editProduct(${product.id})">Edit</button>
                    <button class="btn btn-sm btn-warning" onclick="adjustStock(${product.id})">Adjust Stock</button>
                    <button class="btn btn-sm btn-danger" onclick="confirmDeleteProduct(${product.id}, '${escapeHtml(product.name)}')">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = `<div class="error-message">Error loading products: ${error.message}</div>`;
    }
}

/**
 * Show form for creating a new product
 */
function showProductForm() {
    const container = document.getElementById('product-form-container');
    container.innerHTML = `
        <h3>${arguments[0] === 'edit' ? 'Edit Product' : 'Add New Product'}</h3>
        <form id="product-form" onsubmit="handleProductSubmit(event)">
            <input type="hidden" id="product-id">
            <div class="form-group">
                <label for="product-name">Product Name *</label>
                <input type="text" id="product-name" name="name" required>
            </div>
            <div class="form-group">
                <label for="product-sku">SKU *</label>
                <input type="text" id="product-sku" name="sku" required>
            </div>
            <div class="form-group">
                <label for="product-description">Description *</label>
                <textarea id="product-description" name="description" required></textarea>
            </div>
            <div class="form-group">
                <label for="product-price">Price ($) *</label>
                <input type="number" id="product-price" name="price" required step="0.01" min="0.01">
            </div>
            <div class="form-group">
                <label for="product-stock">Stock Quantity *</label>
                <input type="number" id="product-stock" name="stock_quantity" required min="0" value="0">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">${arguments[0] === 'edit' ? 'Update' : 'Create'} Product</button>
                <button type="button" class="btn btn-secondary" onclick="hideProductForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
    
    if (arguments[0] === 'edit' && arguments[1]) {
        fillProductForm(arguments[1]);
    }
}

/**
 * Hide the product form
 */
function hideProductForm() {
    document.getElementById('product-form-container').style.display = 'none';
    document.getElementById('product-form')?.reset();
}

/**
 * Fill form with product data for editing
 */
function fillProductForm(product) {
    document.getElementById('product-id').value = product.id;
    document.getElementById('product-name').value = product.name;
    document.getElementById('product-sku').value = product.sku;
    document.getElementById('product-description').value = product.description;
    document.getElementById('product-price').value = product.price;
    document.getElementById('product-stock').value = product.stock_quantity;
}

/**
 * Handle product form submission
 */
async function handleProductSubmit(event) {
    event.preventDefault();
    
    const id = document.getElementById('product-id').value;
    const data = {
        name: document.getElementById('product-name').value,
        sku: document.getElementById('product-sku').value,
        description: document.getElementById('product-description').value,
        price: parseFloat(document.getElementById('product-price').value),
        stock_quantity: parseInt(document.getElementById('product-stock').value)
    };

    try {
        if (id) {
            await ProductAPI.update(parseInt(id), data);
            showMessage('Product updated successfully!', 'success');
        } else {
            await ProductAPI.create(data);
            showMessage('Product created successfully!', 'success');
        }
        hideProductForm();
        loadProducts();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Edit an existing product
 */
async function editProduct(id) {
    try {
        const product = await ProductAPI.getById(id);
        showProductForm('edit', product);
    } catch (error) {
        showMessage(`Error loading product: ${error.message}`, 'error');
    }
}

/**
 * Adjust stock for a product
 */
function adjustStock(id) {
    const container = document.getElementById('product-form-container');
    container.innerHTML = `
        <h3>Adjust Stock for Product</h3>
        <form id="stock-form" onsubmit="handleStockAdjust(event)">
            <input type="hidden" id="stock-product-id" value="${id}">
            <div class="form-group">
                <label for="stock-change">Quantity Change *</label>
                <input type="number" id="stock-change" name="quantity_change" required step="1">
                <small>Use positive numbers to add stock, negative to remove</small>
            </div>
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">Update Stock</button>
                <button type="button" class="btn btn-secondary" onclick="hideProductForm()">Cancel</button>
            </div>
        </form>
    `;
    container.style.display = 'block';
}

/**
 * Handle stock adjustment
 */
async function handleStockAdjust(event) {
    event.preventDefault();
    
    const id = parseInt(document.getElementById('stock-product-id').value);
    const change = parseInt(document.getElementById('stock-change').value);

    try {
        await ProductAPI.updateStock(id, change);
        showMessage(`Stock updated by ${change} units!`, 'success');
        hideProductForm();
        loadProducts();
    } catch (error) {
        showMessage(`Error: ${error.message}`, 'error');
    }
}

/**
 * Confirm and delete a product
 */
function confirmDeleteProduct(id, name) {
    showModal(
        'Delete Product',
        `Are you sure you want to delete product "${name}"? This action cannot be undone.`,
        async () => {
            try {
                await ProductAPI.delete(id);
                showMessage('Product deleted successfully!', 'success');
                loadProducts();
            } catch (error) {
                showMessage(`Error deleting product: ${error.message}`, 'error');
            }
        }
    );
}

/**
 * Get product by ID from cache
 */
function getProductById(id) {
    return productsCache.find(p => p.id === id);
}
