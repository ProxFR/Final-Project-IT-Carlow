import os
import sqlite3
from werkzeug.security import generate_password_hash

class database():
    def __init__(self):
        pass

    def generate():

        connection = sqlite3.connect('front/db.sqlite')
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS "user" (
            "id"	INTEGER NOT NULL,
            "email"	VARCHAR(100),
            "password"	VARCHAR(100),
            "name"	VARCHAR(1000),
            "creation_date"	VARCHAR(1000),
            PRIMARY KEY("id"),
            UNIQUE("email")
        );''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS "hash_type" (
            "id"	INTEGER,
            "type_name"	TEXT,
            "hashcat_mode"	TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS "wordlists" (
            "id"	INTEGER,
            "name"	TEXT,
            "url"	TEXT,
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS "instances" (
            "id"	INTEGER,
            "internal_ip"	TEXT,
            "droplet_id"	TEXT,
            "instance_name"	TEXT NOT NULL,
            "instance_size"	TEXT NOT NULL,
            "instance_status"	TEXT NOT NULL,
            "instance_type"	TEXT NOT NULL,
            "task_progression"	INTEGER NOT NULL,
            "user_id"	INTEGER NOT NULL,
            "task_wordlist"	TEXT NOT NULL,
            "instance_power"	TEXT NOT NULL,
            "task_id"	INTEGER,
            "token"	VARCHAR(16) NOT NULL,
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS "tasks" (
            "id"	INTEGER,
            "task_name"	TEXT NOT NULL,
            "hash_type"	TEXT NOT NULL,
            "hash"	TEXT NOT NULL,
            "plaintext"	TEXT DEFAULT '---',
            "status"	TEXT NOT NULL,
            "start_time"	NUMERIC,
            "time_spent"	TEXT DEFAULT '---',
            "result"	TEXT DEFAULT '---',
            PRIMARY KEY("id" AUTOINCREMENT)
        );''')

        try: 
            cursor.execute('''INSERT INTO "user" ("id","email","password","name","creation_date") VALUES (1, ?, ?,'Admin','27/05/2022 21:01:18');''', (os.getenv('APP_ADMIN_EMAIL'), generate_password_hash(os.getenv('APP_ADMIN_PASS'), method='sha256')))
        except:
            pass

        try: 
            cursor.execute('''INSERT INTO "hash_type" ("id","type_name","hashcat_mode") VALUES (1,'MD5','0'),
            (2,'SHA1','100'),
            (3,'SHA256','1400'),
            (4,'SHA512','1700');''')
        except:
            pass

        try: 
            cursor.execute('''INSERT INTO "wordlists" ("id","name","url") VALUES (1,'rockyou.txt','https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt'),
            (2,'10-million-password.txt','https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt');''')
        except:
            pass

        connection.commit()
        connection.close()
