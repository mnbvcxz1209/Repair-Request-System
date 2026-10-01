from dotenv import load_dotenv
import os
import pymysql

load_dotenv()

print("DB_HOST =", os.getenv("DB_HOST"))
print("DB_PORT =", os.getenv("DB_PORT"))
print("DB_USER =", os.getenv("DB_USER"))
print("DB_NAME =", os.getenv("DB_NAME"))
print("DB_PASSWORD =", "SET" if os.getenv("DB_PASSWORD") else "EMPTY")

try:
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
    )
    print(" MySQL 連線成功")
    conn.close()
except Exception as e:
    print(" MySQL 連線失敗：")
    print(e)
