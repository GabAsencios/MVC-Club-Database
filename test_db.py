import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "ssl_ca": os.getenv("DB_SSL_CA"),
    "ssl_verify_cert": True,
    "ssl_verify_identity": True,
}

conn = mysql.connector.connect(**DB_CONFIG)
cur = conn.cursor()
cur.execute("SELECT DATABASE(), VERSION();")
print(cur.fetchone())
cur.close()
conn.close()