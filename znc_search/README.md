# ZNC Log Search - Installation & Setup Guide

A web-based search interface for ZNC IRC logs with authentication, multi-network support, and date filtering.

## Features

- 🔐 Secure login authentication
- 🌐 Multi-network support with auto-detection
- 🔍 Search specific channels or all channels
- 📅 Date range filtering
- 🔤 Case-sensitive/insensitive search
- 🎨 Modern, responsive web interface
- ⚡ Production-ready with Gunicorn
- 🤖 Automated installation script

## System Requirements

- Python 3.8 or higher
- ZNC with logging module enabled
- Ubuntu/Debian Linux (or similar)
- Root/sudo access for systemd service (optional)

## Quick Start (Automated Installation)

### 1. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install Python 3 and required packages
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Prepare Installation Files

Create the application directory and copy all files:

```bash
# Create directory structure
mkdir -p ~/apps/znc_search/templates
mkdir -p ~/apps/znc_search/service

# Copy files to appropriate locations
# - app.py → ~/apps/znc_search/
# - index.html → ~/apps/znc_search/templates/
# - requirements.txt → ~/apps/znc_search/
# - install.sh → ~/apps/znc_search/
# - znc-search.service → ~/apps/znc_search/service/
```

### 3. Configure ZNC Logging

Enable the log module for each network you want to search:

**Method 1: Via IRC**
```
/msg *status LoadMod log
```

**Method 2: Via ZNC Web Admin**
1. Login to ZNC web interface
2. Go to each network
3. Enable the "log" module
4. Save settings

Verify logs exist:
```bash
ls -la ~/.znc/users/$(whoami)/networks/*/moddata/log/
```

### 4. Run Automated Installation

```bash
cd ~/apps/znc_search
chmod +x install.sh
./install.sh
```

The installation script will:
- ✅ Auto-detect your username and home directory
- ✅ Create a Python virtual environment
- ✅ Install all required dependencies
- ✅ Configure paths in app.py
- ✅ Generate a secure secret key
- ✅ Create a password hash for your admin account
- ✅ Configure the systemd service file
- ✅ Optionally install and start the service

