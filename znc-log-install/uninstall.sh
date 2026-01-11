#!/bin/bash

# ZNC Log Search - Uninstall Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "ZNC Log Search - Uninstall"
echo "========================================================================"
echo ""

# Detect username
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)

# Determine installation paths
APP_PATH="$USER_HOME/apps/znc_search"
SYSTEM_SERVICE_PATH="/etc/systemd/system/znc-search.service"

echo -e "${YELLOW}WARNING: This will remove:${NC}"
echo "  - Application files: $APP_PATH"
echo "  - Systemd service: $SYSTEM_SERVICE_PATH"
echo "  - Cron jobs for log imports"
echo ""
echo -e "${RED}Your encrypted database will be DELETED!${NC}"
echo ""
read -p "Are you sure you want to uninstall? (yes/no) " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo ""
echo "Starting uninstall..."
echo ""

# Stop and disable service
if [ -f "$SYSTEM_SERVICE_PATH" ]; then
    echo "Stopping and removing systemd service..."
    
    sudo systemctl stop znc-search 2>/dev/null || true
    sudo systemctl disable znc-search 2>/dev/null || true
    sudo rm -f "$SYSTEM_SERVICE_PATH"
    sudo systemctl daemon-reload
    
    echo -e "${GREEN}✓ Service removed${NC}"
else
    echo "Service not found, skipping..."
fi

# Remove cron jobs
echo "Removing cron jobs..."
crontab -l 2>/dev/null | grep -v "znc_search/import_logs.py" | crontab - 2>/dev/null || true
echo -e "${GREEN}✓ Cron jobs removed${NC}"

# Backup database option
if [ -f "$APP_PATH/znc_logs.db" ]; then
    echo ""
    read -p "Create a backup of the database before deletion? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BACKUP_PATH="$USER_HOME/znc_logs_backup_$(date +%Y%m%d_%H%M%S).db"
        cp "$APP_PATH/znc_logs.db" "$BACKUP_PATH"
        echo -e "${GREEN}✓ Database backed up to: $BACKUP_PATH${NC}"
    fi
fi

# Remove application directory
if [ -d "$APP_PATH" ]; then
    echo ""
    echo "Removing application files..."
    rm -rf "$APP_PATH"
    echo -e "${GREEN}✓ Application files removed${NC}"
else
    echo "Application directory not found, skipping..."
fi

echo ""
echo "========================================================================"
echo "Uninstall Complete!"
echo "========================================================================"
echo ""
echo "ZNC Log Search has been removed from your system."
echo ""