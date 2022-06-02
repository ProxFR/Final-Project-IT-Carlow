import sqlite3 as sql
import json
from secrets import token_hex
from flask import Blueprint, flash, redirect, request, url_for
from flask_login import current_user, login_required
from front.db_action import get_db_connection
from instances.main import *
from humanfriendly import format_timespan
from datetime import datetime, timezone

api = Blueprint('api', __name__)


############################## INSTANCES CALLS ##############################

# Called when the instance is created
@api.route('/api/created', methods=['POST'])
def created():
    conn = get_db_connection()
    content = request.json

    instance_status = str(content['instance_status']) # 'Ready'
    instance_token = str(request.headers.get('Token'))

    # Updating instance_status in instances
    sql = 'UPDATE instances SET instance_status = ? WHERE token = ?'
    cursor = conn.cursor()
    cursor.execute(sql, (instance_status, instance_token))

    # Updating the task progression of the instance 
    sql = 'UPDATE instances SET task_progression = "0" WHERE token = ?'
    cursor = conn.cursor()
    cursor.execute(sql, (instance_token,))

    conn.commit()
    conn.close()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}

# Called during the task progression
@api.route('/api/status', methods=['POST'])
def status():
    conn = get_db_connection()
    content = request.json

    instance_token = str(request.headers.get('Token'))

    progress = round((int(content['progress'][0]) / int(content['progress'][1])) * 100, 1)

    # Updating task_progression in instances
    sql = 'UPDATE instances SET task_progression = ? WHERE token = ?'
    cursor = conn.cursor()
    cursor.execute(sql, (progress, instance_token))

    conn.commit()
    conn.close()

    print(content)

    return json.dumps({'success': True, 'progress': str(progress)}), 200, {'ContentType': 'application/json'}

# Called at the end of the task
@api.route('/api/result/<state>', methods=['POST'])
def result(state):
    conn = get_db_connection()
    content = request.json

    instance_token = str(request.headers.get('Token'))

    # Getting the time spent for the task
    cursor = conn.execute('SELECT start_time FROM tasks WHERE id = (SELECT task_id FROM instances WHERE token = ?)', (instance_token,))
    start_time = cursor.fetchone()

    time_spent = format_timespan(int(datetime.now(tz=timezone.utc).timestamp()) - int(start_time['start_time']))

    if state == "OK":
        result = str(content['Result'].split(":")[1])

        # Updating the task progression of the instance 
        sql = 'UPDATE instances SET task_progression = "100" WHERE token = ?'
        cursor = conn.cursor()
        cursor.execute(sql, (instance_token,))

        # Updating the task row with the plaintext result
        sql = 'UPDATE tasks SET plaintext = ? WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
        cursor = conn.cursor()
        cursor.execute(sql, (result, instance_token))
        
        # Updating the result of the task 
        sql = 'UPDATE tasks SET result = "OK" WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
        cursor = conn.cursor()
        cursor.execute(sql, (instance_token,))

        # Updating the final status of the task 
        sql = 'UPDATE tasks SET status = "Completed" WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
        cursor = conn.cursor()
        cursor.execute(sql, (instance_token,))
        
        # Updating the time spent for the task completion
        sql = 'UPDATE tasks SET time_spent = ? WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
        cursor = conn.cursor()
        cursor.execute(sql, (time_spent, instance_token))

        # Destroy all the running instances
        cursor = conn.execute('SELECT droplet_id FROM instances WHERE task_id = (SELECT task_id FROM instances WHERE token = ?)', (instance_token,))
        droplet_ids = cursor.fetchall()

        for id in droplet_ids:
            destroy(int(id['droplet_id']))

            # Remove a row
            sql = 'DELETE FROM instances WHERE droplet_id = ?'
            cur = conn.cursor()
            cur.execute(sql, (id['droplet_id'],))

            # Remove 1 to the id to get instance continuity
            sql = 'UPDATE sqlite_sequence SET seq = seq - 1 WHERE name="instances"'
            cur = conn.cursor()
            cur.execute(sql)

    if state == "FAILED":
        # Get the number of running instance
        cursor = conn.execute('SELECT count(id) as count FROM instances WHERE task_id = (SELECT task_id FROM instances WHERE token = ?)', (instance_token,))
        instance_count = cursor.fetchone()

        # Only if it's the last instance to run
        if int(instance_count['count']) == 1:

            # Updating the result of the task 
            sql = 'UPDATE tasks SET result = "FAILED" WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
            cursor = conn.cursor()
            cursor.execute(sql, (instance_token,))

            # Updating the final status of the task 
            sql = 'UPDATE tasks SET status = "Completed" WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
            cursor = conn.cursor()
            cursor.execute(sql, (instance_token,))

            # Updating the time spent for the task completion
            sql = 'UPDATE tasks SET time_spent = ? WHERE id = (SELECT task_id FROM instances WHERE token = ?)'
            cursor = conn.cursor()
            cursor.execute(sql, (time_spent, instance_token))

        # Get the number of running instance
        cursor = conn.execute('SELECT droplet_id FROM instances WHERE token = ?', (instance_token,))
        data = cursor.fetchone()

        destroy(int(data['droplet_id']))

        # Remove a row
        sql = 'DELETE FROM instances WHERE droplet_id = ?'
        cur = conn.cursor()
        cur.execute(sql, (data['droplet_id'],))

        # Remove 1 to the id to get instance continuity
        sql = 'UPDATE sqlite_sequence SET seq = seq - 1 WHERE name="instances"'
        cur = conn.cursor()
        cur.execute(sql)

    conn.commit()
    conn.close()
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


