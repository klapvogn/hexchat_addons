# ZNC Log Search

A secure, encrypted web-based search interface for ZNC IRC logs with multi-user support, two-factor authentication, and automatic import capabilities.

## ✨ What's New

### Version 2.0 Features

- **🔐 Multi-User Support**: Database-backed user accounts with individual credentials
- **🛡️ Two-Factor Authentication (2FA)**: Optional TOTP-based 2FA for enhanced security
- **👥 User Management**: Command-line tools for managing users, passwords, and 2FA
- **🔄 Migration System**: Easy upgrade path from single-user to multi-user system
- **⚙️ Web-Based Settings**: Change password and manage 2FA directly in the interface
- **📊 User Tracking**: Audit trails with user creation and update timestamps

## Features

### 🔒 Security
- **Encrypted Database**: All logs stored in an encrypted SQLite database using SQLCipher
- **Multi-User Authentication**: Database-backed user accounts with SHA-256 hashed passwords
- **Two-Factor Authentication**: Optional TOTP-based 2FA with QR code setup
- **Session Management**: Secure session handling with Flask
- **User Administration**: CLI tools for managing users and security settings

### 🔍 Search Capabilities
- **Full-text Search**: Search across all imported IRC logs
- **Network Filtering**: Search within specific IRC networks
- **Channel Filtering**: Narrow searches to specific channels
- **Date Range Filtering**: Search logs within custom date ranges
- **Case-sensitive Search**: Optional case-sensitive matching
- **Context View**: View surrounding lines for search results
- **Result Limiting**: Returns up to 1000 results per query

### 📊 Database Features
- **Efficient Indexing**: Multiple indexes for fast searching
- **Statistics**: View database stats and usage information
- **Backup System**: Automated encrypted backups
- **Cleanup Tools**: Remove old backups automatically
- **Database Maintenance**: Vacuum, reindex, and integrity checks

### 🔄 Automation
- **Incremental Imports**: Only import new logs since last run
- **Cron Job Support**: Automatic scheduled imports
- **Systemd Service**: Run as a background service

## Installation

### Prerequisites

- Python 3.6 or higher
- ZNC IRC bouncer with logs enabled
- Systemd (for service mode)
- sudo access (for system service installation)

### Quick Install

1. **Clone or download the application files** to your desired location

2. **Run the installation script:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Follow the interactive prompts:**
   - Enter your ZNC log directory path (e.g., `/home/username/.znc/users/username/networks`)
   - Set a strong encryption key for the database
   - Choose whether to install as a system service
   - Select automatic import schedule (optional)

4. **Run the migration script** (for new installations or upgrades):
   ```bash
   python3 migrate_add_users.py
   ```
   
   This will create the users table and a default admin account.

### Manual Installation

If you prefer manual installation:

1. **Install Python dependencies:**
   ```bash
   pip3 install flask flask-cors gunicorn pysqlcipher3 pyotp qrcode pillow
   ```

2. **Configure the application:**
   
   Edit the following files and update the configuration variables:
   - `app.py`: Set `DB_KEY` and configure paths
   - `import_logs.py`: Set `ZNC_BASE_PATH` and `DB_KEY`
   - `db_utils.py`: Set `DB_KEY`
   - `user_admin.py`: Set `DB_PATH` and `DB_KEY`
   - `migrate_add_users.py`: Set `DB_PATH` and `DB_KEY`

3. **Initialize the database:**
   ```bash
   python3 import_logs.py
   ```

4. **Run the migration** (creates users table):
   ```bash
   python3 migrate_add_users.py
   ```

5. **Start the web application:**
   
   For testing/development:
   ```bash
   python3 app.py
   ```
   
   For production, use the systemd service (which runs Gunicorn):
   ```bash
   sudo systemctl start znc-search
   ```

## Configuration

### Database Encryption Key

The encryption key must be **identical** across all files:
- `app.py`
- `import_logs.py`
- `db_utils.py`
- `user_admin.py`
- `migrate_add_users.py`

**Example:**
```python
DB_KEY = 'your-strong-encryption-key-here-use-at-least-32-characters'
```

⚠️ **IMPORTANT**: Keep this key secure and backed up. Without it, you cannot access your database!

### Default User Account

After running `migrate_add_users.py`, a default admin account is created:
- **Username**: `admin`
- **Password**: `admin`

