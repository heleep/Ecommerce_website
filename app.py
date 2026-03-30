from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import mysql.connector
import json
from datetime import datetime
import secrets
import io
import os
from werkzeug.utils import secure_filename
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

app = Flask(__name__)
app.secret_key = 'trendythreads-secret-key-2024-very-secure'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
bcrypt = Bcrypt(app)
CORS(app)

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'helee8780@31',
    'database': 'ecommerce_db'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/check-session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session['user_id'],
                'username': session.get('username'),
                'email': session.get('email')
            }
        })
    return jsonify({'logged_in': False})

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered'})
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (data['username'],))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Username already taken'})
        
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, email, password, full_name, phone) VALUES (%s, %s, %s, %s, %s)",
            (data['username'], data['email'], hashed_password, data.get('full_name'), data.get('phone'))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (data['email'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.check_password_hash(user['password'], data['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            session['full_name'] = user['full_name']
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name']
                }
            })
        
        return jsonify({'success': False, 'message': 'Invalid credentials'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        category = request.args.get('category', 'all')
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        
        if category != 'all':
            cursor.execute("SELECT * FROM products WHERE category = %s ORDER BY created_at DESC", (category,))
        else:
            cursor.execute("SELECT * FROM products ORDER BY created_at DESC")
        
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert Decimal to float for JSON serialization
        for product in products:
            product['price'] = float(product['price'])
        return jsonify(products)
    except Exception as e:
        print(f"Error fetching products: {e}")
        return jsonify([])

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO products (name, price, image_url, category, description, stock) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (data['name'], data['price'], data['image_url'], data['category'], 
             data.get('description', ''), data.get('stock', 10))
        )
        conn.commit()
        product_id = cursor.lastrowid
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'id': product_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cart', methods=['GET'])
def get_cart():
    if 'user_id' not in session:
        return jsonify([])
    
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify([])
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.image_url, p.stock
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = %s
        """, (user_id,))
        
        cart_items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for item in cart_items:
            item['price'] = float(item['price'])
        return jsonify(cart_items)
    except Exception as e:
        print(f"Error fetching cart: {e}")
        return jsonify([])

@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'}), 401
    
    try:
        data = request.json
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Check stock
        cursor.execute("SELECT stock FROM products WHERE id = %s", (data['product_id'],))
        stock = cursor.fetchone()
        if not stock or stock[0] <= 0:
            return jsonify({'success': False, 'message': 'Product out of stock'})
        
        # Check if product already in cart
        cursor.execute("SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s", 
                      (user_id, data['product_id']))
        existing = cursor.fetchone()
        
        if existing:
            new_quantity = existing[1] + data.get('quantity', 1)
            if new_quantity > stock[0]:
                return jsonify({'success': False, 'message': 'Not enough stock'})
            cursor.execute("UPDATE cart SET quantity = %s WHERE id = %s", (new_quantity, existing[0]))
        else:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                          (user_id, data['product_id'], data.get('quantity', 1)))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cart/<int:cart_id>', methods=['PUT'])
def update_cart_item(cart_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Check stock
        cursor.execute("""
            SELECT p.stock FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.id = %s AND c.user_id = %s
        """, (cart_id, session['user_id']))
        stock = cursor.fetchone()
        
        if stock and data['quantity'] > stock[0]:
            return jsonify({'success': False, 'message': 'Not enough stock'})
        
        cursor.execute("UPDATE cart SET quantity = %s WHERE id = %s AND user_id = %s", 
                       (data['quantity'], cart_id, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cart/<int:cart_id>', methods=['DELETE'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id = %s AND user_id = %s", (cart_id, session['user_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login'}), 401
    
    try:
        data = request.json
        user_id = session['user_id']
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Get cart items with stock check
        cursor.execute("""
            SELECT c.product_id, c.quantity, p.name, p.price, p.stock
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = %s
        """, (user_id,))
        
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        # Verify stock
        for item in cart_items:
            if item['quantity'] > item['stock']:
                return jsonify({'success': False, 'message': f'{item["name"]} has insufficient stock'})
        
        total_amount = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Generate unique order number
        order_number = f"TRND{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.randbelow(1000)}"
        
        # Create order
        cursor.execute(
            """INSERT INTO orders (order_number, user_id, total_amount, payment_method, payment_status, shipping_address) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (order_number, user_id, total_amount, data['payment_method'], 
             'paid' if data['payment_method'] != 'cod' else 'pending', 
             data.get('shipping_address'))
        )
        order_id = cursor.lastrowid
        
        # Add order items and update stock
        for item in cart_items:
            cursor.execute(
                "INSERT INTO order_items (order_id, product_id, product_name, quantity, price) VALUES (%s, %s, %s, %s, %s)",
                (order_id, item['product_id'], item['name'], item['quantity'], item['price'])
            )
            # Update product stock
            cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", 
                          (item['quantity'], item['product_id']))
        
        # Clear cart
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        
        conn.commit()
        
        # Get order details for invoice
        cursor.execute("""
            SELECT o.*, u.full_name, u.email, u.phone, u.address 
            FROM orders o 
            JOIN users u ON o.user_id = u.id 
            WHERE o.id = %s
        """, (order_id,))
        
        order_details = cursor.fetchone()
        
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
        order_items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert Decimal to float
        order_details['total_amount'] = float(order_details['total_amount'])
        for item in order_items:
            item['price'] = float(item['price'])
        
        return jsonify({
            'success': True,
            'order': order_details,
            'items': order_items
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/orders/<order_number>/invoice', methods=['GET'])
def generate_invoice(order_number):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT o.*, u.full_name, u.email, u.phone, u.address 
            FROM orders o 
            JOIN users u ON o.user_id = u.id 
            WHERE o.order_number = %s AND o.user_id = %s
        """, (order_number, session['user_id']))
        
        order = cursor.fetchone()
        
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order['id'],))
        items = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Generate professional PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#1e3c72'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )
        
        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e3c72'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        story = []
        
        # Header with logo
        story.append(Paragraph("TRENDYTHREADS", title_style))
        story.append(Paragraph("Premium Clothing Store", header_style))
        story.append(Paragraph("123 Fashion Avenue, New Delhi - 110001", header_style))
        story.append(Paragraph("Email: support@trendythreads.com | Phone: +91 11 4567 8900", header_style))
        story.append(Spacer(1, 30))
        
        # Invoice title
        story.append(Paragraph(f"INVOICE", section_style))
        story.append(Spacer(1, 10))
        
        # Invoice and Order details
        invoice_data = [
            ['Invoice Number:', order['order_number']],
            ['Invoice Date:', order['created_at'].strftime('%d %B, %Y')],
            ['Order Status:', 'Confirmed' if order['payment_status'] == 'paid' else 'Pending'],
            ['Payment Method:', order['payment_method'].upper()]
        ]
        
        invoice_table = Table(invoice_data, colWidths=[120, 250])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1e3c72')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(invoice_table)
        story.append(Spacer(1, 20))
        
        # Bill To section
        story.append(Paragraph("BILL TO:", section_style))
        bill_data = [
            ['Customer Name:', order['full_name'] or 'Guest'],
            ['Email Address:', order['email']],
            ['Phone Number:', order['phone'] or 'Not provided'],
            ['Shipping Address:', order['shipping_address'] or 'Not provided']
        ]
        
        bill_table = Table(bill_data, colWidths=[120, 250])
        bill_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(bill_table)
        story.append(Spacer(1, 30))
        
        # Order Items Table
        story.append(Paragraph("ORDER SUMMARY:", section_style))
        
        # Table header
        table_data = [['Sl. No.', 'Product Description', 'Quantity', 'Unit Price', 'Total']]
        
        for idx, item in enumerate(items, 1):
            total = item['price'] * item['quantity']
            table_data.append([
                str(idx),
                item['product_name'],
                str(item['quantity']),
                f"₹{item['price']:,.2f}",
                f"₹{total:,.2f}"
            ])
        
        # Add totals
        subtotal = order['total_amount']
        tax = subtotal * 0.05  # 5% GST
        shipping = 0
        grand_total = subtotal + tax + shipping
        
        table_data.append(['', '', '', 'Subtotal:', f"₹{subtotal:,.2f}"])
        table_data.append(['', '', '', 'GST (5%):', f"₹{tax:,.2f}"])
        table_data.append(['', '', '', 'Shipping:', 'FREE'])
        table_data.append(['', '', '', 'GRAND TOTAL:', f"₹{grand_total:,.2f}"])
        
        items_table = Table(table_data, colWidths=[50, 230, 60, 80, 80])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -5), colors.white),
            ('BACKGROUND', (0, -4), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -5), 1, colors.HexColor('#e0e0e0')),
            ('FONTNAME', (0, -4), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1e3c72')),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
        
        # Thank you note
        thank_style = ParagraphStyle(
            'ThankYou',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        story.append(Paragraph("Thank you for shopping with TrendyThreads!", thank_style))
        story.append(Paragraph("We hope to see you again soon.", thank_style))
        story.append(Spacer(1, 20))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        )
        
        story.append(Paragraph("This is a computer generated invoice and does not require physical signature.", footer_style))
        story.append(Paragraph("For any queries, please contact support@trendythreads.com", footer_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(buffer, as_attachment=True, 
                        download_name=f'Invoice_{order_number}.pdf', 
                        mimetype='application/pdf')
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/orders/user', methods=['GET'])
def get_user_orders():
    if 'user_id' not in session:
        return jsonify([])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM orders 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (session['user_id'],))
        
        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for order in orders:
            order['total_amount'] = float(order['total_amount'])
        
        return jsonify(orders)
    except Exception as e:
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)