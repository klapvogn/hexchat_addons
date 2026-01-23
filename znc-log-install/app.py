from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import hashlib
from datetime import datetime
from functools import wraps
from pysqlcipher3 import dbapi2 as sqlite
import pyotp
import qrcode
import io
import base64

app = Flask(__name__, static_folder='static')
# Serve favicon directly
app.secret_key = '7c5887855a2210e21ce73409d0ebb965e974487dedbb2f6c808dcbc76ab42b1e'
CORS(app)

# Configuration
DB_PATH = '/home/klapvogn/apps/znc_search/znc_logs.db'
DB_KEY = '28ab2972b162ccc779d905cb6b422cd707d0470aef68c4289b41fa8ea42fb7df'

# Network display name mapping (OPTIONAL)
NETWORK_NAMES = {}

def get_db():
    """Get database connection with encryption"""
    conn = sqlite.connect(DB_PATH)
    conn.execute(f"PRAGMA key = '{DB_KEY}'")
    conn.execute("PRAGMA cipher_compatibility = 4")
    return conn

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initialize the database schema"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS networks (
            id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id TEXT NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (network_id) REFERENCES networks(id),
            UNIQUE(network_id, name)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            network_id TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            log_date DATE NOT NULL,
            line_number INTEGER NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (network_id) REFERENCES networks(id)
        )
    ''')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for efficient searching
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_log_network 
        ON log_entries(network_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_log_channel 
        ON log_entries(channel_name)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_log_date 
        ON log_entries(log_date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_log_content 
        ON log_entries(content)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_log_composite 
        ON log_entries(network_id, channel_name, log_date)
    ''')
    
    # Check if default admin user exists, if not create it
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        # Default password is 'admin' - CHANGE THIS IMMEDIATELY!
        default_password_hash = hash_password('admin')
        cursor.execute('''
            INSERT INTO users (username, password_hash, totp_enabled) 
            VALUES (?, ?, 0)
        ''', ('admin', default_password_hash))
        print("WARNING: Default admin user created with password 'admin'. Please change it immediately!")
    
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    totp_code = data.get('totp_code')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user from database
    cursor.execute('''
        SELECT id, username, password_hash, totp_secret, totp_enabled 
        FROM users WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    user_id, username, password_hash, totp_secret, totp_enabled = user
    
    # Verify password
    hashed = hash_password(password)
    if hashed != password_hash:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check if 2FA is enabled
    if totp_enabled:
        if not totp_code:
            # Password is correct but need 2FA code
            return jsonify({
                'requires_2fa': True,
                'message': 'Please enter your 2FA code'
            }), 200
        
        # Verify TOTP code
        totp = pyotp.TOTP(totp_secret)
        if not totp.verify(totp_code, valid_window=1):
            return jsonify({'error': 'Invalid 2FA code'}), 401
    
    # Login successful
    session['logged_in'] = True
    session['username'] = username
    session['user_id'] = user_id
    
    return jsonify({'success': True})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/user/password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400
    
    if len(new_password) < 8:
        return jsonify({'error': 'New password must be at least 8 characters'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get current user
    cursor.execute('''
        SELECT password_hash FROM users WHERE id = ?
    ''', (session['user_id'],))
    
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Verify current password
    current_hash = hash_password(current_password)
    if current_hash != user[0]:
        conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Update password
    new_hash = hash_password(new_password)
    cursor.execute('''
        UPDATE users 
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (new_hash, session['user_id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Password changed successfully'})

@app.route('/api/user/2fa/status', methods=['GET'])
@login_required
def get_2fa_status():
    """Get current 2FA status"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT totp_enabled FROM users WHERE id = ?
    ''', (session['user_id'],))
    
    result = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'enabled': bool(result[0]) if result else False
    })

@app.route('/api/user/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    """Generate new TOTP secret and QR code"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Generate new secret
    secret = pyotp.random_base32()
    
    # Save secret to database (not enabled yet)
    cursor.execute('''
        UPDATE users 
        SET totp_secret = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (secret, session['user_id']))
    
    conn.commit()
    conn.close()
    
    # Generate QR code
    username = session['username']
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name='IRC Log Search'
    )
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        'secret': secret,
        'qr_code': f'data:image/png;base64,{img_str}',
        'manual_entry': secret
    })

@app.route('/api/user/2fa/enable', methods=['POST'])
@login_required
def enable_2fa():
    """Enable 2FA after verifying a code"""
    data = request.json
    totp_code = data.get('code')
    
    if not totp_code:
        return jsonify({'error': 'Verification code required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user's secret
    cursor.execute('''
        SELECT totp_secret FROM users WHERE id = ?
    ''', (session['user_id'],))
    
    result = cursor.fetchone()
    if not result or not result[0]:
        conn.close()
        return jsonify({'error': 'No 2FA secret found. Please set up 2FA first.'}), 400
    
    secret = result[0]
    
    # Verify code
    totp = pyotp.TOTP(secret)
    if not totp.verify(totp_code, valid_window=1):
        conn.close()
        return jsonify({'error': 'Invalid verification code'}), 401
    
    # Enable 2FA
    cursor.execute('''
        UPDATE users 
        SET totp_enabled = 1, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '2FA enabled successfully'
    })

