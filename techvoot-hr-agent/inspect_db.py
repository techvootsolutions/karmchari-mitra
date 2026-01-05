
import sqlite3
import pandas as pd

conn = sqlite3.connect('hr_candidates.db')
try:
    df = pd.read_sql_query("SELECT * FROM call_logs", conn)
    print("Call Logs Data:")
    print(df.to_string())
    
    df_cand = pd.read_sql_query("SELECT id, name, status FROM candidates", conn)
    print("\nCandidates Data:")
    print(df_cand.to_string())
except Exception as e:
    print(e)
finally:
    conn.close()
