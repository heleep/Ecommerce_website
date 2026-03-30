// Global variables
let currentUser = null;
let currentCategory = 'kurti';
let cart = [];
let currentOrder = null;

// API Helper Functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, '#ef4444');
        return null;
    }
}

// Toast Notification
function showToast(message, color = '#3b82f6') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        background: ${color};
        color: white;
        padding: 12px 24px;
        border-radius: 40px;
        z-index: 1100;
        animation: slideIn 0.3s ease;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(-100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(-100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Load products from API
async function loadProducts() {
    try {
        const products = await apiCall(`/api/products?category=${currentCategory}`);
        const grid = document.getElementById('productGrid');
        
        if (!grid) return;
        
        if (!products || products.length === 0) {
            grid.innerHTML = '<p style="text-align:center; padding:3rem;">No products found in this category</p>';
            return;
        }
        
        grid.innerHTML = products.map(product => `
            <div class="product-card">
                <img class="product-img" src="${product.image_url || 'https://via.placeholder.com/300'}" 
                     alt="${product.name}" 
                     onerror="this.src='https://via.placeholder.com/300?text=Image+Not+Found'">
                <div class="product-info">
                    <div class="product-title">${escapeHtml(product.name)}</div>
                    <div class="product-price">₹${product.price.toFixed(2)}</div>
                    <div class="product-stock">${product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}</div>
                    <button class="add-to-cart" onclick="addToCart(${product.id})" ${product.stock <= 0 ? 'disabled' : ''}>
                        <i class="fas fa-shopping-cart"></i> Add to Cart
                    </button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading products:', error);
        showToast('Failed to load products', '#ef4444');
    }
}

// Add to cart
async function addToCart(productId) {
    if (!currentUser) {
        showToast('Please login first', '#ef4444');
        openModal('loginModal');
        return;
    }
    
    const result = await apiCall('/api/cart', {
        method: 'POST',
        body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    
    if (result && result.success) {
        showToast('Added to cart successfully!', '#10b981');
        loadCart();
    } else {
        showToast('Failed to add to cart', '#ef4444');
    }
}

// Load cart items
async function loadCart() {
    if (!currentUser) {
        document.getElementById('cartCount').innerText = '0';
        return;
    }
    
    const cartItems = await apiCall('/api/cart');
    if (cartItems) {
        cart = cartItems;
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        document.getElementById('cartCount').innerText = totalItems;
        
        const cartDiv = document.getElementById('cartItems');
        if (!cartDiv) return;
        
        if (cart.length === 0) {
            cartDiv.innerHTML = '<p style="text-align:center; padding:2rem;">Your cart is empty</p>';
            document.getElementById('cartTotal').innerText = '0';
            return;
        }
        
        const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        cartDiv.innerHTML = cart.map(item => `
            <div class="cart-item">
                <img src="${item.image_url}" width="70" height="70" style="border-radius:12px; object-fit:cover" onerror="this.src='https://via.placeholder.com/70'">
                <div style="flex:1">
                    <strong>${escapeHtml(item.name)}</strong><br>
                    <span style="color:#3b82f6;">₹${item.price}</span> x ${item.quantity}
                    <div style="margin-top:8px;">
                        <button class="qty-btn" onclick="updateCartItem(${item.id}, ${item.quantity + 1})">+</button>
                        <button class="qty-btn" onclick="updateCartItem(${item.id}, ${item.quantity - 1})">-</button>
                        <button class="remove-btn" onclick="removeCartItem(${item.id})">Remove</button>
                    </div>
                </div>
                <div style="font-weight:600;">₹${(item.price * item.quantity).toFixed(2)}</div>
            </div>
        `).join('');
        
        document.getElementById('cartTotal').innerText = total.toFixed(2);
    }
}

// Update cart item quantity
async function updateCartItem(cartId, newQuantity) {
    if (newQuantity <= 0) {
        await removeCartItem(cartId);
        return;
    }
    
    const result = await apiCall(`/api/cart/${cartId}`, {
        method: 'PUT',
        body: JSON.stringify({ quantity: newQuantity })
    });
    
    if (result && result.success) {
        loadCart();
    }
}

// Remove cart item
async function removeCartItem(cartId) {
    const result = await apiCall(`/api/cart/${cartId}`, { method: 'DELETE' });
    if (result && result.success) {
        loadCart();
        showToast('Item removed from cart', '#64748b');
    }
}

// Checkout process
async function checkout() {
    if (cart.length === 0) {
        showToast('Your cart is empty', '#ef4444');
        return;
    }
    
    closeModal('cartModal');
    openModal('paymentModal');
}

// Process payment
async function processPayment(method) {
    const shippingAddress = prompt('Please enter your shipping address:');
    if (!shippingAddress) {
        showToast('Shipping address is required', '#ef4444');
        return;
    }
    
    const result = await apiCall('/api/orders', {
        method: 'POST',
        body: JSON.stringify({
            payment_method: method,
            shipping_address: shippingAddress
        })
    });
    
    if (result && result.success) {
        currentOrder = result;
        showInvoice(result.order, result.items);
        closeModal('paymentModal');
        loadCart();
        showToast(`Order placed successfully! Order ID: ${result.order.order_number}`, '#10b981');
    } else {
        showToast('Order failed: ' + (result?.message || 'Unknown error'), '#ef4444');
    }
}

// Show QR payment
function showQRPayment() {
    const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const qrDiv = document.getElementById('qrSection');
    if (qrDiv) {
        qrDiv.style.display = 'block';
        qrDiv.innerHTML = `
            <div class="qr-container">
                <i class="fas fa-qrcode" style="font-size: 70px; color: #3b82f6;"></i>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa=trendythreads@okhdfc&pn=TrendyThreads&am=${total}&cu=INR" 
                     alt="QR Code" width="180" style="margin: 1rem 0;">
                <p style="font-weight:600;">Amount: ₹${total.toFixed(2)}</p>
                <p style="font-size:0.9rem;">Scan QR code with any UPI app</p>
                <button class="btn-primary" onclick="processPayment('qr')" style="margin-top:1rem;">
                    Confirm Payment
                </button>
            </div>
        `;
    }
}

// Show invoice
function showInvoice(order, items) {
    const invoiceDiv = document.getElementById('invoiceContent');
    if (!invoiceDiv) return;
    
    const subtotal = order.total_amount;
    const tax = subtotal * 0.05;
    const grandTotal = subtotal + tax;
    
    invoiceDiv.innerHTML = `
        <div style="text-align:center; border-bottom:2px solid #3b82f6; padding-bottom:1rem; margin-bottom:1rem;">
            <h2 style="color:#3b82f6;">TrendyThreads</h2>
            <p>123 Fashion Street, New Delhi | support@trendythreads.com</p>
        </div>
        
        <div style="display:flex; justify-content:space-between; margin-bottom:1.5rem;">
            <div>
                <h4>Invoice Details</h4>
                <p><strong>Invoice #:</strong> ${order.order_number}</p>
                <p><strong>Date:</strong> ${new Date(order.created_at).toLocaleString()}</p>
            </div>
            <div>
                <h4>Payment Details</h4>
                <p><strong>Method:</strong> ${order.payment_method}</p>
                <p><strong>Status:</strong> ${order.payment_status}</p>
            </div>
        </div>
        
        <div style="margin-bottom:1.5rem;">
            <h4>Customer Information</h4>
            <p><strong>Name:</strong> ${escapeHtml(order.full_name || 'Guest')}</p>
            <p><strong>Email:</strong> ${escapeHtml(order.email || 'Not provided')}</p>
            <p><strong>Address:</strong> ${escapeHtml(order.shipping_address || 'Not provided')}</p>
        </div>
        
        <table style="width:100%; border-collapse:collapse; margin-bottom:1rem;">
            <thead>
                <tr style="background:#f1f5f9;">
                    <th style="padding:0.75rem; text-align:left;">Product</th>
                    <th style="padding:0.75rem; text-align:center;">Quantity</th>
                    <th style="padding:0.75rem; text-align:right;">Price</th>
                    <th style="padding:0.75rem; text-align:right;">Total</th>
                </tr>
            </thead>
            <tbody>
                ${items.map(item => `
                    <tr style="border-bottom:1px solid #e2e8f0;">
                        <td style="padding:0.75rem;">${escapeHtml(item.product_name)}</td>
                        <td style="padding:0.75rem; text-align:center;">${item.quantity}</td>
                        <td style="padding:0.75rem; text-align:right;">₹${item.price.toFixed(2)}</td>
                        <td style="padding:0.75rem; text-align:right;">₹${(item.price * item.quantity).toFixed(2)}</td>
                    </tr>
                `).join('')}
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="3" style="padding:0.75rem; text-align:right;"><strong>Subtotal:</strong></td>
                    <td style="padding:0.75rem; text-align:right;">₹${subtotal.toFixed(2)}</td>
                </tr>
                <tr>
                    <td colspan="3" style="padding:0.75rem; text-align:right;"><strong>Tax (5%):</strong></td>
                    <td style="padding:0.75rem; text-align:right;">₹${tax.toFixed(2)}</td>
                </tr>
                <tr style="background:#f1f5f9;">
                    <td colspan="3" style="padding:0.75rem; text-align:right;"><strong>Grand Total:</strong></td>
                    <td style="padding:0.75rem; text-align:right;"><strong style="color:#3b82f6;">₹${grandTotal.toFixed(2)}</strong></td>
                </tr>
            </tfoot>
        </table>
        
        <div style="text-align:center; margin-top:1rem; padding-top:1rem; border-top:1px solid #e2e8f0;">
            <p>Thank you for shopping with TrendyThreads!</p>
            <p style="font-size:0.85rem; color:#64748b;">This is a computer generated invoice</p>
        </div>
    `;
    
    openModal('invoiceModal');
    
    // Download button handler
    const downloadBtn = document.getElementById('downloadInvoiceBtn');
    if (downloadBtn) {
        downloadBtn.onclick = () => {
            window.open(`/api/orders/${order.order_number}/invoice`, '_blank');
        };
    }
}

// Authentication functions
async function login() {
    const email = document.getElementById('loginEmail')?.value;
    const password = document.getElementById('loginPassword')?.value;
    
    if (!email || !password) {
        showToast('Please enter email and password', '#ef4444');
        return;
    }
    
    const result = await apiCall('/api/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    
    if (result && result.success) {
        currentUser = result.user;
        showToast(`Welcome back, ${currentUser.username}!`, '#10b981');
        closeModal('loginModal');
        
        // Update UI
        const authButtons = document.getElementById('authButtons');
        if (authButtons) {
            authButtons.innerHTML = `
                <span style="margin-right:1rem;">👋 Hi, ${escapeHtml(currentUser.username)}</span>
                <button class="login-btn" onclick="logout()">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </button>
            `;
        }
        
        loadCart();
        loadProducts();
    } else {
        showToast('Invalid credentials', '#ef4444');
    }
}

async function register() {
    const userData = {
        username: document.getElementById('regUsername')?.value,
        email: document.getElementById('regEmail')?.value,
        full_name: document.getElementById('regFullName')?.value,
        phone: document.getElementById('regPhone')?.value,
        password: document.getElementById('regPassword')?.value
    };
    
    if (!userData.username || !userData.email || !userData.password) {
        showToast('Please fill all required fields', '#ef4444');
        return;
    }
    
    const result = await apiCall('/api/register', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
    
    if (result && result.success) {
        showToast('Registration successful! Please login.', '#10b981');
        closeModal('registerModal');
        openModal('loginModal');
    } else {
        showToast('Registration failed: ' + (result?.message || 'Unknown error'), '#ef4444');
    }
}

async function logout() {
    await apiCall('/api/logout', { method: 'POST' });
    currentUser = null;
    cart = [];
    document.getElementById('cartCount').innerText = '0';
    
    const authButtons = document.getElementById('authButtons');
    if (authButtons) {
        authButtons.innerHTML = '<button class="login-btn" onclick="openModal(\'loginModal\')"><i class="fas fa-user"></i> Login</button>';
    }
    
    showToast('Logged out successfully', '#64748b');
    loadProducts();
}

// Modal functions
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize event listeners
function initEventListeners() {
    // Category buttons
    document.querySelectorAll('.cat-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = btn.dataset.cat;
            loadProducts();
        });
    });
    
    // Cart button
    const cartBtn = document.getElementById('cartBtn');
    if (cartBtn) {
        cartBtn.addEventListener('click', () => {
            if (!currentUser) {
                showToast('Please login first', '#ef4444');
                openModal('loginModal');
                return;
            }
            loadCart();
            openModal('cartModal');
        });
    }
    
    // Login button
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', () => openModal('loginModal'));
    }
    
    // Modal close on background click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadProducts();
    
    // Check if user is already logged in via session
    fetch('/api/check-session')
        .then(res => res.json())
        .then(data => {
            if (data.logged_in) {
                currentUser = data.user;
                const authButtons = document.getElementById('authButtons');
                if (authButtons) {
                    authButtons.innerHTML = `
                        <span style="margin-right:1rem;">👋 Hi, ${escapeHtml(currentUser.username)}</span>
                        <button class="login-btn" onclick="logout()">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </button>
                    `;
                }
                loadCart();
            }
        })
        .catch(err => console.error('Session check failed:', err));
});