@app.route('/api/user/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """Disable 2FA"""
    data = request.json
    password = data.get('password')
    
    if not password:
        return jsonify({'error': 'Password required to disable 2FA'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verify password
    cursor.execute('''
        SELECT password_hash FROM users WHERE id = ?
    ''', (session['user_id'],))
    
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    password_hash = hash_password(password)
    if password_hash != result[0]:
        conn.close()
        return jsonify({'error': 'Invalid password'}), 401
    
    # Disable 2FA
    cursor.execute('''
        UPDATE users 
        SET totp_enabled = 0, totp_secret = NULL, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '2FA disabled successfully'
    })

@app.route('/api/networks', methods=['GET'])
@login_required
def get_networks():
    """List available networks from database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT n.id, n.display_name 
        FROM networks n
        INNER JOIN log_entries le ON n.id = le.network_id
        ORDER BY n.display_name
    ''')
    
    networks = []
    for row in cursor.fetchall():
        networks.append({
            'id': row[0],
            'name': row[1]
        })
    
    conn.close()
    return jsonify({'networks': networks})

@app.route('/api/channels/<network>', methods=['GET'])
@login_required
def get_channels(network):
    """List available channels for a network (only actual channels starting with #)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT channel_name 
        FROM log_entries 
        WHERE network_id = ? 
        AND channel_name LIKE '#%'
        ORDER BY channel_name
    ''', (network,))
    
    channels = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return jsonify({'channels': channels})

@app.route('/api/context', methods=['POST'])
@login_required
def get_context():
    """Get surrounding lines for a specific log entry"""
    data = request.json
    network = data.get('network')
    channel = data.get('channel')
    log_date = data.get('date')
    center_line = data.get('line')
    lines_before = data.get('lines_before', 2)
    lines_after = data.get('lines_after', 2)
    
    if not all([network, channel, log_date, center_line]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Calculate range
    start_line = max(1, center_line - lines_before)
    end_line = center_line + lines_after
    
    cursor.execute('''
        SELECT line_number, content
        FROM log_entries
        WHERE network_id = ? 
        AND channel_name = ? 
        AND log_date = ?
        AND line_number BETWEEN ? AND ?
        ORDER BY line_number
    ''', (network, channel, log_date, start_line, end_line))
    
    context = []
    for row in cursor.fetchall():
        context.append({
            'line': row[0],
            'content': row[1],
            'is_match': row[0] == center_line
        })
    
    # Get total lines for this date
    cursor.execute('''
        SELECT COUNT(*) FROM log_entries
        WHERE network_id = ? AND channel_name = ? AND log_date = ?
    ''', (network, channel, log_date))
    
    total_lines = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'context': context,
        'start_line': start_line,
        'end_line': end_line,
        'total_lines': total_lines,
        'can_expand_up': start_line > 1,
        'can_expand_down': end_line < total_lines
    })

@app.route('/api/search', methods=['POST'])
@login_required
def search_logs():
    data = request.json
    query = data.get('query', '')
    network = data.get('network', '')
    channel = data.get('channel', '')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    case_sensitive = data.get('case_sensitive', False)
    
    if not query:
        return jsonify({'error': 'Query required'}), 400
    
    if not network:
        return jsonify({'error': 'Network required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Build query
    sql_query = '''
        SELECT 
            le.network_id,
            n.display_name,
            le.channel_name,
            le.log_date,
            le.line_number,
            le.content
        FROM log_entries le
        JOIN networks n ON le.network_id = n.id
        WHERE le.network_id = ?
    '''
    params = [network]
    
    # Add channel filter if specified
    if channel:
        sql_query += ' AND le.channel_name = ?'
        params.append(channel)
    
    # Add date range filters
    if start_date:
        sql_query += ' AND le.log_date >= ?'
        params.append(start_date)
    
    if end_date:
        sql_query += ' AND le.log_date <= ?'
        params.append(end_date)
    
    # Add search filter
    if case_sensitive:
        sql_query += ' AND le.content LIKE ?'
        params.append(f'%{query}%')
    else:
        sql_query += ' AND LOWER(le.content) LIKE LOWER(?)'
        params.append(f'%{query}%')
    
    sql_query += ' ORDER BY le.log_date DESC, le.line_number ASC LIMIT 1000'
    
    cursor.execute(sql_query, params)
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'network': row[1],
            'network_id': row[0],
            'channel': row[2],
            'date': row[3],
            'line': row[4],
            'content': row[5]
        })
    
    conn.close()
    
    return jsonify({
        'results': results,
        'total': len(results),
        'truncated': len(results) >= 1000
    })

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get database statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get total entries
    cursor.execute('SELECT COUNT(*) FROM log_entries')
    total_entries = cursor.fetchone()[0]
    
    # Get date range
    cursor.execute('SELECT MIN(log_date), MAX(log_date) FROM log_entries')
    date_range = cursor.fetchone()
    
    # Get network count
    cursor.execute('SELECT COUNT(DISTINCT network_id) FROM log_entries')
    network_count = cursor.fetchone()[0]
    
    # Get channel count
    cursor.execute('SELECT COUNT(DISTINCT channel_name) FROM log_entries WHERE channel_name LIKE "#%"')
    channel_count = cursor.fetchone()[0]
    
    # Get network counts
    cursor.execute('''
        SELECT n.display_name, COUNT(*) 
        FROM log_entries le
        JOIN networks n ON le.network_id = n.id
        GROUP BY n.display_name
        ORDER BY COUNT(*) DESC
    ''')
    network_stats = [{'network': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'total_entries': total_entries,
        'network_count': network_count,
        'channel_count': channel_count,
        'date_range': {
            'start': date_range[0],
            'end': date_range[1]
        },
        'networks': network_stats
    })

if __name__ == '__main__':
    # Initialize database on first run
    if not os.path.exists(DB_PATH):
        print("Initializing encrypted database...")
        init_db()
        print("Database initialized. Run import_logs.py to import your ZNC logs.")
    else:
        # Make sure users table exists
        init_db()
    
    # For production, use a proper WSGI server like gunicorn
    app.run(host='0.0.0.0', port=5000, debug=False)