############################## FRONT-END CALLS ##############################

@api.route('/api/create', methods=['POST'])
@login_required
def create():
    conn = get_db_connection()

    # Checking if task name is existing
    cursor = conn.execute('SELECT id FROM tasks WHERE task_name = ?', [request.form.get('task-name')])
    existing = cursor.fetchone()

    if existing is None:
         # Getting data from the form
        selectedInstanceNum = request.form.get('number')

        cursor = conn.execute('SELECT hashcat_mode,type_name FROM hash_type WHERE type_name = ?', [request.form.get('hash-type')])
        hashcat_mode = cursor.fetchone()

        dic = {
            "task_name": request.form.get('task-name'),
            "task_status": "waiting",
            "type_name": hashcat_mode['type_name'],
            "hash": request.form.get('hash'),
            "start_time": int(datetime.now(tz=timezone.utc).timestamp())
        }

        # Creating task
        sql = ''' INSERT INTO tasks(task_name, hash_type, hash, status, start_time)
                VALUES(?,?,?,?,?) '''
        cursor = conn.cursor()
        cursor.execute(
            sql, (dic['task_name'], dic['type_name'], dic['hash'], dic['task_status'], dic['start_time']))

        # Creating dictonary containing all the parameters
        for instance in range(int(selectedInstanceNum)):
            
            dic.update({
                "instance_name": request.form.get('task-name').upper() + "-" + str(instance + 1),
                "instance_size": "s-1vcpu-1gb",
                "instance_status": "Creating",
                "instance_type": "worker",
                "task_progression": 0,
                "user_id": current_user.get_id(),
                "wordlist": request.form.get('select' + str(instance + 1)),
                "instance_power": "on",
                "hashcat_mode": int(hashcat_mode['hashcat_mode']),
                "token": token_hex(16)
            })

            # Getting wordlist URL
            cursor = conn.execute('SELECT url FROM wordlists WHERE name = ?', [request.form.get('select' + str(instance + 1))])
            wordlist_link = cursor.fetchone()

            # Adding wordlist_url to dictionnary
            dic.update({
                "wordlist_url": wordlist_link['url']
            })

            # Creating the droplet
            droplet = hashcat(name=dic['instance_name'], region="lon1", image="debian-11-x64", size=dic['instance_size'], api_token=dic['token'], hash=dic['hash'], wordlist_url=dic['wordlist_url'], wordlist_name=dic['wordlist'])
            droplet.create()

            # Wait 1s to permit the load() action to perform correctly
            sleep(1)

            # Getting the droplet ID and private IP address to permit futur destroy() and actions
            droplet_info = droplet.load()
            droplet_id = droplet_info.id
            droplet_ip = droplet_info.private_ip_address

            # Getting the max id from the table task to permit link with table instances
            cursor = conn.execute('SELECT max(id) as id FROM tasks')
            task_id = cursor.fetchone()

            # Adding instances details to DB
            sql = ''' INSERT INTO instances(internal_ip,droplet_id,instance_name,instance_size,instance_status,instance_type,task_progression,user_id,task_wordlist,instance_power,task_id,token)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?) '''
            cursor = conn.cursor()
            cursor.execute(sql, (droplet_ip,droplet_id,dic['instance_name'], dic['instance_size'], dic['instance_status'], dic['instance_type'],
                        dic['task_progression'], dic['user_id'], dic['wordlist'], dic['instance_power'], int(task_id['id']), dic['token']))

            # Commit changes to the DB
            conn.commit()
        
        conn.close()
        return redirect(url_for('main.dashboard'))

    else:
        flash('Task name already exists')
        return redirect(url_for('main.attack'))
       
# Destroy instance using the front-end only
@api.route('/api/destroy/<name>', methods=['POST'])
@login_required
def destroy_droplet(name):
    
    # Get the droplet ID of the selected instance
    conn = get_db_connection()
    cursor = conn.execute('SELECT droplet_id,task_id FROM instances WHERE instance_name = ?', [name])
    data = cursor.fetchone()

    destroy(int(data['droplet_id']))

    # Remove a row
    sql = 'DELETE FROM instances WHERE instance_name = ?'
    cur = conn.cursor()
    cur.execute(sql, [name])

    # Remove 1 to the id to get instance continuity
    sql = 'UPDATE sqlite_sequence SET seq = seq - 1 WHERE name="instances"'
    cur = conn.cursor()
    cur.execute(sql)

    # If all the instances of a task are destroyed, delete the task
    cursor = conn.execute('SELECT count(id) as count FROM instances WHERE task_id = ?', [data['task_id']])
    instance_count = cursor.fetchone()

    if int(instance_count['count']) == 0:

        # Remove the task
        sql = 'DELETE FROM tasks WHERE id = ?'
        cur = conn.cursor()
        cur.execute(sql, [int(data['task_id'])])

        # Remove 1 to the id to get task continuity
        sql = 'UPDATE sqlite_sequence SET seq = seq - 1 WHERE name="tasks"'
        cur = conn.cursor()
        cur.execute(sql)    

    conn.commit()
    conn.close()
    return redirect(url_for('main.dashboard'))
