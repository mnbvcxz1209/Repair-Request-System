from dotenv import load_dotenv
import os
import pymysql
from werkzeug.security import generate_password_hash

load_dotenv()

def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", ""),
        port=int(os.getenv("DB_PORT", "")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ic_system"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

username = "admin"
password = "1"  

pw_hash = generate_password_hash(password)

conn = get_conn()
try:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s)",
            (username, pw_hash),
        )
    conn.commit()
    print(" admin created:", username, password)
finally:
    conn.close()
