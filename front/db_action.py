import sqlite3 as sql
from sqlite3 import Error

def get_db_connection():
    try:
        conn = sql.connect('front/db.sqlite')
    except Error as e:
        print(e)
    conn.row_factory = sql.Row
    return conn