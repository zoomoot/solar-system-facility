#!/bin/bash

# Solar System Database Setup Script
# Sets up MariaDB database and creates schema

echo "=========================================="
echo "Solar System Database Setup"
echo "=========================================="

# Configuration
DB_NAME="solar_system"
DB_USER="solar_user"
DB_PASS="solar_pass_2025"

echo ""
echo "This script will:"
echo "1. Create MariaDB database: $DB_NAME"
echo "2. Create user: $DB_USER"
echo "3. Load schema from database_schema.sql"
echo ""
echo "Prerequisites:"
echo "- MariaDB must be installed and running"
echo "- You need root/admin access to MariaDB"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 1
fi

echo ""
echo "Enter MariaDB root password:"
read -s MYSQL_ROOT_PASS

echo ""
echo "Creating database and user..."

mysql -u root -p"$MYSQL_ROOT_PASS" <<EOF
-- Create database
CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';

-- Grant privileges
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;

-- Show databases
SHOW DATABASES;
EOF

if [ $? -eq 0 ]; then
    echo "✅ Database and user created successfully"
else
    echo "❌ Error creating database and user"
    exit 1
fi

echo ""
echo "Loading schema..."

mysql -u root -p"$MYSQL_ROOT_PASS" $DB_NAME < database_schema.sql

if [ $? -eq 0 ]; then
    echo "✅ Schema loaded successfully"
else
    echo "❌ Error loading schema"
    exit 1
fi

echo ""
echo "Verifying setup..."

mysql -u $DB_USER -p"$DB_PASS" $DB_NAME <<EOF
SHOW TABLES;
SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = '$DB_NAME';
EOF

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Database Configuration:"
echo "  Host: localhost"
echo "  Port: 3306"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASS"
echo ""
echo "Set these environment variables before running loader:"
echo "  export DB_HOST=localhost"
echo "  export DB_PORT=3306"
echo "  export DB_NAME=$DB_NAME"
echo "  export DB_USER=$DB_USER"
echo "  export DB_PASSWORD=$DB_PASS"
echo ""
echo "Or create a .env file with these values"
echo "=========================================="




