CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    image_url TEXT,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    stock INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id INT,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending',
    order_status VARCHAR(50) DEFAULT 'confirmed',
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Order items table
CREATE TABLE IF NOT EXISTS order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    product_name VARCHAR(255),
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Cart table
CREATE TABLE IF NOT EXISTS cart (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Insert sample products
INSERT INTO products (name, price, image_url, category, description) VALUES
('Floral Cotton Kurti', 899, 'https://picsum.photos/id/20/300/300', 'kurti', 'Beautiful floral printed cotton kurti'),
('Embroidered Straight Kurti', 1299, 'https://picsum.photos/id/26/300/300', 'kurti', 'Elegant embroidered straight kurti'),
('Anarkali Kurta Set', 1999, 'https://picsum.photos/id/28/300/300', 'kurti', 'Traditional Anarkali kurta set'),
('Oversized White Tee', 599, 'https://picsum.photos/id/1/300/300', 'tshirt', 'Comfortable oversized cotton t-shirt'),
('Striped Casual Top', 799, 'https://picsum.photos/id/13/300/300', 'tshirt', 'Stylish striped casual top'),
('Graphic Printed T-Shirt', 449, 'https://picsum.photos/id/42/300/300', 'tshirt', 'Cool graphic printed t-shirt'),
('Cotton Night Suit', 699, 'https://picsum.photos/id/29/300/300', 'nightwear', 'Soft cotton night suit'),
('Satin Pajama Set', 1099, 'https://picsum.photos/id/34/300/300', 'nightwear', 'Luxury satin pajama set'),
('Lounge Shorts & Tee', 899, 'https://picsum.photos/id/52/300/300', 'nightwear', 'Comfortable lounge wear set');