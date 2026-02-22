import sys
import os
import urllib.parse
import psycopg2

def check_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL environment variable is not set.")
        return

    # Handle postgres:// vs postgresql://
    db_url = db_url.replace("postgres://", "postgresql://")
    
    print(f"Connecting to: {db_url.split('@')[-1]}") # Print host only for security
    
    try:
        # Standard connection check
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✅ Success! Database Version: {version[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Connection Failed: {str(e)}")
        
        if "could not translate host name" in str(e):
            print("\n💡 DIAGNOSIS: This is a DNS issue.")
            print("- If you are local, use the EXTERNAL URL.")
            print("- If you are on Render, ensure both DB and App are in the same Region.")

if __name__ == "__main__":
    check_connection()
