# ZNC Log Search

A secure, encrypted web-based search interface for ZNC IRC logs with automatic import capabilities.

## Features

### 🔒 Security
- **Encrypted Database**: All logs stored in an encrypted SQLite database using SQLCipher
- **Password Protection**: Web interface protected with SHA-256 hashed passwords
- **Session Management**: Secure session handling with Flask

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

### Manual Installation

If you prefer manual installation:

1. **Install Python dependencies:**
   ```bash
   pip3 install flask flask-cors pysqlcipher3
   ```

2. **Configure the application:**
   
   Edit the following files and update the configuration variables:
   - `app.py`: Set `DB_KEY` and `USERS` (password)
   - `import_logs.py`: Set `ZNC_BASE_PATH` and `DB_KEY`
   - `db_utils.py`: Set `DB_KEY`

3. **Initialize the database:**
   ```bash
   python3 import_logs.py
   ```

4. **Start the web application:**
   ```bash
   python3 app.py
   ```

## Configuration

### Database Encryption Key

The encryption key must be **identical** across all three files:
- `app.py`
- `import_logs.py`
- `db_utils.py`

**Example:**
```python
DB_KEY = 'your-strong-encryption-key-here-use-at-least-32-characters'
```

### User Authentication

Default credentials in `app.py`:
- Username: `admin`
- Password: `admin` (SHA-256 hashed)

**To change the password:**
```bash
echo -n "your-new-password" | sha256sum
```

Update the hash in `app.py`:
```python
USERS = {
    'admin': 'your-sha256-hash-here'
}
```

### Network Display Names (Optional)

Customize network display names in `app.py` and `import_logs.py`:
```python
NETWORK_NAMES = {
    'libera': 'Libera.Chat',
    'oftc': 'OFTC',
    'efnet': 'EFnet'
}
```

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

1. Start the application:
   ```bash
   python3 app.py
   ```

2. Open your browser to: `http://localhost:5000`

3. Log in with your credentials

4. Use the search interface:
   - Select network and channel (optional)
   - Enter search query
   - Set date range (optional)
   - Click "Search"

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
Type=simple
User=username
WorkingDirectory=/home/username/apps/znc_search
ExecStart=/usr/bin/python3 /home/username/apps/znc_search/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

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
- `POST /api/login` - Authenticate user
- `POST /api/logout` - End session

### Data Retrieval
- `GET /api/networks` - List available networks
- `GET /api/channels/<network>` - List channels for a network
- `GET /api/stats` - Get database statistics
- `POST /api/search` - Search logs
- `POST /api/context` - Get context around a specific line

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

**Solution**: Encryption key mismatch. Ensure `DB_KEY` is identical in all files.

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

### Port Already in Use

**Problem**: "Address already in use: Port 5000"

**Solution**: Change port in `app.py`:
```python
app.run(host='0.0.0.0', port=5001, debug=False)
```

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

1. **Change Default Password**: Always change the default admin password
2. **Strong Encryption Key**: Use a minimum 32-character random encryption key
3. **Network Access**: By default, the app listens on `0.0.0.0` (all interfaces)
   - For local-only access, change to `127.0.0.1` in `app.py`
4. **HTTPS**: For production, use a reverse proxy (nginx/Apache) with SSL
5. **Backups**: Store backups securely; they contain sensitive IRC logs
6. **File Permissions**: Restrict access to the database and application files

## Performance Tips

1. **Regular Maintenance**: Run `vacuum` and `reindex` monthly
2. **Incremental Imports**: Use `--incremental` flag for faster updates
3. **Limit Search Results**: Use date ranges to narrow searches
4. **Database Location**: Store on SSD for better performance
5. **Backup Strategy**: Keep backups on separate storage

## Requirements

### Python Packages
- `flask` - Web framework
- `flask-cors` - Cross-origin resource sharing
- `pysqlcipher3` - Encrypted SQLite database

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

## Changelog

### Version 1.0
- Initial release
- Encrypted database support
- Web-based search interface
- Automatic import scheduling
- Database maintenance utilities
- Systemd service integration
