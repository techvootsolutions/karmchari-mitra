from werkzeug.security import generate_password_hash
import sys
import os

# Add parent directory to path to import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

def seed_admin_user():
    print("Creating admin user...")
    conn = database.get_db_connection()
    
    # Check if admin exists
    existing = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if existing:
        print("Admin user already exists.")
        return

    password_hash = generate_password_hash('admin123')
    conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ('admin', password_hash))
    conn.commit()
    conn.close()
    print("Admin user created successfully!")
    print("Username: admin")
    print("Password: admin123")

if __name__ == "__main__":
    seed_admin_user()
