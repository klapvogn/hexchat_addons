#!/usr/bin/env python3
"""
Import ZNC logs into encrypted SQLite database

This script scans the ZNC log directory structure and imports all logs
into an encrypted SQLite database for faster searching.

Usage:
    python3 import_logs.py [--incremental]
    
Options:
    --incremental   Only import logs newer than the last import date
"""

import os
import sys
from datetime import datetime
from pysqlcipher3 import dbapi2 as sqlite
import argparse

# Configuration - should match app.py
ZNC_BASE_PATH = '/home/klapvogn/.znc/users/klapvogn/networks'
DB_PATH = 'znc_logs.db'
DB_KEY = 'IS_HANDLED_BY_INSTALL.SH'  # Must match app.py

# Network display name mapping (should match app.py)
NETWORK_NAMES = {}

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
    
    # Create import tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_last_import_date(conn):
    """Get the date of the last import"""
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM import_metadata WHERE key = ?', ('last_import_date',))
    row = cursor.fetchone()
    if row:
        try:
            return datetime.fromisoformat(row[0])
        except ValueError:
            return None
    return None

def set_last_import_date(conn, date):
    """Set the last import date"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO import_metadata (key, value) 
        VALUES (?, ?)
    ''', ('last_import_date', date.isoformat()))
    conn.commit()

def parse_log_date(filename):
    """Parse date from log filename"""
    date_str = filename.replace('.log', '')
    
    # Try format with dashes first (2025-12-04)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        pass
    
    # Try format without dashes (20251204 or channel_20251204)
    try:
        date_str = date_str.split('_')[-1]
        return datetime.strptime(date_str, '%Y%m%d')
    except ValueError:
        pass
    
    return None

def import_network(conn, network_id, incremental=False, last_import_date=None):
    """Import logs for a single network"""
    cursor = conn.cursor()
    
    # Get or create network entry
    display_name = NETWORK_NAMES.get(network_id, network_id.capitalize())
    cursor.execute('''
        INSERT OR REPLACE INTO networks (id, display_name) 
        VALUES (?, ?)
    ''', (network_id, display_name))
    
    log_base = os.path.join(ZNC_BASE_PATH, network_id, 'moddata/log')
    
    if not os.path.exists(log_base):
        print(f"  ⚠ Log directory not found: {log_base}")
        return 0
    
    total_imported = 0
    
    # Iterate through channels
    for channel_name in os.listdir(log_base):
        channel_path = os.path.join(log_base, channel_name)
        
        if not os.path.isdir(channel_path):
            continue
        
        print(f"  Processing channel: {channel_name}")
        
        # Get or create channel entry
        cursor.execute('''
            INSERT OR IGNORE INTO channels (network_id, name) 
            VALUES (?, ?)
        ''', (network_id, channel_name))
        
        # Process log files in this channel
        log_files = sorted([f for f in os.listdir(channel_path) if f.endswith('.log')])
        
        for log_file in log_files:
            log_date = parse_log_date(log_file)
            
            if not log_date:
                print(f"    ⚠ Skipping file with unparseable date: {log_file}")
                continue
            
            # Skip if incremental and file is older than last import
            if incremental and last_import_date and log_date < last_import_date:
                continue
            
            file_path = os.path.join(channel_path, log_file)
            
            # Check if this file has already been imported
            cursor.execute('''
                SELECT COUNT(*) FROM log_entries 
                WHERE network_id = ? 
                AND channel_name = ? 
                AND log_date = ?
            ''', (network_id, channel_name, log_date.strftime('%Y-%m-%d')))
            
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0 and incremental:
                continue
            
            # Delete existing entries for this file (for full re-import)
            if not incremental:
                cursor.execute('''
                    DELETE FROM log_entries 
                    WHERE network_id = ? 
                    AND channel_name = ? 
                    AND log_date = ?
                ''', (network_id, channel_name, log_date.strftime('%Y-%m-%d')))
            
            # Import the file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                # Batch insert for better performance
                entries = []
                for line_num, line in enumerate(lines, 1):
                    entries.append((
                        network_id,
                        channel_name,
                        log_date.strftime('%Y-%m-%d'),
                        line_num,
                        line.rstrip()
                    ))
                
                cursor.executemany('''
                    INSERT INTO log_entries 
                    (network_id, channel_name, log_date, line_number, content)
                    VALUES (?, ?, ?, ?, ?)
                ''', entries)
                
                total_imported += len(entries)
                print(f"    ✓ {log_file}: {len(entries)} lines")
                
            except Exception as e:
                print(f"    ✗ Error reading {log_file}: {e}")
                continue
    
    conn.commit()
    return total_imported

def main():
    parser = argparse.ArgumentParser(description='Import ZNC logs to encrypted SQLite database')
    parser.add_argument('--incremental', action='store_true', 
                       help='Only import new logs since last import')
    parser.add_argument('--network', type=str, 
                       help='Import only specific network')
    args = parser.parse_args()
    
    # Check if ZNC base path exists
    if not os.path.exists(ZNC_BASE_PATH):
        print(f"Error: ZNC base path not found: {ZNC_BASE_PATH}")
        print("Please update ZNC_BASE_PATH in this script.")
        sys.exit(1)
    
    # Initialize database if needed
    if not os.path.exists(DB_PATH):
        print("Initializing new encrypted database...")
        init_db()
    
    # Connect to database
    conn = get_db()
    
    # Get last import date for incremental imports
    last_import_date = None
    if args.incremental:
        last_import_date = get_last_import_date(conn)
        if last_import_date:
            print(f"Incremental import: only importing logs after {last_import_date.strftime('%Y-%m-%d')}")
        else:
            print("No previous import found, performing full import...")
    
    print(f"\nScanning ZNC logs from: {ZNC_BASE_PATH}")
    print("=" * 70)
    
    # Get list of networks
    networks = []
    if args.network:
        if os.path.exists(os.path.join(ZNC_BASE_PATH, args.network)):
            networks = [args.network]
        else:
            print(f"Error: Network '{args.network}' not found")
            sys.exit(1)
    else:
        networks = [d for d in os.listdir(ZNC_BASE_PATH) 
                   if os.path.isdir(os.path.join(ZNC_BASE_PATH, d))]
    
    # Import each network
    total_imported = 0
    for network_id in sorted(networks):
        print(f"\nImporting network: {network_id}")
        count = import_network(conn, network_id, args.incremental, last_import_date)
        total_imported += count
        print(f"  Total lines imported: {count:,}")
    
    # Update last import date
    set_last_import_date(conn, datetime.now())
    
    # Get final statistics
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM log_entries')
    total_entries = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT network_id) FROM log_entries')
    network_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT channel_name) FROM log_entries')
    channel_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(log_date), MAX(log_date) FROM log_entries')
    date_range = cursor.fetchone()
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("Import complete!")
    print(f"  New lines imported: {total_imported:,}")
    print(f"  Total lines in database: {total_entries:,}")
    print(f"  Networks: {network_count}")
    print(f"  Channels: {channel_count}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    print("\nDatabase encrypted and ready to use.")

if __name__ == '__main__':
    main()