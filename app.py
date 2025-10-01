from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session timeout
socketio = SocketIO(app)

# Database connection settings
db_config = {
    'host': 'localhost',
    'user': 'rishab',
    'password': 'SouL123@',
    'database': 'chatapp'
}

# Global connection and cursor
conn = None
cursor = None

def get_db_connection():
    global conn, cursor
    try:
        if conn is None or not conn.open:
            conn = pymysql.connect(**db_config)
            cursor = conn.cursor()
            logger.info("Established new database connection")
        return conn, cursor
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

# Online Users Tracking
online_users = set()

# ---------- Routes ----------

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn, cursor = get_db_connection()
            cursor.execute("SELECT password FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[0], password):
                session['username'] = username
                logger.info(f"User {username} logged in")
                return redirect('/chat')
            else:
                logger.warning(f"Failed login attempt for {username}")
                return "Invalid username or password!"
        except Exception as e:
            logger.error(f"Database error in login: {e}")
            return "Database error, please try again later", 500
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            conn, cursor = get_db_connection()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                logger.warning(f"Registration failed: Username {username} already exists")
                return "Username already exists!"
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            logger.info(f"User {username} registered")
            return redirect('/login')
        except Exception as e:
            logger.error(f"Database error in register: {e}")
            return "Database error, please try again later", 500
    return render_template('register.html')

@app.route('/logout')
def logout():
    username = session.pop('username', None)
    if username and username in online_users:
        online_users.remove(username)
        logger.info(f"User {username} logged out, removed from online_users")
        socketio.emit('update_users', list(online_users), broadcast=True)
    return redirect('/login')

@app.route('/chat')
def chat():
    if 'username' not in session:
        logger.warning("Unauthorized access to /chat")
        return redirect('/login')
    return render_template('chat.html', username=session['username'])

@app.route('/get_users')
def get_users():
    current = session.get('username')
    if not current:
        logger.warning("No user in session for /get_users")
        return jsonify({'online': [], 'offline': []})
    try:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT username FROM users WHERE username != %s", (current,))
        all_users = [row[0] for row in cursor.fetchall()]
        online = list(online_users)
        offline = list(set(all_users) - set(online))
        logger.debug(f"Online users: {online}, Offline users: {offline}")
        return jsonify({'online': online, 'offline': offline})
    except Exception as e:
        logger.error(f"Database error in get_users: {e}")
        return jsonify({'online': list(online_users), 'offline': []})

@app.route('/history/<receiver>')
def chat_history(receiver):
    sender = session.get('username')
    if not sender:
        logger.warning("No user in session for /history")
        return jsonify([])
    try:
        conn, cursor = get_db_connection()
        cursor.execute(
            "SELECT sender, message, timestamp, status, id FROM messages WHERE "
            "((sender=%s AND receiver=%s AND deleted_for_sender=FALSE) OR "
            "(sender=%s AND receiver=%s AND deleted_for_receiver=FALSE)) "
            "ORDER BY timestamp ASC",
            (sender, receiver, receiver, sender)
        )
        chats = cursor.fetchall()
        logger.debug(f"Chat history for {sender} and {receiver}: {len(chats)} messages")
        return jsonify([{'sender': row[0], 'message': row[1], 'timestamp': str(row[2]), 'status': row[3], 'id': row[4]} for row in chats])
    except Exception as e:
        logger.error(f"Database error in chat_history: {e}")
        return jsonify([])

@app.route('/delete_message', methods=['POST'])
def delete_message():
    data = request.json
    msg_id = data.get('id')
    user = session.get('username')
    if not user or not msg_id:
        logger.warning("Invalid request for /delete_message")
        return 'Invalid request', 400
    try:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT sender, receiver FROM messages WHERE id=%s", (msg_id,))
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Message {msg_id} not found for deletion")
            return 'Message not found', 404
        sender, receiver = row
        if user == sender:
            cursor.execute("UPDATE messages SET deleted_for_sender=TRUE WHERE id=%s", (msg_id,))
        elif user == receiver:
            cursor.execute("UPDATE messages SET deleted_for_receiver=TRUE WHERE id=%s", (msg_id,))
        else:
            logger.warning(f"User {user} not authorized to delete message {msg_id}")
            return 'Unauthorized', 403
        conn.commit()
        logger.debug(f"Message {msg_id} marked as deleted for {user}")
        # Notify the user who deleted the message
        socketio.emit('message_deleted', {'id': msg_id}, room=user)
        return '', 204
    except Exception as e:
        logger.error(f"Database error in delete_message: {e}")
        return 'Database error', 500

@app.route('/mark_seen/<sender>', methods=['POST'])
def mark_seen(sender):
    receiver = session.get('username')
    if not receiver:
        logger.warning("No user in session for /mark_seen")
        return '', 403
    try:
        conn, cursor = get_db_connection()
        cursor.execute("""
            UPDATE messages SET status='seen'
            WHERE sender=%s AND receiver=%s AND status != 'seen' AND deleted_for_receiver=FALSE
        """, (sender, receiver))
        conn.commit()
        cursor.execute(
            "SELECT id, sender, receiver, message, timestamp, status FROM messages "
            "WHERE sender=%s AND receiver=%s AND status='seen' AND deleted_for_receiver=FALSE",
            (sender, receiver)
        )
        seen_messages = cursor.fetchall()
        logger.debug(f"Marked {len(seen_messages)} messages as seen from {sender} to {receiver}")
        for msg in seen_messages:
            socketio.emit('message_status_updated', {
                'id': msg[0], 'from': msg[1], 'msg': msg[3], 'timestamp': str(msg[4]), 'status': msg[5]
            }, room=sender)
        return '', 204
    except Exception as e:
        logger.error(f"Database error in mark_seen: {e}")
        return '', 500

# ---------- SocketIO Events ----------

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        online_users.add(username)
        join_room(username)
        logger.info(f"User {username} connected, online_users: {online_users}")
        try:
            conn, cursor = get_db_connection()
            cursor.execute(
                "SELECT id, sender, receiver, message, timestamp, status FROM messages "
                "WHERE receiver=%s AND status='sent' AND deleted_for_receiver=FALSE",
                (username,)
            )
            pending_messages = cursor.fetchall()
            logger.debug(f"Found {len(pending_messages)} pending messages for {username}")
            for msg in pending_messages:
                message_id, sender, receiver, message, timestamp, status = msg
                cursor.execute("UPDATE messages SET status='delivered' WHERE id=%s", (message_id,))
                conn.commit()
                socketio.emit('private_message', {
                    'from': sender, 'msg': message, 'id': message_id, 
                    'status': 'delivered', 'timestamp': str(timestamp)
                }, room=receiver)
                socketio.emit('message_status_updated', {
                    'id': message_id, 'from': sender, 'msg': message, 
                    'timestamp': str(timestamp), 'status': 'delivered'
                }, room=sender)
            socketio.emit('update_users', list(online_users), broadcast=True)
        except Exception as e:
            logger.error(f"Database error in handle_connect: {e}")

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username and username in online_users:
        online_users.remove(username)
        logger.info(f"User {username} disconnected, online_users: {online_users}")
        socketio.emit('update_users', list(online_users), broadcast=True)

@socketio.on('join')
def join():
    username = session.get('username')
    if username:
        join_room(username)
        logger.debug(f"User {username} joined room")
        socketio.emit('update_users', list(online_users), broadcast=True)

@socketio.on('private_message')
def handle_private_message(data):
    sender = session.get('username')
    if not sender:
        logger.warning("No user in session for private_message")
        return
    receiver = data['to']
    msg = data['msg']
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn, cursor = get_db_connection()
        cursor.execute("INSERT INTO messages (sender, receiver, message, status, timestamp, deleted_for_sender, deleted_for_receiver) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                       (sender, receiver, msg, 'sent', timestamp, False, False))
        conn.commit()
        message_id = cursor.lastrowid
        logger.debug(f"Message {message_id} sent from {sender} to {receiver}, status: sent")
        status = 'sent'
        if receiver in online_users:
            status = 'delivered'
            emit('private_message', {
                'from': sender, 'msg': msg, 'id': message_id, 
                'status': status, 'timestamp': timestamp
            }, room=receiver)
            cursor.execute("UPDATE messages SET status='delivered' WHERE id=%s", (message_id,))
            conn.commit()
            logger.debug(f"Message {message_id} updated to delivered for {receiver}")
        emit('private_message', {
            'from': sender, 'msg': msg, 'id': message_id, 
            'status': status, 'timestamp': timestamp
        }, room=sender)
    except Exception as e:
        logger.error(f"Database error in private_message: {e}")

@socketio.on("typing")
def handle_typing(data):
    sender = session.get('username')
    emit("show_typing", {"from": sender}, room=data['to'])

@socketio.on("stop_typing")
def handle_stop_typing(data):
    emit("hide_typing", {}, room=data['to'])

@socketio.on("group_message")
def handle_group_message(data):
    sender = session.get('username')
    message = data['msg']
    try:
        conn, cursor = get_db_connection()
        cursor.execute("INSERT INTO group_messages (sender, message) VALUES (%s, %s)", (sender, message))
        conn.commit()
        logger.debug(f"Group message from {sender}: {message}")
        emit("group_message", {"from": sender, "msg": message}, broadcast=True)
    except Exception as e:
        logger.error(f"Database error in group_message: {e}")

@app.route("/group_history")
def group_history():
    try:
        conn, cursor = get_db_connection()
        cursor.execute("SELECT sender, message, timestamp FROM group_messages ORDER BY timestamp ASC")
        chats = cursor.fetchall()
        return jsonify([{'sender': row[0], 'message': row[1], 'timestamp': str(row[2])} for row in chats])
    except Exception as e:
        logger.error(f"Database error in group_history: {e}")
        return jsonify([])

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True)
    finally:
        if conn and conn.open:
            conn.close()
            logger.info("Database connection closed")        