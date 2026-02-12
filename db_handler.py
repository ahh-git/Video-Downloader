import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

# UNIQUE NAME TO PREVENT CONFLICTS
DB_NAME = "unisaver_ultimate_v3.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, name TEXT, photo TEXT, joined_at TEXT, is_banned INTEGER, remember_token TEXT)''')
    
    # 2. History Table
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, video_title TEXT, video_url TEXT, 
                  download_type TEXT, timestamp TEXT)''')
    
    # 3. Stats & Config
    c.execute('''CREATE TABLE IF NOT EXISTS stats 
                 (id INTEGER PRIMARY KEY, visits INTEGER, broadcast_msg TEXT, maintenance_mode INTEGER)''')
    
    # 4. Reports
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, url TEXT, issue TEXT, timestamp TEXT)''')

    # Initialize Defaults
    c.execute("SELECT count(*) FROM stats")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO stats (id, visits, broadcast_msg, maintenance_mode) VALUES (1, 0, '', 0)")
        
    conn.commit()
    conn.close()

# --- USER OPS ---
def add_user(email, name, photo):
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO users (email, name, photo, joined_at, is_banned, remember_token) VALUES (?, ?, ?, ?, ?, ?)", 
                  (email, name, photo, datetime.now(), 0, None))
        conn.commit()
    except: pass
    conn.close()

def log_download(email, title, url, dtype):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO history (email, video_title, video_url, download_type, timestamp) VALUES (?, ?, ?, ?, ?)",
                (email, title, url, dtype, datetime.now()))
        conn.commit()
    except: pass
    conn.close()

def get_user_stats(email):
    conn = get_connection()
    try: count = conn.execute("SELECT count(*) FROM history WHERE email = ?", (email,)).fetchone()[0]
    except: count = 0
    conn.close()
    return count

def clear_user_history(email):
    conn = get_connection()
    conn.execute("DELETE FROM history WHERE email = ?", (email,))
    conn.commit()
    conn.close()

# --- ADMIN & ANALYTICS ---
def get_daily_downloads():
    conn = get_connection()
    try:
        seven_days_ago = datetime.now() - timedelta(days=7)
        df = pd.read_sql_query("SELECT timestamp FROM history", conn)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            mask = (df['timestamp'] > seven_days_ago)
            df = df.loc[mask]
            daily = df.groupby(df['timestamp'].dt.date).size().reset_index(name='count')
            return daily
        return pd.DataFrame()
    except: return pd.DataFrame()
    conn.close()

def increment_visitor():
    conn = get_connection()
    try:
        conn.execute("UPDATE stats SET visits = visits + 1 WHERE id = 1")
        conn.commit()
    except: pass
    conn.close()

def set_config(msg, maintenance):
    conn = get_connection()
    try:
        conn.execute("UPDATE stats SET broadcast_msg = ?, maintenance_mode = ? WHERE id = 1", (msg, maintenance))
        conn.commit()
    except: pass
    conn.close()

def get_config():
    conn = get_connection()
    try:
        row = conn.execute("SELECT broadcast_msg, maintenance_mode FROM stats WHERE id = 1").fetchone()
        return row if row else ("", 0)
    except: return ("", 0)
    conn.close()

def get_global_stats():
    conn = get_connection()
    try:
        visits = conn.execute("SELECT visits FROM stats WHERE id = 1").fetchone()[0]
        users = conn.execute("SELECT count(*) FROM users").fetchone()[0]
        downloads = conn.execute("SELECT count(*) FROM history").fetchone()[0]
        reports = conn.execute("SELECT count(*) FROM reports").fetchone()[0]
    except: visits, users, downloads, reports = 0, 0, 0, 0
    conn.close()
    return visits, users, downloads, reports

def get_all_users():
    conn = get_connection()
    try: df = pd.read_sql_query("SELECT * FROM users", conn)
    except: df = pd.DataFrame()
    conn.close()
    return df

def toggle_ban(email, current):
    conn = get_connection()
    new = 1 if current == 0 else 0
    conn.execute("UPDATE users SET is_banned = ? WHERE email = ?", (new, email))
    conn.commit()
    conn.close()

def check_ban(email):
    conn = get_connection()
    try:
        res = conn.execute("SELECT is_banned FROM users WHERE email = ?", (email,)).fetchone()
        return res[0] if res else 0
    except: return 0
    conn.close()
