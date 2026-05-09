import sqlite3

def patch_database_v3():
    db_file = 'iska_database.db'
    conn = sqlite3.connect(db_file)
    try:
        conn.execute('ALTER TABLE query_logs ADD COLUMN session_id TEXT')
        conn.commit()
        print("Success! Added 'session_id' to query_logs.")
    except Exception as e:
        print(f"Notice: {e}")
    conn.close()

if __name__ == "__main__":
    patch_database_v3()