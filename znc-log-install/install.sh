#!/bin/bash

# ZNC Log Search with Encrypted SQLite - Installation Script
# Automatically detects username and configures paths

set -e

# Capture script directory FIRST, before any cd commands
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
#BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "ZNC Log Search with Encrypted SQLite - Setup"
echo "========================================================================"
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
DB_PATH="$APP_PATH/znc_logs.db"

echo "Installation paths:"
echo "  Application: $APP_PATH"
echo "  Virtual env: $VENV_PATH"
echo "  ZNC logs:    $ZNC_BASE_PATH"
echo "  Database:    $DB_PATH"
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

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if SQLCipher is installed
echo "Checking for SQLCipher..."
if ! command -v sqlcipher &> /dev/null; then
    echo -e "${YELLOW}WARNING: SQLCipher is not installed${NC}"
    echo ""
    echo "SQLCipher is required for database encryption. Install it with:"
    echo -e "${YELLOW}  Ubuntu/Debian: sudo apt-get install sqlcipher libsqlcipher-dev${NC}"
    echo -e "${YELLOW}  macOS:         brew install sqlcipher${NC}"
    echo -e "${YELLOW}  CentOS/RHEL:   sudo yum install sqlcipher sqlcipher-devel${NC}"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ SQLCipher found${NC}"
fi

# Create directories
echo ""
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
pip install Flask==3.0.0 Flask-CORS==4.0.0 gunicorn==21.2.0 pysqlcipher3==1.2.0 -q

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Generate encryption key
echo "========================================================================"
echo "SECURITY CONFIGURATION"
echo "========================================================================"
echo ""
# Check if DB_KEY already exists in any config file
echo "Checking for existing encryption keys..."
CONFIG_FILES=("$APP_PATH/app.py" "$APP_PATH/import_logs.py" "$APP_PATH/db_utils.py")
EXISTING_KEYS=()
DIFFERENT_KEYS=false

for config_file in "${CONFIG_FILES[@]}"; do
    if [ -f "$config_file" ]; then
        if grep -q "DB_KEY = '[^']*'" "$config_file"; then
            key=$(grep "DB_KEY = '[^']*'" "$config_file" | sed "s/.*DB_KEY = '\([^']*\)'.*/\1/")
            if [ -n "$key" ] && [ "$key" != "your-encryption-key-here" ]; then
                filename=$(basename "$config_file")
                EXISTING_KEYS+=("$filename:$key")
                
                # Check if this key differs from others
                if [ ${#EXISTING_KEYS[@]} -gt 1 ]; then
                    first_key=$(echo "${EXISTING_KEYS[0]}" | cut -d: -f2)
                    if [ "$key" != "$first_key" ]; then
                        DIFFERENT_KEYS=true
                        echo -e "${RED}⚠ Warning: $filename has a different key than other files!${NC}"
                    fi
                fi
            fi
        fi
    fi
done

# Process the results
if [ ${#EXISTING_KEYS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Found existing DB_KEY in configuration files${NC}"
    echo ""
    
    # Show which files have keys
    for entry in "${EXISTING_KEYS[@]}"; do
        filename=$(echo "$entry" | cut -d: -f1)
        key=$(echo "$entry" | cut -d: -f2)
        echo "  $filename: ${key:0:16}..."
    done
    
    if [ "$DIFFERENT_KEYS" = true ]; then
        echo -e "${RED}⚠ WARNING: Configuration files have different encryption keys!${NC}"
        echo -e "${RED}  This will cause database access errors.${NC}"
        echo ""
        echo "Options:"
        echo "  1) Use the key from app.py"
        echo "  2) Use the key from import_logs.py" 
        echo "  3) Use the key from db_utils.py"
        echo "  4) Generate a new key (recommended for consistency)"
        echo ""
        read -p "Choose option (1-4): " -n 1 -r
        echo
        
        case $REPLY in
            1)
                ENCRYPTION_KEY=$(echo "${EXISTING_KEYS[0]}" | cut -d: -f2)
                ;;
            2)
                for entry in "${EXISTING_KEYS[@]}"; do
                    if [[ "$entry" == *"import_logs.py"* ]]; then
                        ENCRYPTION_KEY=$(echo "$entry" | cut -d: -f2)
                        break
                    fi
                done
                ;;
            3)
                for entry in "${EXISTING_KEYS[@]}"; do
                    if [[ "$entry" == *"db_utils.py"* ]]; then
                        ENCRYPTION_KEY=$(echo "$entry" | cut -d: -f2)
                        break
                    fi
                done
                ;;
            4)
                # Will generate new key below
                SKIP_KEY_GEN=false
                ;;
            *)
                echo -e "${RED}Invalid choice. Generating new key.${NC}"
                SKIP_KEY_GEN=false
                ;;
        esac
        
        if [[ $REPLY =~ ^[1-3]$ ]]; then
            echo -e "${GREEN}Using selected key from configuration files${NC}"
            SKIP_KEY_GEN=true
        fi
    else
        # All files have the same key
        ENCRYPTION_KEY=$(echo "${EXISTING_KEYS[0]}" | cut -d: -f2)
        echo ""
        echo -e "${YELLOW}Current key (first 16 chars): ${ENCRYPTION_KEY:0:16}...${NC}"
        read -p "Keep existing encryption key? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${GREEN}Using existing encryption key${NC}"
            SKIP_KEY_GEN=true
        else
            echo -e "${YELLOW}Will generate new key${NC}"
            SKIP_KEY_GEN=false
        fi
    fi