**🚨 SECURITY WARNING**: Change this password immediately after first login!

**To change the password:**
1. Log in to the web interface
2. Go to Settings → Change Password
3. Enter current password and new password

### Network Display Names (Optional)

Customize network display names in `app.py` and `import_logs.py`:
```python
NETWORK_NAMES = {
    'libera': 'Libera.Chat',
    'oftc': 'OFTC',
    'efnet': 'EFnet'
}
```

## User Management

### Web Interface User Settings

Users can manage their own accounts through the web interface:

**Change Password:**
1. Log in to the web interface
2. Click "Settings" in the navigation
3. Go to "Change Password" section
4. Enter current password and new password
5. Click "Update Password"

**Enable Two-Factor Authentication:**
1. Log in to the web interface
2. Click "Settings" in the navigation
3. Go to "Two-Factor Authentication" section
4. Click "Enable 2FA"
5. Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)
6. Enter the 6-digit code from your app to verify
7. Save your backup codes in a secure location

**Disable Two-Factor Authentication:**
1. Go to Settings → Two-Factor Authentication
2. Click "Disable 2FA"
3. Enter your password to confirm
4. 2FA will be disabled

### Command-Line User Administration

The `user_admin.py` script provides comprehensive user management:

#### List All Users
```bash
python3 user_admin.py list
```

Shows all users with their ID, username, 2FA status, and timestamps.

#### Add New User
```bash
python3 user_admin.py add <username>
```

Creates a new user account. You'll be prompted to:
- Enter a password (minimum 8 characters)
- Confirm the password

Example:
```bash
python3 user_admin.py add alice
# Enter password: ********
# Confirm password: ********
# ✓ User 'alice' created successfully
```

#### Reset User Password
```bash
python3 user_admin.py password <username>
```

Resets a user's password. Useful if a user forgets their password.

Example:
```bash
python3 user_admin.py password bob
# Enter new password: ********
# Confirm new password: ********
# ✓ Password for user 'bob' reset successfully
```

#### Disable 2FA for User
```bash
python3 user_admin.py disable-2fa <username>
```

Disables two-factor authentication for a user. Useful if a user loses access to their authenticator app.

Example:
```bash
python3 user_admin.py disable-2fa charlie
# ✓ 2FA disabled for user 'charlie'
```

#### Delete User
```bash
python3 user_admin.py delete <username>
```

Permanently deletes a user account. Requires confirmation.

Example:
```bash
python3 user_admin.py delete olduser
# Are you sure you want to delete user 'olduser'? (yes/no): yes
# ✓ User 'olduser' deleted successfully
```

#### View User Information
```bash
python3 user_admin.py info <username>
```

Displays detailed information about a user:
- User ID
- Username
- 2FA status
- Whether 2FA secret is set
- Account creation date
- Last update date

Example:
```bash
python3 user_admin.py info admin
# ============================================================
# USER INFORMATION
# ============================================================
# ID:              1
# Username:        admin
# 2FA Status:      Enabled
# 2FA Secret:      [SET]
# Created:         2025-01-15 10:23:45
# Last Updated:    2025-01-16 14:30:22
```

## Two-Factor Authentication (2FA)

### Setting Up 2FA

1. **Log in to the web interface**

2. **Navigate to Settings → Two-Factor Authentication**

3. **Click "Enable 2FA"**

4. **Scan the QR code** with your authenticator app:
   - Google Authenticator (iOS/Android)
   - Authy (iOS/Android/Desktop)
   - Microsoft Authenticator (iOS/Android)
   - 1Password
   - Any other TOTP-compatible app

5. **Enter the 6-digit code** from your authenticator app

6. **Save your backup codes** (if provided) in a secure location

### Using 2FA

Once 2FA is enabled, you'll need to:
1. Enter your username and password
2. Enter the 6-digit code from your authenticator app
3. Click "Login"

The code refreshes every 30 seconds, so make sure to enter it quickly.

### Lost Authenticator Device?

If you lose access to your authenticator app:

**For your own account:**
- Use your backup codes (if you saved them)
- Contact an administrator to disable 2FA

**For other users (administrators):**
```bash
python3 user_admin.py disable-2fa <username>
```

### 2FA Best Practices

