from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import hashlib
from datetime import datetime
from functools import wraps
from pysqlcipher3 import dbapi2 as sqlite

app = Flask(__name__)
app.secret_key = 'THE_iNSTALL.SH_FILE_HANDLES_THIS'
CORS(app)

# Configuration
DB_PATH = 'znc_logs.db'
DB_KEY = 'THE_iNSTALL.SH_FILE_HANDLES_THIS'  # Change this to a strong encryption key

# Network display name mapping (OPTIONAL)
NETWORK_NAMES = {}

# User authentication
USERS = {
    'admin': 'THE_iNSTALL.SH_FILE_HANDLES_THIS'
}

def get_db():
    """Get database connection with encryption"""
    conn = sqlite.connect(DB_PATH)
    conn.execute(f"PRAGMA key = '{DB_KEY}'")
    conn.execute("PRAGMA cipher_compatibility = 4")
    return conn

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
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    if username in USERS and USERS[username] == hashed:
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/networks', methods=['GET'])
@login_required
def get_networks():
    """List available networks from database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT id, display_name 
        FROM networks 
        ORDER BY display_name
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
    """List available channels for a network"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT channel_name 
        FROM log_entries 
        WHERE network_id = ? 
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
    log_date = data.get('date')  # Format: YYYY-MM-DD
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
            'network': row[1],  # display_name
            'network_id': row[0],  # network_id
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
    
    # For production, use a proper WSGI server like gunicorn
    app.run(host='0.0.0.0', port=5000, debug=False)