#!/bin/bash

# ZNC Log Search Installation Script
# Automatically detects username and configures paths

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "ZNC Log Search Setup"
echo "================================"
echo ""

# Detect username
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)

echo -e "${GREEN}Detected user:${NC} $CURRENT_USER"
echo -e "${GREEN}Home directory:${NC} $USER_HOME"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}ERROR: Don't run this script as root/sudo${NC}"
    echo "Run as your normal user: ./install.sh"
    exit 1
fi

# Determine installation paths
APP_PATH="$USER_HOME/apps/znc_search"
VENV_PATH="$APP_PATH/venv"  # Local venv in app directory
ZNC_BASE_PATH="$USER_HOME/.znc/users/$CURRENT_USER/networks"

echo "Installation paths:"
echo "  Application: $APP_PATH"
echo "  Virtual env: $VENV_PATH"
echo "  ZNC logs:    $ZNC_BASE_PATH"
echo ""

# Check if ZNC logs exist
if [ ! -d "$ZNC_BASE_PATH" ]; then
    echo -e "${YELLOW}WARNING: ZNC log path not found at $ZNC_BASE_PATH${NC}"
    echo "Make sure ZNC is installed and logging is enabled"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create directories
echo "Creating directories..."
mkdir -p "$APP_PATH/templates"

# Navigate to app directory
cd "$APP_PATH"

# Create virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists, skipping..."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip -q
pip install Flask==3.0.0 Flask-CORS==4.0.0 gunicorn==21.2.0 -q

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Configure app.py
if [ -f "$APP_PATH/app.py" ]; then
    echo "Configuring app.py with detected paths..."
    
    # Update ZNC_BASE_PATH in app.py (handles both placeholder and existing paths)
    sed -i "s|ZNC_BASE_PATH = '/home/.*/\.znc/users/.*/networks'|ZNC_BASE_PATH = '$ZNC_BASE_PATH'|g" "$APP_PATH/app.py"
    
    echo -e "${GREEN}✓ app.py configured with your paths${NC}"
else
    echo -e "${YELLOW}WARNING: app.py not found at $APP_PATH/app.py${NC}"
    echo "Make sure to copy app.py to $APP_PATH/"
fi

# Generate configurations
echo ""
echo "================================"
echo "CONFIGURATION REQUIRED"
echo "================================"
echo ""

# Generate secret key
echo -e "${GREEN}1. Secret Key (for app.py line 11):${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "$SECRET_KEY"
echo ""

# Ask for password
echo -e "${GREEN}2. Admin Password Setup:${NC}"
read -sp "Enter a password for the admin user: " PASSWORD
echo ""
PASSWORD_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$PASSWORD'.encode()).hexdigest())")
echo "Your password hash (for app.py line 24):"
echo "$PASSWORD_HASH"
echo ""

# Update app.py with generated values if it exists
if [ -f "$APP_PATH/app.py" ]; then
    echo "Automatically updating app.py with generated values..."
    
    # Update secret key
    sed -i "s|app.secret_key = '.*'|app.secret_key = '$SECRET_KEY'|g" "$APP_PATH/app.py"
    
    # Update password hash
    sed -i "s|'admin': '.*'|'admin': '$PASSWORD_HASH'|g" "$APP_PATH/app.py"
    
    echo -e "${GREEN}✓ app.py automatically configured!${NC}"
    echo ""
fi

# Configure systemd service
SERVICE_FILE="$APP_PATH/service/znc-search.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "Configuring systemd service file..."
    
    # Update paths in service file
    sed -i "s|User=.*|User=$CURRENT_USER|g" "$SERVICE_FILE"
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$APP_PATH|g" "$SERVICE_FILE"
    sed -i "s|Environment=\"PATH=.*\"|Environment=\"PATH=$VENV_PATH/bin\"|g" "$SERVICE_FILE"
    sed -i "s|ExecStart=.*|ExecStart=$VENV_PATH/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app|g" "$SERVICE_FILE"
    
    echo -e "${GREEN}✓ Service file configured${NC}"
fi

# Install systemd service
echo ""
echo "================================"
echo "SYSTEMD SERVICE INSTALLATION"
echo "================================"
echo ""

SYSTEM_SERVICE_PATH="/etc/systemd/system/znc-search.service"

if [ -f "$SERVICE_FILE" ]; then
    echo "Service file ready: $SERVICE_FILE"
    echo ""
    
    # Check if service already exists
    if [ -f "$SYSTEM_SERVICE_PATH" ]; then
        echo -e "${YELLOW}WARNING: Service file already exists at $SYSTEM_SERVICE_PATH${NC}"
        echo ""
        read -p "Overwrite existing service file? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping service installation..."
            SKIP_SERVICE=true
        fi
    fi
    
    if [ "$SKIP_SERVICE" != true ]; then
        echo "Installing systemd service (requires sudo)..."
        
        # Copy service file
        if sudo cp "$SERVICE_FILE" "$SYSTEM_SERVICE_PATH"; then
            echo -e "${GREEN}✓ Service file installed${NC}"
            
            # Reload systemd
            echo "Reloading systemd daemon..."
            sudo systemctl daemon-reload
            echo -e "${GREEN}✓ Systemd reloaded${NC}"
            
            echo ""
            read -p "Enable service to start on boot? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl enable znc-search
                echo -e "${GREEN}✓ Service enabled${NC}"
            fi
            
            echo ""
            read -p "Start service now? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo systemctl start znc-search
                echo -e "${GREEN}✓ Service started${NC}"
                echo ""
                echo "Service status:"
                sudo systemctl status znc-search --no-pager -l
            fi
        else
            echo -e "${RED}✗ Failed to install service file${NC}"
            echo "You can install it manually with:"
            echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
        fi
    fi
else
    echo -e "${YELLOW}WARNING: znc-search.service not found in $APP_PATH${NC}"
    echo "Service installation skipped"
fi

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Configuration Summary:"
echo "  User:        $CURRENT_USER"
echo "  App Path:    $APP_PATH"
echo "  Venv Path:   $VENV_PATH"
echo "  ZNC Path:    $ZNC_BASE_PATH"
echo ""
echo "Quick commands:"
echo ""
echo "1. Test manually:"
echo "   cd $APP_PATH"
echo "   source venv/bin/activate"
echo "   python app.py"
echo ""
echo "2. Check service status:"
echo "   sudo systemctl status znc-search"
echo ""
echo "3. View logs:"
echo "   journalctl -u znc-search -f"
echo ""
echo "4. Restart service:"
echo "   sudo systemctl restart znc-search"
echo ""
echo -e "${GREEN}Login credentials:${NC}"
echo "  Username: admin"
echo "  Password: (the one you just entered)"
echo ""
echo "Access at: http://your-server:5000"
echo ""