else
    echo -e "${GREEN}No existing encryption keys found${NC}"
    SKIP_KEY_GEN=false
fi

echo ""

# Generate encryption key (if not using existing)
echo -e "${YELLOW}Step 1: Database Encryption Key${NC}"
if [ "$SKIP_KEY_GEN" = true ]; then
    echo -e "${GREEN}✓ Using existing key${NC}"
else
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo -e "${GREEN}✓ New encryption key generated${NC}"
    
    # Warn about database re-import if replacing existing key
    if [ ${#EXISTING_KEYS[@]} -gt 0 ]; then
        echo ""
        echo -e "${RED}⚠ WARNING: You've changed the encryption key!${NC}"
        echo -e "${RED}  Any existing encrypted database will be unreadable.${NC}"
        echo -e "${RED}  You'll need to re-import your logs.${NC}"
        echo ""
        read -p "Continue with new key? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation aborted."
            exit 1
        fi
    fi
fi
echo ""

echo -e "${YELLOW}Step 1: Generating Database Encryption Key${NC}"
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}✓ Encryption key generated${NC}"
echo ""

# Generate Flask secret key
echo -e "${YELLOW}Step 2: Generating Flask Secret Key${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}✓ Flask secret key generated${NC}"
echo ""

# Ask for admin password
echo -e "${YELLOW}Step 3: Admin Password Setup${NC}"
while true; do
    read -sp "Enter a password for the admin user: " PASSWORD
    echo ""
    read -sp "Confirm password: " PASSWORD_CONFIRM
    echo ""
    
    if [ "$PASSWORD" == "$PASSWORD_CONFIRM" ]; then
        break
    else
        echo -e "${RED}Passwords don't match. Try again.${NC}"
        echo ""
    fi
done

PASSWORD_HASH=$(python3 -c "import hashlib; print(hashlib.sha256('$PASSWORD'.encode()).hexdigest())")
echo -e "${GREEN}✓ Password hash generated${NC}"
echo ""

echo "========================================================================"
echo "CONFIGURATION SUMMARY"
echo "========================================================================"
echo ""
echo "The following values have been generated:"
echo ""
echo -e "${YELLOW}Database Encryption Key:${NC}"
echo "$ENCRYPTION_KEY"
echo ""
echo -e "${YELLOW}Flask Secret Key:${NC}"
echo "$SECRET_KEY"
echo ""
echo -e "${YELLOW}Admin Password Hash:${NC}"
echo "$PASSWORD_HASH"
echo ""
echo -e "${GREEN}IMPORTANT: Save the encryption key securely!${NC}"
echo "You'll need it if you ever need to recover the database."
echo ""

read -p "Press Enter to continue with installation..."
echo ""

echo "File deployment:"
echo "  Script location: $SCRIPT_DIR"
echo "  Install target:  $APP_PATH"
echo ""

# Only copy files if script is run from a different directory than APP_PATH
if [ "$SCRIPT_DIR" != "$APP_PATH" ]; then
    echo "Copying application files..."

    for file in app.py import_logs.py db_utils.py requirements.txt; do
        # Check both lowercase and capitalized versions
        if [ -f "$SCRIPT_DIR/$file" ]; then
            cp "$SCRIPT_DIR/$file" "$APP_PATH/"
            echo -e "${GREEN}✓ Copied $file${NC}"
        elif [ -f "$SCRIPT_DIR/${file^}" ]; then
            # Try with first letter capitalized
            cp "$SCRIPT_DIR/${file^}" "$APP_PATH/$file"
            echo -e "${GREEN}✓ Copied ${file^} as $file${NC}"
        else
            # Try to find case-insensitively
            found_file=$(find "$SCRIPT_DIR" -maxdepth 1 -iname "$file" -type f | head -n 1)
            if [ -n "$found_file" ]; then
                cp "$found_file" "$APP_PATH/$file"
                echo -e "${GREEN}✓ Copied $(basename "$found_file") as $file${NC}"
            else
                echo -e "${YELLOW}⚠ $file not found in $SCRIPT_DIR${NC}"
            fi
        fi
    done

    # Copy templates if they exist
    if [ -d "$SCRIPT_DIR/templates" ]; then
        cp -r "$SCRIPT_DIR/templates/"* "$APP_PATH/templates/" 2>/dev/null || true
        echo -e "${GREEN}✓ Copied templates${NC}"
    fi
else
    echo "Files already in place (running from installation directory)"
    # Verify required files exist
    for file in app.py import_logs.py db_utils.py requirements.txt; do
        if [ -f "$APP_PATH/$file" ]; then
            echo -e "${GREEN}✓ Found $file${NC}"
        else
            echo -e "${RED}✗ Missing $file${NC}"
            echo -e "${RED}ERROR: Required file $file not found!${NC}"
            echo "Please ensure all required files are in $APP_PATH"
            exit 1
        fi
    done
fi

# Configure app.py
if [ -f "$APP_PATH/app.py" ]; then
    echo ""
    echo "Configuring app.py..."
    
    # Update DB_PATH
    sed -i "s|DB_PATH = '.*'|DB_PATH = '$DB_PATH'|g" "$APP_PATH/app.py"
    
    # Update DB_KEY
    sed -i "s|DB_KEY = '.*'|DB_KEY = '$ENCRYPTION_KEY'|g" "$APP_PATH/app.py"
    
    # Update secret key
    sed -i "s|app.secret_key = '.*'|app.secret_key = '$SECRET_KEY'|g" "$APP_PATH/app.py"
    
    # Update password hash
    sed -i "s|'admin': '.*'|'admin': '$PASSWORD_HASH'|g" "$APP_PATH/app.py"
    
    echo -e "${GREEN}✓ app.py configured${NC}"
fi

# Configure import_logs.py
if [ -f "$APP_PATH/import_logs.py" ]; then
    echo "Configuring import_logs.py..."
    
    # Update ZNC_BASE_PATH
    sed -i "s|ZNC_BASE_PATH = '.*'|ZNC_BASE_PATH = '$ZNC_BASE_PATH'|g" "$APP_PATH/import_logs.py"
    
    # Update DB_PATH
    sed -i "s|DB_PATH = '.*'|DB_PATH = '$DB_PATH'|g" "$APP_PATH/import_logs.py"
    
    # Update DB_KEY
    sed -i "s|DB_KEY = '.*'|DB_KEY = '$ENCRYPTION_KEY'|g" "$APP_PATH/import_logs.py"
    
    echo -e "${GREEN}✓ import_logs.py configured${NC}"
fi

# Configure db_utils.py
if [ -f "$APP_PATH/db_utils.py" ]; then
    echo "Configuring db_utils.py..."
    
    # Update DB_PATH
    sed -i "s|DB_PATH = '.*'|DB_PATH = '$DB_PATH'|g" "$APP_PATH/db_utils.py"
    
    # Update DB_KEY
    sed -i "s|DB_KEY = '.*'|DB_KEY = '$ENCRYPTION_KEY'|g" "$APP_PATH/db_utils.py"
    
    echo -e "${GREEN}✓ db_utils.py configured${NC}"
fi

# Make scripts executable
chmod +x "$APP_PATH/import_logs.py" 2>/dev/null || true
chmod +x "$APP_PATH/db_utils.py" 2>/dev/null || true

echo ""
echo "========================================================================"
echo "DATABASE INITIALIZATION"
echo "========================================================================"
echo ""

# Ask if user wants to import logs now
if [ -d "$ZNC_BASE_PATH" ]; then
    read -p "Import your ZNC logs now? This may take a while. (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Starting log import..."
        echo "This may take several minutes depending on log size..."
        echo ""
        
        cd "$APP_PATH"
        source venv/bin/activate
        python3 import_logs.py
        
        echo ""
        echo -e "${GREEN}✓ Logs imported successfully${NC}"
    else
        echo "Skipping log import. You can import later with:"
        echo "  cd $APP_PATH && source venv/bin/activate && python3 import_logs.py"
    fi
else
    echo -e "${YELLOW}ZNC logs directory not found. Skipping import.${NC}"
    echo "Configure ZNC logging, then run:"
    echo "  cd $APP_PATH && source venv/bin/activate && python3 import_logs.py"
fi

echo ""
echo "========================================================================"
echo "SYSTEMD SERVICE INSTALLATION"
echo "========================================================================"
echo ""

# Create systemd service file (kept locally for reference/backup)
mkdir -p "$APP_PATH/service"
SERVICE_FILE="$APP_PATH/service/znc-search.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=ZNC Log Search with Encrypted Database
After=network.target

[Service]
Type=notify
User=$CURRENT_USER
WorkingDirectory=$APP_PATH
Environment="PATH=$VENV_PATH/bin"
ExecStart=$VENV_PATH/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created${NC}"

SYSTEM_SERVICE_PATH="/etc/systemd/system/znc-search.service"

echo ""
read -p "Install systemd service? (requires sudo) (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
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
    echo "Service installation skipped."
    echo "You can install it later with:"
    echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable znc-search"
    echo "  sudo systemctl start znc-search"
fi

echo ""
echo "========================================================================"
echo "CRON JOB SETUP (Optional)"
echo "========================================================================"
echo ""
echo "For automatic daily log imports, you can add a cron job."
echo ""
read -p "Add cron job for daily imports at 2 AM? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    CRON_CMD="0 */2 * * * cd $APP_PATH && $VENV_PATH/bin/python3 import_logs.py --incremental >> $APP_PATH/import.log 2>&1"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    
    echo -e "${GREEN}✓ Cron job added${NC}"
    echo "Logs will be automatically imported daily at 2 AM"
    echo "Import logs are saved to: $APP_PATH/import.log"
else
    echo "Cron job skipped. You can add it manually with:"
    echo "  crontab -e"
    echo ""
    echo "Add this line:"
    echo "  0 2 * * * cd $APP_PATH && $VENV_PATH/bin/python3 import_logs.py --incremental"
fi

echo ""
echo "========================================================================"
echo "INSTALLATION COMPLETE!"
echo "========================================================================"
echo ""
echo -e "${GREEN}Configuration Summary:${NC}"
echo "  User:          $CURRENT_USER"
echo "  App Path:      $APP_PATH"
echo "  Venv Path:     $VENV_PATH"
echo "  ZNC Path:      $ZNC_BASE_PATH"
echo "  Database:      $DB_PATH"
echo ""
echo -e "${YELLOW}Login Credentials:${NC}"
echo "  Username:      admin"
echo "  Password:      (the one you entered)"
echo ""
echo -e "${YELLOW}Important Files:${NC}"
echo "  Encryption Key: $ENCRYPTION_KEY"
echo "  (Save this securely - needed for database recovery)"
echo ""
echo -e "${GREEN}Quick Commands:${NC}"
echo ""
echo "1. Test manually:"
echo "   cd $APP_PATH"
echo "   source venv/bin/activate"
echo "   python3 app.py"
echo ""
echo "2. Check service status:"
echo "   sudo systemctl status znc-search"
echo ""
echo "3. View service logs:"
echo "   journalctl -u znc-search -f"
echo ""
echo "4. Restart service:"
echo "   sudo systemctl restart znc-search"
echo ""
echo "5. Import logs manually:"
echo "   cd $APP_PATH && source venv/bin/activate && python3 import_logs.py"
echo ""
echo "6. View database stats:"
echo "   cd $APP_PATH && source venv/bin/activate && python3 db_utils.py stats"
echo ""
echo "7. Create database backup:"
echo "   cd $APP_PATH && source venv/bin/activate && python3 db_utils.py backup"
echo ""
echo -e "${GREEN}Access at: http://your-server:5000${NC}"
echo ""
echo "For more information, see the README.md file"
echo ""
