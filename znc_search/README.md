# ZNC Log Search - Installation & Setup Guide

A web-based search interface for ZNC IRC logs with authentication, multi-network support, and date filtering.

## Features

- 🔐 Secure login authentication
- 🌐 Multi-network
- 📁 Search specific channels or all channels
- 📅 Date range filtering
- 🔤 Case-sensitive/insensitive search
- 🎨 Modern, responsive web interface
- ⚡ Production-ready with Gunicorn

## System Requirements

- Python 3.8 or higher
- ZNC with logging module enabled
- Ubuntu/Debian Linux (or similar)
- Root/sudo access for systemd service

## Installation Steps

### 1. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Create Python Virtual Environment

```bash
# Create venv directory if it doesn't exist
mkdir -p /home/<USERNAME>/venvs

# Create virtual environment
python3 -m venv /home/<USERNAME>/venvs/HexChat-Search
```

### 3. Install Python Packages

```bash
# Activate virtual environment
source /home/<USERNAME>/venvs/HexChat-Search/bin/activate

# Install required packages
pip install --upgrade pip
pip install Flask==3.0.0
pip install Flask-CORS==4.0.0
pip install gunicorn==21.2.0
```

### 4. Create Application Directory

```bash
# Create application directory
mkdir -p /home/<USERNAME>/apps/znc_log_search
mkdir -p /home/<USERNAME>/apps/znc_log_search/templates

# Navigate to directory
cd /home/<USERNAME>/apps/znc_log_search
```

### 5. Copy Application Files

Place these files in `/home/<USERNAME>/apps/znc_log_search/`:
- `app.py` - Main Flask application
- `templates/index.html` - Web interface
- `znc-search.service` - Systemd service file

Directory structure:
```
/home/<USERNAME>/apps/znc_log_search/
├── app.py
├── templates/
│   └── index.html
└── znc-search.service
```

### 6. Configure ZNC Logging

Enable the log module for each network:

**Method 1: Via IRC**
```
/msg *status LoadMod log
```

**Method 2: Via ZNC Web Admin**
1. Login to ZNC web interface
2. Go to each network (TL, OB, CTW, Libera, omg)
3. Enable the "log" module
4. Save settings

Verify logs exist:
```bash
ls -la /home/<USERNAME>/.znc/users/<USERNAME>/networks/*/moddata/log/
```

### 7. Configure Application

Edit `app.py` and set your password:

```bash
# Generate password hash
python3 -c "import hashlib; print(hashlib.sha256('YourPasswordHere'.encode()).hexdigest())"

# Edit app.py
nano /home/<USERNAME>/apps/znc_log_search/app.py
```

Update line 25 with your password hash:
```python
USERS = {
    'admin': 'your_generated_hash_here'
}
```

### 8. Test the Application

```bash
# Activate venv
source /home/<USERNAME>/venvs/HexChat-Search/bin/activate

# Run with Gunicorn
cd /home/<USERNAME>/apps/znc_log_search
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Visit: `http://your-server-ip:5000`

Press `CTRL+C` to stop when done testing.

### 9. Install as Systemd Service

```bash
# Copy service file
sudo cp /home/<USERNAME>/apps/znc_log_search/znc-search.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable znc-search

# Start service
sudo systemctl start znc-search

# Check status
sudo systemctl status znc-search
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

# View logs
journalctl -u znc-search -f

# View last 100 log lines
journalctl -u znc-search -n 100 --no-pager
```

### If Service Fails to Start

```bash
# Check detailed logs
journalctl -u znc-search -n 50 --no-pager

# Verify gunicorn path
ls -la /home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn

# Test manually
sudo -u <USERNAME> /home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn --version

# Check permissions
ls -la /home/<USERNAME>/apps/znc_log_search/
```

## Configuration

### Network Names

Edit `app.py` lines 17-23 to customize network display names:

```python
NETWORK_NAMES = {
    'NETWORK1': 'SHORT NAME1',
    'NETWORK2': 'SHORT NAME2',
    'NETWORK3': 'SHORT NAME3',
    'NETWORK4': 'SHORT NAME4',
    'NETWORK5': 'SHORT NAME5',
}
```

### Change Password

```bash
# Generate new hash
python3 -c "import hashlib; print(hashlib.sha256('NewPassword'.encode()).hexdigest())"

# Edit app.py and update line 25
nano /home/<USERNAME>/apps/znc_log_search/app.py

# Restart service
sudo systemctl restart znc-search
```

### Change Port

Edit `znc-search.service` and change the port in the `ExecStart` line:

```ini
ExecStart=/home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn -w 4 -b 0.0.0.0:8080 app:app
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
   - Password: (the one you configured)

2. **Search Logs**
   - Select Network (TL, OB, CTW, Libera, omg)
   - Select Channel (or leave as "All Channels")
   - Enter search query
   - Optional: Set date range
   - Optional: Enable case-sensitive search
   - Click "Search"

3. **Results**
   - Shows network, channel, file, and line number
   - Displays full log line content
   - Maximum 1000 results per search

### Example Searches

| Query | Finds |
|-------|-------|
| `kicked` | All kick events |
| `waiting for` | Queue messages |
| `username` | All mentions of username |
| `joined #` | Channel join events |
| `http` | URLs in logs |

## Supported Log Formats

The application handles both ZNC log filename formats:

- ✅ `2025-12-04.log` (date with dashes)
- ✅ `channel_20251204.log` (channel prefix, no dashes)

## Firewall Configuration

If using UFW firewall:

```bash
# Allow port 5000
sudo ufw allow 5000/tcp

# Check firewall status
sudo ufw status
```

## Security Recommendations

1. **Use Strong Password**: Generate a secure password hash
2. **Restrict Access**: Use firewall rules to limit access
3. **HTTPS**: Set up nginx reverse proxy with SSL/TLS
4. **Regular Updates**: Keep Python packages updated
5. **Monitor Logs**: Check service logs regularly

## Production Deployment with Nginx (Optional)

### Install Nginx

```bash
sudo apt install nginx -y
```

### Configure Nginx

Create `/etc/nginx/sites-available/znc-search`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
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

## Troubleshooting

### Can't Login
- Verify password hash is correct in `app.py`
- Check if service is running: `sudo systemctl status znc-search`
- View logs: `journalctl -u znc-search -f`

### No Networks Showing
- Verify ZNC base path in `app.py` line 14
- Check log module is loaded in ZNC: `/msg *status ListMods`
- Verify log directories exist: `ls -la /home/<USERNAME>/.znc/users/<USERNAME>/networks/*/moddata/log/`

### No Search Results
- Check if log files exist in the channel directory
- Verify date format is supported (YYYY-MM-DD.log or channel_YYYYMMDD.log)
- Try case-insensitive search
- Check date range isn't excluding files

### Service Won't Start (203/EXEC Error)
- Verify gunicorn path: `ls -la /home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn`
- Check service file: `cat /etc/systemd/system/znc-search.service`
- Test manually: `sudo -u <USERNAME> /home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn --version`
- Check permissions: `chmod +x /home/<USERNAME>/venvs/HexChat-Search/bin/gunicorn`

### Permission Denied Errors
```bash
# Fix ownership
sudo chown -R <USERNAME>:<USERNAME> /home/<USERNAME>/apps/znc_log_search
sudo chown -R <USERNAME>:<USERNAME> /home/<USERNAME>/venvs/HexChat-Search

# Fix permissions
chmod 755 /home/<USERNAME>/apps/znc_log_search
chmod 644 /home/<USERNAME>/apps/znc_log_search/app.py
```

## File Locations

- **Application**: `/home/<USERNAME>/apps/znc_log_search/`
- **Virtual Environment**: `/home/<USERNAME>/venvs/HexChat-Search/`
- **ZNC Logs**: `/home/<USERNAME>/.znc/users/<USERNAME>/networks/*/moddata/log/`
- **Service File**: `/etc/systemd/system/znc-search.service`
- **Nginx Config**: `/etc/nginx/sites-available/znc-search` (if using nginx)

## Package Versions

- Flask: 3.0.0
- Flask-CORS: 4.0.0
- Gunicorn: 21.2.0
- Python: 3.8+

## Updating the Application

```bash
# Stop service
sudo systemctl stop znc-search

# Update app.py or other files
nano /home/<USERNAME>/apps/znc_log_search/app.py

# Restart service
sudo systemctl start znc-search
```

## Backup

```bash
# Backup application
tar -czf znc-search-backup-$(date +%Y%m%d).tar.gz /home/<USERNAME>/apps/znc_log_search/

# Backup ZNC logs (optional)
tar -czf znc-logs-backup-$(date +%Y%m%d).tar.gz /home/<USERNAME>/.znc/users/<USERNAME>/networks/
```

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop znc-search
sudo systemctl disable znc-search

# Remove service file
sudo rm /etc/systemd/system/znc-search.service
sudo systemctl daemon-reload

# Remove application
rm -rf /home/<USERNAME>/apps/znc_log_search/

# Remove virtual environment (optional)
rm -rf /home/<USERNAME>/venvs/HexChat-Search/
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs: `journalctl -u znc-search -n 100`
3. Verify all installation steps were completed

## License

This is a custom application for personal use.

---

**Version**: 1.0  
**Last Updated**: January 2026