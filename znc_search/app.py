from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import os
import re
from datetime import datetime
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'CHANGE_IT_TO_YOUR_KEY'  # Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
CORS(app)

# Configuration
ZNC_BASE_PATH = '/home/<USERNAME>/.znc/users/klapvogn/networks'

# Network display name mapping (OPTIONAL - leave empty for automatic detection)
# Add entries here ONLY if you want custom short names
# Example:
#NETWORK_NAMES = {
#    'NETWORK1': 'SHORT NAME1',
#}
NETWORK_NAMES = {}

# User authentication
# Generate hash with: python3 -c "import hashlib; print(hashlib.sha256('YourPassword'.encode()).hexdigest())"
USERS = {
    'admin': 'CHANGE_IT_TO_YOUR_KEY'
}

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
    """List available networks - auto-detects all networks with logging enabled"""
    networks = []
    
    if os.path.exists(ZNC_BASE_PATH):
        for item in os.listdir(ZNC_BASE_PATH):
            network_path = os.path.join(ZNC_BASE_PATH, item, 'moddata/log')
            if os.path.exists(network_path):
                # Use custom display name if defined in NETWORK_NAMES, otherwise capitalize folder name
                display_name = NETWORK_NAMES.get(item, item.capitalize())
                networks.append({
                    'id': item,
                    'name': display_name
                })
    
    # Sort by display name
    networks.sort(key=lambda x: x['name'])
    
    return jsonify({'networks': networks})

@app.route('/api/channels/<network>', methods=['GET'])
@login_required
def get_channels(network):
    """List available channels for a network"""
    channels = []
    
    log_path = os.path.join(ZNC_BASE_PATH, network, 'moddata/log')
    
    if os.path.exists(log_path):
        for item in os.listdir(log_path):
            item_path = os.path.join(log_path, item)
            if os.path.isdir(item_path):
                channels.append(item)
    
    return jsonify({'channels': sorted(channels)})

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
    
    results = []
    
    # Build path to channel logs
    if channel:
        # Search specific channel
        search_paths = [os.path.join(ZNC_BASE_PATH, network, 'moddata/log', channel)]
    else:
        # Search all channels in network
        log_base = os.path.join(ZNC_BASE_PATH, network, 'moddata/log')
        search_paths = []
        if os.path.exists(log_base):
            for item in os.listdir(log_base):
                item_path = os.path.join(log_base, item)
                if os.path.isdir(item_path):
                    search_paths.append(item_path)
    
    # Convert dates if provided
    start_dt = None
    end_dt = None
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            pass
    
    # Search through each path
    for channel_path in search_paths:
        if not os.path.exists(channel_path):
            continue
        
        channel_name = os.path.basename(channel_path)
        
        for log_file in sorted(os.listdir(channel_path)):
            if not log_file.endswith('.log'):
                continue
            
            # Parse date from filename (handles both ZNC formats)
            # Format 1: 2025-12-04.log (YYYY-MM-DD)
            # Format 2: channel_20251204.log (channel_YYYYMMDD)
            try:
                date_str = log_file.replace('.log', '')
                
                # Try format with dashes first (2025-12-04)
                try:
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    # Try format without dashes (20251204 or channel_20251204)
                    date_str = date_str.split('_')[-1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                
                # Filter by date range if provided
                if start_dt and file_date < start_dt:
                    continue
                if end_dt and file_date > end_dt:
                    continue
                    
            except (ValueError, IndexError):
                # Skip files that don't match expected date formats
                continue
            
            # Search within file
            file_path = os.path.join(channel_path, log_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        # Search logic
                        if case_sensitive:
                            match = query in line
                        else:
                            match = query.lower() in line.lower()
                        
                        if match:
                            # Use custom network name if defined, otherwise use folder name
                            network_display = NETWORK_NAMES.get(network, network.capitalize())
                            
                            results.append({
                                'network': network_display,
                                'channel': channel_name,
                                'file': log_file,
                                'line': line_num,
                                'content': line.strip(),
                                'date': date_str
                            })
                            
                            # Limit results to prevent overwhelming response
                            if len(results) >= 1000:
                                return jsonify({
                                    'results': results,
                                    'total': len(results),
                                    'truncated': True
                                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
    
    return jsonify({
        'results': results,
        'total': len(results),
        'truncated': False
    })

if __name__ == '__main__':
    # For production, use a proper WSGI server like gunicorn
    app.run(host='0.0.0.0', port=5000, debug=False)
