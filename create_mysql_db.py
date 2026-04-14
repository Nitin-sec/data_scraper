"""
One-time utility to create the MySQL database if it does not exist.
Does NOT drop or modify an existing database.
Run this before running setup.py for the first time.
"""
import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('MYSQL_HOST', 'localhost')
port = int(os.getenv('MYSQL_PORT', '3306'))
user = os.getenv('MYSQL_USER')
password = os.getenv('MYSQL_PASSWORD')
database = os.getenv('MYSQL_DB')

if not all([user, password, database]):
    raise SystemExit("MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DB must be set in .env")

# Validate database name is a safe identifier
if not database.replace('_', '').isalnum():
    raise SystemExit(f"Unsafe database name: {database!r}")

print(f"Connecting to MySQL at {host}:{port} as {user}")

try:
    connection = pymysql.connect(host=host, port=port, user=user, password=password)

    with connection.cursor() as cursor:
        # Parameterized check - safe against injection
        cursor.execute(
            "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
            (database,)
        )
        if cursor.fetchone():
            print(f"Database '{database}' already exists. Nothing to do.")
        else:
            # database name is validated as alphanumeric+underscore above
            cursor.execute(
                f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"Created database: {database}")

    connection.close()

except Exception as e:
    raise SystemExit(f"Error: {e}")
