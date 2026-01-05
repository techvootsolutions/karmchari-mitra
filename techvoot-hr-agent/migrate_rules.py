import sqlite3

def migrate_rules_table():
    print("Creating job_rules table...")
    conn = sqlite3.connect('hr_candidates.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_keyword TEXT NOT NULL,
        min_years INT DEFAULT 0,
        max_years INT DEFAULT 100,
        min_salary INT DEFAULT 0,
        max_salary INT DEFAULT 0
    )
    ''')
    
    # Seed the user's requested defaults (optional, but helpful)
    # WordPress: 2-3 yrs, 33-39k
    # React: 7-8 yrs, 55-60k
    
    # Check if empty
    if cursor.execute('SELECT count(*) FROM job_rules').fetchone()[0] == 0:
        cursor.execute('INSERT INTO job_rules (role_keyword, min_years, max_years, min_salary, max_salary) VALUES (?, ?, ?, ?, ?)',
                      ('WordPress', 2, 3, 33000, 39000))
        cursor.execute('INSERT INTO job_rules (role_keyword, min_years, max_years, min_salary, max_salary) VALUES (?, ?, ?, ?, ?)',
                      ('React', 7, 8, 55000, 60000))
        print("Seeded default rules.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_rules_table()
