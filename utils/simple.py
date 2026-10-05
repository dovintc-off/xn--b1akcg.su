# simple.py created by DOV1NTC powered by XWARED TEAM(C)
import os, json
from utils.database_init import get_db
from utils.log import log

def load_quizzes_data(path: str):
    if not os.path.exists(path): 
        log("path is not exists", "error")
        return None
    try:
        with open(os.path.join(path, "data", "quizzes.json"), "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        log(f"Some error: {e}", "error")
        return None
        
def _archive_old_logs(conn, ARCHIVE_THRESHOLD, LOGS_DIR):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connect_logs ORDER BY id ASC LIMIT ?", (ARCHIVE_THRESHOLD,))
        old_logs_list = [dict(row) for row in cursor.fetchall()]
        
        if len(old_logs_list) < ARCHIVE_THRESHOLD: 
            return
            
        first_date = old_logs_list[0]['request_date'].replace(':', '-').replace(' ', '_')
        filename = f"archive_{first_date}.json"
        filepath = os.path.join(LOGS_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(old_logs_list, f, ensure_ascii=False)
            
        ids_to_delete = [item['id'] for item in old_logs_list]
        placeholders = ','.join('?' for _ in ids_to_delete)
        conn.execute(f"DELETE FROM connect_logs WHERE id IN ({placeholders})", ids_to_delete)
        conn.commit()
        log(f"Archived {len(old_logs_list)} logs to {filename}", "info")
    except Exception as e:
        log(f"Archive error: {e}", "error")

def save_log(ip, path, BASE_DIR, MAX_LOG_ENTRIES, ARCHIVE_THRESHOLD):
    conn = get_db(BASE_DIR)
    if not conn: return
    
    try:
        conn.execute("INSERT INTO connect_logs (ip, path) VALUES (?, ?)", (ip, path))
        conn.commit()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM connect_logs")
        count = cursor.fetchone()['cnt']
        
        if count > MAX_LOG_ENTRIES:
            excess = count - MAX_LOG_ENTRIES + ARCHIVE_THRESHOLD
            cursor.execute("DELETE FROM connect_logs WHERE id IN (SELECT id FROM connect_logs ORDER BY id ASC LIMIT ?)", (excess,))
            conn.commit()
            
        cursor.execute("SELECT COUNT(*) as cnt FROM connect_logs")
        if cursor.fetchone()['cnt'] >= MAX_LOG_ENTRIES:
             _archive_old_logs(conn, ARCHIVE_THRESHOLD, os.path.join(BASE_DIR, "data", "logs"))
             
    except Exception as e:
        log(f"Log save error: {e}", "error")
    finally:
        conn.close()
        
def check_user_admin_rights(user_id, BASE_DIR):
    if not user_id: return False
    conn = get_db(BASE_DIR)
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT permissions FROM users WHERE id = ? AND permissions = 'admin'", (user_id,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        log(f"Error checking admin rights in DB: {e}", "error")
        return False
    finally:
        conn.close()
    
def get_admin_stats(BASE_DIR, date_from=None, date_to=None, limit=20):
    conn = get_db(BASE_DIR)
    if not conn: return {'online': 0, 'logs': [], 'total_in_range': 0}
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT ip) as count 
            FROM connect_logs 
            WHERE request_date > datetime('now', '-5 minutes')
        """)
        online_count = cursor.fetchone()['count'] or 0
        
        query = "SELECT ip, path, request_date FROM connect_logs WHERE 1=1"
        params = []
        
        if date_from:
            query += " AND request_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND request_date <= ?"
            params.append(date_to)
            
        query += " ORDER BY request_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        
        count_query = "SELECT COUNT(*) as cnt FROM connect_logs WHERE 1=1"
        count_params = []
        if date_from: 
            count_query += " AND request_date >= ?"; count_params.append(date_from)
        if date_to: 
            count_query += " AND request_date <= ?"; count_params.append(date_to)
            
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['cnt']
        
        return {
            'online': online_count,
            'logs': logs,
            'total_in_range': total
        }
    except Exception as e:
        log(f"Stats error: {e}", "error")
        return {'online': 0, 'logs': [], 'total_in_range': 0}
    finally:
        conn.close()