**Important:** During installation, you'll be prompted to:
1. Enter a password for the admin account (this is the password you'll use to login)
2. Choose whether to enable the service on boot
3. Choose whether to start the service immediately

### 5. Access the Application

Visit: `http://your-server-ip:5000`

Login with:
- **Username:** admin
- **Password:** (the password you entered during installation)

## Manual Installation (Alternative)

If you prefer manual installation or need to customize the setup:

### 1. Create Virtual Environment

```bash
mkdir -p ~/apps/znc_search
cd ~/apps/znc_search
python3 -m venv venv
```

### 2. Install Dependencies

```bash
source venv/bin/activate
pip install --upgrade pip
pip install Flask==3.0.0 Flask-CORS==4.0.0 gunicorn==21.2.0
```

### 3. Copy Application Files

```bash
mkdir -p templates
# Copy app.py, templates/index.html, requirements.txt to this directory
```

### 4. Configure app.py

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Update line 11 in `app.py` with the generated key.

Generate password hash:
```bash
python3 -c "import hashlib; print(hashlib.sha256('YourPasswordHere'.encode()).hexdigest())"
```

Update line 24 in `app.py` with the generated hash.

Update line 14 in `app.py` with your ZNC path:
```python
ZNC_BASE_PATH = '/home/YOUR_USERNAME/.znc/users/YOUR_USERNAME/networks'
```

### 5. Test Manually

```bash
source venv/bin/activate
python app.py
# Or with gunicorn:
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 6. Install as Service (Optional)

Edit `znc-search.service` and update paths:
- User line
- WorkingDirectory
- Environment PATH
- ExecStart

Then:
```bash
sudo cp znc-search.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable znc-search
sudo systemctl start znc-search
```

## Service Management

### Control the Service

```bash
# Start the service
sudo systemctl start znc-search

# Stop the service
sudo systemctl stop znc-search

# Restart the service
sudo systemctl restart znc-search

# Check service status
sudo systemctl status znc-search

# View live logs
journalctl -u znc-search -f

# View last 100 log lines
journalctl -u znc-search -n 100 --no-pager
```

### If Service Fails to Start

```bash
# Check detailed logs
journalctl -u znc-search -n 50 --no-pager

# Verify paths in service file
cat /etc/systemd/system/znc-search.service

# Test gunicorn manually
cd ~/apps/znc_search
source venv/bin/activate
gunicorn --version

# Check permissions
ls -la ~/apps/znc_search/
```

## Configuration

### Network Names (Optional)

By default, the application auto-detects all networks with logging enabled and uses the capitalized folder name as the display name.

To customize network display names, edit `app.py` lines 17-23:

```python
NETWORK_NAMES = {
    'libera': 'Libera.Chat',
    'oftc': 'OFTC',
    'efnet': 'EFnet',
    # Add more custom names as needed
}
```

### Change Admin Password

```bash
# Generate new hash
python3 -c "import hashlib; print(hashlib.sha256('NewPassword'.encode()).hexdigest())"

# Edit app.py and update line 24
nano ~/apps/znc_search/app.py

# Restart service
sudo systemctl restart znc-search
```

### Add Additional Users

Edit `app.py` and add users to the USERS dictionary:

```python
USERS = {
    'admin': 'admin_password_hash_here',
    'user2': 'user2_password_hash_here',
}
```

### Change Port

Edit `/etc/systemd/system/znc-search.service` and change the port in the `ExecStart` line:

```ini
ExecStart=/home/YOUR_USERNAME/apps/znc_search/venv/bin/gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart znc-search
```

## Usage

### Web Interface

1. **Login**
   - Username: `admin`
   - Password: (configured during installation)

2. **Search Logs**
   - Select Network (auto-detected from your ZNC configuration)
   - Select Channel (or leave as "All Channels")
   - Enter search query
   - Optional: Set date range
   - Optional: Enable case-sensitive search
   - Click "Search"

3. **View Results**
   - Shows network, channel, file, and line number
   - Displays full log line content
   - Maximum 1000 results per search (prevents overwhelming responses)

### Example Searches

| Query | Finds |
|-------|-------|
| `kicked` | All kick events |
| `waiting for` | Queue messages |
| `username` | All mentions of username |
| `joined #` | Channel join events |
| `http` | URLs in logs |
| `error` | Error messages |
| `nick!user@host` | Specific user activity |

## Supported Log Formats

The application handles both ZNC log filename formats:

- ✅ `2025-12-04.log` (date with dashes)
- ✅ `channel_20251204.log` (channel prefix, no dashes)
- ✅ `20251204.log` (date without dashes)

## Firewall Configuration

If using UFW firewall:

```bash
# Allow port 5000
sudo ufw allow 5000/tcp

# Check firewall status
sudo ufw status
```

For remote access, ensure your server's firewall allows incoming connections on port 5000.

## Security Recommendations

1. **Use Strong Password**: Generate a secure password during installation
2. **Restrict Access**: Use firewall rules to limit access to trusted IPs
3. **HTTPS**: Set up nginx reverse proxy with SSL/TLS for production
4. **Regular Updates**: Keep Python packages updated
5. **Monitor Logs**: Check service logs regularly for suspicious activity
6. **Change Default Port**: Consider using a non-standard port
7. **VPN/SSH Tunnel**: Access through VPN or SSH tunnel for maximum security

## Production Deployment with Nginx (Recommended)

### Install Nginx

```bash
sudo apt install nginx -y
```

### Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/znc-search`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration (after certbot setup)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/znc-search /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Add HTTPS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically update your nginx configuration for SSL.

## Troubleshooting

### Can't Login
- **Check Password**: Verify password hash is correct in `app.py` line 24
- **Service Status**: `sudo systemctl status znc-search`
- **View Logs**: `journalctl -u znc-search -f`
- **Test Manually**: Run `python app.py` to see error messages

### No Networks Showing
- **Check ZNC Path**: Verify path in `app.py` line 14 matches your setup
- **Verify Logging**: `/msg *status ListMods` - ensure "log" module is loaded
- **Check Directories**: `ls -la ~/.znc/users/$(whoami)/networks/*/moddata/log/`
- **Permissions**: Ensure the application user can read ZNC log directories

### No Search Results
- **Check Logs Exist**: Verify log files exist in channel directories
- **Date Format**: Ensure log files match supported formats
- **Try Case-Insensitive**: Disable case-sensitive search
- **Check Date Range**: Verify date range isn't excluding files
- **Test Simple Query**: Try searching for a common word

### Service Won't Start (Exit Code 203/EXEC)
- **Check Paths**: `cat /etc/systemd/system/znc-search.service`
- **Verify Gunicorn**: `ls -la ~/apps/znc_search/venv/bin/gunicorn`
- **Test Manually**: `sudo -u $(whoami) ~/apps/znc_search/venv/bin/gunicorn --version`
- **Fix Permissions**: `chmod +x ~/apps/znc_search/venv/bin/gunicorn`
- **Reinstall**: Run `./install.sh` again

### Permission Denied Errors
```bash
# Fix ownership
sudo chown -R $(whoami):$(whoami) ~/apps/znc_search

# Fix permissions
chmod 755 ~/apps/znc_search
chmod 644 ~/apps/znc_search/app.py
chmod 755 ~/apps/znc_search/venv/bin/*
```

### Port Already in Use
```bash
# Check what's using port 5000
sudo lsof -i :5000

# Or use a different port (see "Change Port" section)
```

### Python Virtual Environment Issues
```bash
# Recreate venv
cd ~/apps/znc_search
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## File Locations

After installation, files are located at:

- **Application**: `~/apps/znc_search/`
- **Virtual Environment**: `~/apps/znc_search/venv/`
- **ZNC Logs**: `~/.znc/users/USERNAME/networks/*/moddata/log/`
- **Service File**: `/etc/systemd/system/znc-search.service`
- **Nginx Config**: `/etc/nginx/sites-available/znc-search` (if using nginx)

## Package Versions

- Flask: 3.0.0
- Flask-CORS: 4.0.0
- Gunicorn: 21.2.0
- Python: 3.8+

## Updating the Application

### Update Application Code

```bash
# Stop service
sudo systemctl stop znc-search

# Update files (app.py, index.html, etc.)
cd ~/apps/znc_search
# ... make your changes ...

# Restart service
sudo systemctl start znc-search
```

### Update Python Dependencies

```bash
cd ~/apps/znc_search
source venv/bin/activate
pip install --upgrade Flask Flask-CORS gunicorn
sudo systemctl restart znc-search
```

### Reinstall Completely

```bash
cd ~/apps/znc_search
./install.sh
# Follow prompts to reconfigure
```

## Backup

### Backup Application

```bash
tar -czf znc-search-backup-$(date +%Y%m%d).tar.gz ~/apps/znc_search/
```

### Backup Configuration Only

```bash
cp ~/apps/znc_search/app.py ~/app.py.backup.$(date +%Y%m%d)
```

### Backup ZNC Logs (Optional)

```bash
tar -czf znc-logs-backup-$(date +%Y%m%d).tar.gz ~/.znc/users/$(whoami)/networks/
```

## Uninstall

### Complete Removal

```bash
# Stop and disable service
sudo systemctl stop znc-search
sudo systemctl disable znc-search

# Remove service file
sudo rm /etc/systemd/system/znc-search.service
sudo systemctl daemon-reload

# Remove application
rm -rf ~/apps/znc_search/

# Remove nginx config (if installed)
sudo rm /etc/nginx/sites-enabled/znc-search
sudo rm /etc/nginx/sites-available/znc-search
sudo systemctl restart nginx
```

### Keep Logs Only

If you want to remove the application but keep ZNC logs:

```bash
# Only remove the application directory
rm -rf ~/apps/znc_search/
```

Your ZNC logs remain at `~/.znc/users/USERNAME/networks/*/moddata/log/`

## Advanced Configuration

### Custom Search Limits

Edit `app.py` line 191 to change the result limit:

```python
if len(results) >= 1000:  # Change 1000 to desired limit
```

### Multiple Workers

Adjust Gunicorn workers in `/etc/systemd/system/znc-search.service`:

```ini
ExecStart=/path/to/gunicorn -w 8 -b 0.0.0.0:5000 app:app
```

Rule of thumb: `(2 × num_cores) + 1` workers

### Enable Debug Mode (Not for Production!)

Edit `app.py` last line:

```python
app.run(host='0.0.0.0', port=5000, debug=True)  # Only for testing!
```

## Performance Tips

1. **Regular Log Rotation**: Large log files slow down searches
2. **Use Date Filters**: Narrow searches with date ranges
3. **Specific Channels**: Search individual channels when possible
4. **Index Frequently**: Consider indexing for very large log collections
5. **SSD Storage**: Store logs on SSD for faster access

## Support & Resources

- **Check Logs**: First step for any issue - `journalctl -u znc-search -n 100`
- **Test Manually**: Run `python app.py` to see detailed errors
- **ZNC Documentation**: https://wiki.znc.in/
- **Flask Documentation**: https://flask.palletsprojects.com/

## Changelog

### Version 1.1 (January 2026)
- ✨ Added automated installation script
- ✨ Auto-detection of username and paths
- ✨ Automatic secret key and password generation
- ✨ Auto-configuration of service file
- ✨ Local venv in application directory
- 🐛 Improved error handling
- 📝 Updated documentation

### Version 1.0
- Initial release
- Basic search functionality
- Multi-network support
- Date filtering
- Authentication system

## License

This is a custom application for personal use.

---

**Version**: 1.1  
**Last Updated**: January 2026  
**Automated Installation**: Yes