- ✅ **DO**: Save backup codes in a secure password manager
- ✅ **DO**: Use a reputable authenticator app
- ✅ **DO**: Set up 2FA on a device you always have with you
- ❌ **DON'T**: Share your 2FA secret or QR code
- ❌ **DON'T**: Use SMS-based authentication (not supported)
- ❌ **DON'T**: Disable 2FA unless absolutely necessary

## Usage

### Initial Log Import

Import all existing logs:
```bash
python3 import_logs.py
```

### Incremental Import

Import only new logs since last import:
```bash
python3 import_logs.py --incremental
```

### Import Specific Network

Import logs from a single network:
```bash
python3 import_logs.py --network libera
```

### Web Interface

**For Testing/Development:**

1. Start the application:
   ```bash
   python3 app.py
   ```

**For Production:**

1. Use the systemd service (runs Gunicorn automatically):
   ```bash
   sudo systemctl start znc-search
   ```

**Accessing the Interface:**

2. Open your browser to: `http://localhost:5000`

3. Log in with your credentials:
   - Default: `admin` / `admin` (change immediately!)

4. Use the search interface:
   - Select network and channel (optional)
   - Enter search query
   - Set date range (optional)
   - Click "Search"

5. Access Settings:
   - Click "Settings" in navigation
   - Change your password
   - Enable/disable 2FA
   - View your account information

### Database Utilities

The `db_utils.py` script provides various maintenance commands:

#### View Statistics
```bash
python3 db_utils.py stats
```

Shows:
- Total log entries
- Number of networks and channels
- Date range of logs
- Database file size
- Entries per network
- Top channels by activity

#### Optimize Database
```bash
python3 db_utils.py vacuum
```

Reclaims unused space and optimizes the database file.

#### Rebuild Indexes
```bash
python3 db_utils.py reindex
```

Rebuilds all database indexes for optimal performance.

#### Verify Database Integrity
```bash
python3 db_utils.py verify
```

Checks database integrity and foreign key constraints.

#### Create Backup
```bash
python3 db_utils.py backup
```

Creates an encrypted backup in the `backup/` directory.

Custom backup location:
```bash
python3 db_utils.py backup -o /path/to/backup.db
```

#### Export to SQL
```bash
python3 db_utils.py export
```

**⚠️ WARNING**: Exports to unencrypted SQL file!

#### Cleanup Old Backups
```bash
python3 db_utils.py cleanup
```

Removes backups older than 30 days (default).

Custom retention:
```bash
python3 db_utils.py cleanup --keep-days 60
```

## Migration from Version 1.0

If you're upgrading from the old single-user system:

### Automatic Migration

1. **Run the migration script:**
   ```bash
   python3 migrate_add_users.py
   ```

2. **What it does:**
   - Creates the `users` table in your existing database
   - Creates a default admin user (username: `admin`, password: `admin`)
   - **Does NOT affect** your existing log data

3. **After migration:**
   - Log in with username `admin` and password `admin`
   - **Immediately change the password** via Settings → Change Password
   - Create additional user accounts as needed
   - Set up 2FA for enhanced security

### Migration Notes

- ✅ Your log data is **completely safe** - migration only adds the users table
- ✅ All existing searches, networks, and channels remain unchanged
- ✅ Database encryption key stays the same
- ✅ You can continue importing logs as before
- ⚠️ The old `USERS` dictionary in `app.py` is no longer used
- ⚠️ Change the default password immediately

## Systemd Service

### Service File Location

After installation: `/etc/systemd/system/znc-search.service`

### Service Management

**Start the service:**
```bash
sudo systemctl start znc-search
```

**Stop the service:**
```bash
sudo systemctl stop znc-search
```

**Restart the service:**
```bash
sudo systemctl restart znc-search
```

**Check status:**
```bash
sudo systemctl status znc-search
```

**View logs:**
```bash
sudo journalctl -u znc-search -f
```

**Enable at boot:**
```bash
sudo systemctl enable znc-search
```

**Disable at boot:**
```bash
sudo systemctl disable znc-search
```

### Sample Service File

