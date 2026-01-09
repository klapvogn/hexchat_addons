#!/bin/bash

# ZNC Log Search Installation Script
# Run this script from the znc_log_search directory

set -e

echo "================================"
echo "ZNC Log Search Setup"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Note: Some steps may require sudo access"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Generate secret key
echo ""
echo "================================"
echo "CONFIGURATION REQUIRED"
echo "================================"
echo ""
echo "Generated Secret Key (add to app.py line 13):"
python3 -c "import secrets; print(secrets.token_hex(32))"
echo ""

# Ask for password
echo "Enter a password for the admin user:"
read -s password
echo ""
echo "Your hashed password (add to app.py line 29):"
python3 -c "import hashlib; print(hashlib.sha256('$password'.encode()).hexdigest())"
echo ""

echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Edit app.py and update:"
echo "   - Line 13: app.secret_key (use the generated key above)"
echo "   - Line 29: Password hash (use the hash above)"
echo "   - Line 16: Verify ZNC_BASE_PATH is correct"
echo ""
echo "2. Test the application:"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "3. To install as a service:"
echo "   sudo cp znc-search.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable znc-search"
echo "   sudo systemctl start znc-search"
echo ""