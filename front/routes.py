import json
import os
import sqlite3 as sql
from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from front.db_action import get_db_connection
from instances.main import drop
from .models import User
from .start import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect("/dashboard", code=302)
    else:
        return render_template('login.html')

@main.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    workers = conn.execute('SELECT instance_name, internal_ip, task_progression, task_wordlist, instance_status, status FROM instances INNER JOIN tasks ON instances.task_id = tasks.id WHERE user_id = ?', (current_user.get_id()))
                
    return render_template('dashboard.html', workers=workers)

@main.route('/attack')
@login_required
def attack():
    conn = get_db_connection()
    hash_type = conn.execute('SELECT type_name FROM hash_type')
    wordlists = conn.execute('SELECT name FROM wordlists')
    return render_template('attack.html', hash_type=hash_type, wordlists=wordlists)

@main.route('/wordlist')
@login_required
def wordlist():
    conn = get_db_connection()
    wordlists = conn.execute('SELECT id, name, url FROM wordlists')
    return render_template('wordlist.html', wordlists=wordlists)

@main.route('/wordlist', methods=['POST'])
@login_required
def add_wordlist():
    conn = get_db_connection()
    sql = ''' INSERT INTO wordlists(name,url)
              VALUES(?,?) '''
    cursor = conn.cursor()
    cursor.execute(sql, (request.form.get('name'),request.form.get('url')))
    conn.commit()
    return redirect(url_for('main.wordlist'))

@main.route('/wordlist/delete/<id>', methods=['POST'])
@login_required
def del_wordlist(id):
    conn = get_db_connection()

    # Remove a row
    sql = 'DELETE FROM wordlists WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, [id])

    # Remove 1 to the id to get continuity
    sql = 'UPDATE sqlite_sequence SET seq = seq - 1 WHERE name="wordlists"'
    cur = conn.cursor()
    cur.execute(sql)
    
    conn.commit()
    return redirect(url_for('main.wordlist'))

@main.route('/tasks')
@login_required
def tasks():
    conn = get_db_connection()
    tasks = conn.execute('SELECT id, task_name, hash, plaintext, status, time_spent, result, hash_type FROM tasks')
    return render_template('tasks.html', tasks=tasks)

@main.route('/tasks/delete/<id>', methods=['POST'])
@login_required
def del_task(id):
    conn = get_db_connection()

    # Remove a row
    sql = 'DELETE FROM tasks WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, [id])
    
    conn.commit()
    return redirect(url_for('main.tasks'))

@main.route('/users')
@login_required
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@main.route('/users/delete/<id>', methods=['POST'])
@login_required
def del_user(id):
    conn = get_db_connection()

    # Remove a row
    sql = 'DELETE FROM user WHERE id=?'
    cur = conn.cursor()
    cur.execute(sql, [id])
    
    conn.commit()
    return redirect(url_for('main.users'))

@main.route('/supervision')
@login_required
def supervision():
    return redirect(os.getenv('MONITORING_URL') + "/grafana", code=302)

