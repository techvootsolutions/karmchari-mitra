import sqlite3

def migrate_questions():
    print("Adding custom_questions to job_rules...")
    conn = sqlite3.connect('hr_candidates.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('ALTER TABLE job_rules ADD COLUMN custom_questions TEXT')
        print("Added custom_questions column.")
    except sqlite3.OperationalError:
        print("Column custom_questions already exists.")
        
    # Update default rules with sample questions
    questions_wp = """1. How long have you worked with WordPress?
2. Have you developed any custom plugins?
3. Are you familiar with WooCommerce hooks?"""

    questions_react = """1. What is the difference between State and Props?
2. Have you used Redux for state management?
3. Explain the Virtual DOM."""

    cursor.execute('UPDATE job_rules SET custom_questions = ? WHERE role_keyword = ?', (questions_wp, 'WordPress'))
    cursor.execute('UPDATE job_rules SET custom_questions = ? WHERE role_keyword = ?', (questions_react, 'React'))
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_questions()