```ini
[Unit]
Description=ZNC Log Search Web Interface
After=network.target

[Service]
Type=notify
User=username
WorkingDirectory=/home/username/apps/znc_search
Environment="PATH=/home/username/apps/znc_search/venv/bin"
ExecStart=/home/username/apps/znc_search/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Note**: The service uses Gunicorn with 4 worker processes. Adjust the `-w` parameter based on your server's resources (recommended: 2-4 workers per CPU core).

## Cron Jobs

### Automatic Log Import

The installation script can set up automatic imports. Common schedules:

#### Every Hour
```cron
0 * * * * cd /home/username/apps/znc_search && /usr/bin/python3 import_logs.py --incremental >> /home/username/apps/znc_search/import.log 2>&1
```

#### Every 6 Hours
```cron
0 */6 * * * cd /home/username/apps/znc_search && /usr/bin/python3 import_logs.py --incremental >> /home/username/apps/znc_search/import.log 2>&1
```

#### Daily at 2 AM
```cron
0 2 * * * cd /home/username/apps/znc_search && /usr/bin/python3 import_logs.py --incremental >> /home/username/apps/znc_search/import.log 2>&1
```

### Manual Cron Setup

Edit your crontab:
```bash
crontab -e
```

Add your desired schedule (examples above).

### View Import Logs

Check the import log file:
```bash
tail -f ~/apps/znc_search/import.log
```

## API Endpoints

The application provides a REST API (requires authentication):

### Authentication
- `POST /api/login` - Authenticate user (supports 2FA)
- `POST /api/logout` - End session

### User Management
- `POST /api/user/password` - Change password
- `GET /api/user/2fa/status` - Get 2FA status
- `POST /api/user/2fa/setup` - Generate 2FA QR code
- `POST /api/user/2fa/enable` - Enable 2FA
- `POST /api/user/2fa/disable` - Disable 2FA

### Data Retrieval
- `GET /api/networks` - List available networks
- `GET /api/channels/<network>` - List channels for a network
- `GET /api/stats` - Get database statistics
- `POST /api/search` - Search logs
- `POST /api/context` - Get context around a specific line

### Login Request Examples

**Standard login:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Login with 2FA:**
```json
{
  "username": "admin",
  "password": "your-password",
  "totp_code": "123456"
}
```

**Response when 2FA is required:**
```json
{
  "requires_2fa": true,
  "message": "Please enter your 2FA code"
}
```

### Search Request Example

```json
{
  "query": "search term",
  "network": "libera",
  "channel": "#channel",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "case_sensitive": false
}
```

### Context Request Example

```json
{
  "network": "libera",
  "channel": "#channel",
  "date": "2025-01-15",
  "line": 150,
  "lines_before": 5,
  "lines_after": 5
}
```

### Change Password Request

```json
{
  "current_password": "old-password",
  "new_password": "new-secure-password"
}
```

### 2FA Setup Response

```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KG...",
  "manual_entry": "JBSWY3DPEHPK3PXP"
}
```

## Database Schema

### Tables

**networks**
- `id` (TEXT, PRIMARY KEY) - Network identifier
- `display_name` (TEXT) - Human-readable network name

**channels**
- `id` (INTEGER, PRIMARY KEY)
- `network_id` (TEXT, FOREIGN KEY)
- `name` (TEXT) - Channel name

**log_entries**
- `id` (INTEGER, PRIMARY KEY)
- `network_id` (TEXT, FOREIGN KEY)
- `channel_name` (TEXT)
- `log_date` (DATE)
- `line_number` (INTEGER)
- `content` (TEXT) - Log line content

**users** *(NEW in v2.0)*
- `id` (INTEGER, PRIMARY KEY)
- `username` (TEXT, UNIQUE) - User's login name
- `password_hash` (TEXT) - SHA-256 hashed password
- `totp_secret` (TEXT, NULLABLE) - TOTP secret for 2FA
- `totp_enabled` (INTEGER) - Whether 2FA is enabled (0 or 1)
- `created_at` (TIMESTAMP) - Account creation time
- `updated_at` (TIMESTAMP) - Last update time

**import_metadata**
- `key` (TEXT, PRIMARY KEY)
- `value` (TEXT) - Metadata values

### Indexes

- `idx_log_network` - Network ID
- `idx_log_channel` - Channel name
- `idx_log_date` - Log date
- `idx_log_content` - Content (for searching)
- `idx_log_composite` - Composite index (network, channel, date)

## Troubleshooting

### Database Connection Errors

**Problem**: "Error: file is not a database"

**Solution**: Encryption key mismatch. Ensure `DB_KEY` is identical in all files:
- `app.py`
- `import_logs.py`
- `db_utils.py`
- `user_admin.py`
- `migrate_add_users.py`

### Migration Issues

**Problem**: "Users table already exists"

**Solution**: This is normal if you've already run the migration. The script will skip table creation and just ensure the admin user exists.

**Problem**: Can't log in after migration

**Solution**: 
1. Ensure you're using the correct credentials: `admin` / `admin`
2. If you changed the password in the old system, reset it:
   ```bash
   python3 user_admin.py password admin
   ```

### 2FA Issues

**Problem**: Lost access to authenticator app

**Solution**: An administrator can disable 2FA:
```bash
python3 user_admin.py disable-2fa <username>
```

**Problem**: 2FA codes not working

**Solution**: 
- Ensure your device's time is correct (TOTP requires accurate time)
- Try the previous or next code (30-second window)
- Check that you're using the correct account in your authenticator app

**Problem**: Can't enable 2FA

**Solution**:
1. Ensure pyotp and qrcode are installed: `pip3 install pyotp qrcode pillow`
2. Check browser console for errors
3. Try a different authenticator app

### Import Failures

**Problem**: "Error: ZNC base path not found"

**Solution**: Update `ZNC_BASE_PATH` in `import_logs.py` to point to your ZNC logs directory.

### Permission Denied

**Problem**: Cannot write to database or create backups

**Solution**: 
```bash
chmod 755 ~/apps/znc_search
chmod 644 ~/apps/znc_search/znc_logs.db
```

### Service Won't Start

**Problem**: Systemd service fails to start

**Solution**: Check logs:
```bash
sudo journalctl -u znc-search -n 50
```

Verify paths in service file match your installation.

Common issues:
- Gunicorn not installed: `source venv/bin/activate && pip install gunicorn`
- Wrong venv path in service file
- Missing app.py file
- Database permission issues

### Port Already in Use

**Problem**: "Address already in use: Port 5000"

**Solution**: 
- Check if another instance is running: `sudo systemctl status znc-search`
- Change port in systemd service file (edit the `-b 0.0.0.0:5000` parameter)
- Or change in `app.py` if running directly:
```python
app.run(host='0.0.0.0', port=5001, debug=False)
```

### Gunicorn Worker Timeout

**Problem**: Workers timing out or restarting frequently

**Solution**: Adjust worker count and timeout in service file:
```ini
ExecStart=/path/to/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 --timeout 120 app:app
```

Reduce workers (`-w 2`) if you have limited resources, or increase timeout (`--timeout 120`) for slow queries.

### User Management Issues

**Problem**: "User not found" when trying to manage users

**Solution**: 
1. Check if migration was run: `python3 migrate_add_users.py`
2. Verify database path in `user_admin.py` matches your setup
3. List all users to verify: `python3 user_admin.py list`

## Uninstallation

Run the uninstall script:
```bash
chmod +x uninstall.sh
./uninstall.sh
```

This will:
- Stop and remove the systemd service
- Remove cron jobs
- Delete application files
- Optionally backup the database before deletion

## Security Considerations

### Critical Security Practices

1. **Change Default Credentials**: 
   - The default `admin/admin` credentials are INSECURE
   - Change immediately after first login
   - Use a strong password (minimum 12 characters, mix of letters, numbers, symbols)

2. **Enable Two-Factor Authentication**:
   - Highly recommended for all users
   - Especially important for administrative accounts
   - Protects against password compromise

3. **Strong Encryption Key**: 
   - Use a minimum 32-character random encryption key
   - Store securely - without it, you cannot access your database
   - Consider using a password manager to generate and store it

4. **Database Security**:
   - Set appropriate file permissions: `chmod 600 znc_logs.db`
   - Keep regular encrypted backups
   - Store backups in a different location

5. **Production Server**: 
   - The systemd service uses Gunicorn (WSGI server) for production
   - Do NOT use Flask's development server (`app.run()`) in production
   - Never run with `debug=True` in production

6. **Network Access**: 
   - By default, the app listens on `0.0.0.0` (all interfaces)
   - For local-only access, change to `127.0.0.1` in the systemd service file
   - For remote access, use a reverse proxy with HTTPS

7. **HTTPS/TLS**: 
   - For production, use a reverse proxy (nginx/Apache) with SSL
   - Never transmit passwords over unencrypted connections
   - Use Let's Encrypt for free SSL certificates

8. **User Account Security**:
   - Remove unused accounts regularly
   - Enforce strong password policies
   - Monitor user activity through logs
   - Disable accounts instead of deleting (to preserve audit trail)

9. **Backup Security**: 
   - Backups are encrypted with the same key as the database
   - Store backups securely; they contain sensitive IRC logs
   - Test backup restoration periodically

10. **File Permissions**: 
    - Restrict access to the database and application files
    - Only the application user should have access
    - Never run as root

11. **Session Security**:
    - Change `app.secret_key` to a random value
    - Sessions expire when browser closes
    - Log out when finished using the application

12. **Audit and Monitoring**:
    - Review systemd logs regularly: `journalctl -u znc-search`
    - Monitor failed login attempts
    - Keep import logs for troubleshooting

## Performance Tips

1. **Regular Maintenance**: Run `vacuum` and `reindex` monthly
2. **Incremental Imports**: Use `--incremental` flag for faster updates
3. **Limit Search Results**: Use date ranges to narrow searches
4. **Database Location**: Store on SSD for better performance
5. **Backup Strategy**: Keep backups on separate storage
6. **Worker Processes**: Adjust Gunicorn workers based on CPU cores
7. **Query Optimization**: Use specific network/channel filters when possible

## Requirements

### Python Packages
- `flask==3.0.0` - Web framework
- `flask-cors==4.0.0` - Cross-origin resource sharing
- `gunicorn==21.2.0` - WSGI HTTP server (for production deployment)
- `pysqlcipher3==1.2.0` - Encrypted SQLite database
- `pyotp==2.9.0` - TOTP-based 2FA *(NEW)*
- `qrcode==8.2` - QR code generation for 2FA *(NEW)*
- `pillow==12.1.0` - Image processing for QR codes *(NEW)*

### System Requirements
- Minimum 512 MB RAM
- Storage: ~2-5 MB per 10,000 log lines (encrypted)
- Linux with systemd (for service mode)

## License

This project is provided as-is for personal use.

## Support

For issues, questions, or feature requests, please check:
1. This README for common solutions
2. The troubleshooting section
3. Log files for error messages
4. User management documentation for account issues

## Changelog

### Version 2.0
- **Added**: Multi-user support with database-backed accounts
- **Added**: Two-factor authentication (TOTP-based)
- **Added**: User management CLI (`user_admin.py`)
- **Added**: Password change via web interface
- **Added**: 2FA setup and management via web interface
- **Added**: Migration script for upgrading from v1.0
- **Added**: User audit trails (created_at, updated_at)
- **Enhanced**: Security with per-user credentials
- **Enhanced**: Session management
- **Changed**: Removed hardcoded user dictionary in favor of database

### Version 1.0
- Initial release
- Encrypted database support
- Web-based search interface
- Automatic import scheduling
- Database maintenance utilities
- Systemd service integration

---

## Quick Reference

### Common Commands

```bash
# User Management
python3 user_admin.py list                    # List all users
python3 user_admin.py add <username>          # Add user
python3 user_admin.py password <username>     # Reset password
python3 user_admin.py disable-2fa <username>  # Disable 2FA
python3 user_admin.py delete <username>       # Delete user
python3 user_admin.py info <username>         # User info

# Migration
python3 migrate_add_users.py                  # Run migration

# Log Import
python3 import_logs.py                        # Full import
python3 import_logs.py --incremental          # Incremental import
python3 import_logs.py --network libera       # Import one network

# Database Utilities
python3 db_utils.py stats                     # View statistics
python3 db_utils.py vacuum                    # Optimize database
python3 db_utils.py backup                    # Create backup
python3 db_utils.py cleanup                   # Clean old backups

# Service Management
sudo systemctl start znc-search               # Start service
sudo systemctl stop znc-search                # Stop service
sudo systemctl restart znc-search             # Restart service
sudo systemctl status znc-search              # Check status
sudo journalctl -u znc-search -f              # View logs
```

### Default Credentials

**After Migration:**
- Username: `admin`
- Password: `admin`

**🚨 CHANGE IMMEDIATELY AFTER FIRST LOGIN! 🚨**