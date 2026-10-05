# app.py created by DOV1NTC powered by XWARED TEAM(C)
import random, string, os, json, time, gevent, threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
from flask_socketio import SocketIO, join_room, emit
from utils.load_env import *
from utils.database_init import init_db, get_db
from utils.simple import load_quizzes_data, save_log, get_admin_stats
from utils.log import log

BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'quizes')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "data", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
load(BASE_DIR)
MAX_LOG_ENTRIES = 10000
ARCHIVE_THRESHOLD = 1000
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=7200, async_mode='gevent')
app.secret_key = get_secret_key()
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = False
ADMIN_PASSWORD = get_password()
init_db(BASE_DIR)
quizzes_data = load_quizzes_data(BASE_DIR)

@app.before_request
def track_user_activity():
    skip_prefixes = ['/api/', '/static/', '/favicon.ico', '/adm-panel']
    if any(request.path.startswith(p) for p in skip_prefixes):
        return None
    if request.method == 'GET':
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        threading.Thread(target=save_log, args=(ip, request.path, BASE_DIR, MAX_LOG_ENTRIES, ARCHIVE_THRESHOLD), daemon=True).start()

@app.route('/create')
def create(): return render_template("create.html")

@app.route('/')
def index(): return render_template("index.html", quiz_data=quizzes_data)

@app.route('/home')
def home_page(): return render_template("home.html")

@app.route('/connect')
def connect_page():
    game_code = request.args.get('id')
    if not game_code: return redirect(url_for('index'))
    try: game_code = int(game_code)
    except (TypeError, ValueError): return render_template('connect.html', room_code=None, room_exists=False)
    game = get_game_by_code(game_code)
    if not game: return render_template('connect.html', room_code=game_code, room_exists=False)
    return render_template('connect.html', room_code=game_code, room_exists=True)

@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

@app.route('/display')
def display_page():
    if 'user_id' not in session: return redirect(url_for('home_page'))
    new_room_quiz_id = request.args.get('new_room')
    active_session_code = request.args.get('active_session')
    if active_session_code:
        game = get_game_by_code(active_session_code)
        if not game or str(game['owner_id']) != str(session.get('user_id')):
            log(f"[SECURITY] Отказано в доступе к {active_session_code}", "warning")
            session.pop('hosted_room_code', None)
            return redirect(url_for('home_page'))
        log(f"[RECOVER] Ведущий восстановлен в комнате {active_session_code}")
        state = load_room_state(game)
        quiz_id = state.get('quiz_id')
        quiz_name = quizzes_data.get(str(quiz_id), {}).get('Name', '')
        return render_template("display.html", room_code=int(active_session_code), quiz_id=str(quiz_id) if quiz_id is not None else None, quiz_name=quiz_name, auto_create=False)
    if new_room_quiz_id and str(new_room_quiz_id) in quizzes_data:
        return render_template("display.html", quiz_id=new_room_quiz_id, quiz_name=quizzes_data[str(new_room_quiz_id)]['Name'], auto_create=True)
    return redirect(url_for('home_page'))

@app.route('/active_session')
def active_session_page():
    if 'user_id' not in session: return redirect(url_for('home_page'))
    raw_code = request.args.get('id')
    if not raw_code: return redirect(url_for('home_page'))
    try: code = int(raw_code)
    except (TypeError, ValueError): return redirect(url_for('home_page'))
    game = get_game_by_code(code)
    if not game or str(game['owner_id']) != str(session.get('user_id')):
        log(f"[SECURITY] Отказано в доступе к active_session {code}", "warning")
        session.pop('hosted_room_code', None)
        return redirect(url_for('home_page'))
    state = load_room_state(game)
    quiz_id = state.get('quiz_id')
    quiz_name = quizzes_data.get(str(quiz_id), {}).get('Name', '')
    return render_template("display.html", room_code=code, quiz_id=str(quiz_id) if quiz_id is not None else None, quiz_name=quiz_name, auto_create=False)

@app.route('/privacy_policy')
def privacy_policy():
    lang = request.args.get('l', 'ru').lower()
    return render_template('privacy.html', is_russian=(lang == 'ru'))

@app.route('/profile')
def profile_page():
    if 'user_id' not in session: return redirect(url_for('home_page'))
    conn = get_db(BASE_DIR); cursor = conn.cursor()
    cursor.execute("SELECT username, permissions FROM users WHERE id = ?", (session['user_id'],))
    user_data = cursor.fetchone(); conn.close()
    if not user_data: return "Ошибка: Пользователь не найден", 404
    return render_template('profile.html', user_id=session['user_id'], username=user_data['username'], permissions=user_data['permissions'])

@app.route('/quiz')
def info_quiz():
    param = request.args.get('id', "all")
    if param in quizzes_data: return render_template("quiz_info.html", quiz_data=quizzes_data[param])
    return render_template("quiz_info.html", quiz_data=False)

@app.route('/api/update-username', methods=['POST'])
def api_update_username():
    if 'user_id' not in session: return jsonify({"error": "Не авторизован"}), 401
    data = request.get_json() or {}; new_username = str(data.get('username', '')).strip()
    if not new_username or len(new_username) < 3 or len(new_username) > 20: return jsonify({"error": "Имя должно быть от 3 до 20 символов"}), 400
    conn = get_db(BASE_DIR); cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (new_username, session['user_id']))
    if cursor.fetchone(): conn.close(); return jsonify({"error": "Это имя уже занято"}), 409
    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, session['user_id']))
    conn.commit(); conn.close(); session['username'] = new_username
    return jsonify({"status": "ok", "new_username": new_username})

@app.route('/api/update-json-data/<password>', methods=['POST'])
def api_update_json_data(password):
    if str(password) != get_password(): return jsonify({"error": "Invalid password"}), 403
    threading.Thread(target=reload_data, daemon=True).start()
    return jsonify({"status": "Reload started"}), 200

def reload_data():
    global quizzes_data
    try:
        new_data = load_quizzes_data(BASE_DIR)
        quizzes_data = new_data
        log("Data updated successfully", "info")
    except Exception as e:
        log(f"Error updating data: {e}", "error")
        
@app.route('/quiz-images/<int:quiz_id>/<path:filename>')
def serve_quiz_image(quiz_id, filename):
    quiz_folder = os.path.join(BASE_DATA_DIR, str(quiz_id))
    filepath = os.path.join(quiz_folder, filename)
    if not os.path.exists(filepath) or not os.path.abspath(filepath).startswith(os.path.abspath(quiz_folder)): return abort(404)
    return send_from_directory(quiz_folder, filename)

@app.route('/api/quizzes', methods=['GET'])
def get_quizess_data():
    param = request.args.get('param', "all"); result_list = []
    if param == 'popular': return jsonify({"Недоступно"}), 404
    if param == "ids":
        id_start = request.args.get('ids_first'); id_end = request.args.get('ids_end')
        if not id_start or not id_end: return jsonify({"error": "укажите верные ids_first и ids_end"}), 400
        try: start_int = int(id_start); end_int = int(id_end)
        except ValueError: return jsonify({"error": "ID должны быть числами"}), 400
        for q_id, q_data in quizzes_data.items():
            try: quiz_id_int = int(q_id)
            except ValueError: log("", "error"); continue
            if start_int <= quiz_id_int <= end_int:
                path = os.path.join(os.path.dirname(__file__), f"data\\quizes\\{q_id}\\{q_data['PreviewImagePath']}").replace(r'\/', '/').replace('\\', '/')
                if os.path.exists(path): result_list.append([q_id, q_data["Name"], q_data["PreviewImagePath"]])
        return jsonify(result_list)
    return jsonify([])

@app.route('/adm-login', methods=['GET', 'POST'])
def adm_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('adm_panel'))
        else: return render_template('adm_login.html', error='Неверный пароль')
    if session.get('is_admin'): return redirect(url_for('adm_panel'))
    return render_template('adm_login.html', error=None)

@app.route('/api/send-code', methods=['POST'])
def api_send_code():
    request_start = time.time(); log("[SEND_CODE] request started")
    data = request.get_json()
    log(f"[SEND_CODE] json received: {time.time() - request_start:.3f}s")
    if not data: return jsonify({"error": "Пустой запрос"}), 400
    email = str(data.get('email', '')).strip().lower()
    if '@' not in email or '.' not in email.split('@')[-1]: return jsonify({"error": "Некорректный email"}), 400
    code = ''.join(random.choices(string.digits, k=6))
    try:
        conn = get_db(BASE_DIR)
        if conn is None: log("[SEND_CODE] DB connection failed", "error"); return jsonify({"error": "База данных недоступна"}), 500
        conn.execute("INSERT INTO codes (email, code) VALUES (?, ?)", (email, code)); conn.commit(); conn.close()
        log(f"[SEND_CODE] DB done: {time.time() - request_start:.3f}s")
    except Exception as e: log(f"Ошибка записи в БД: {e}", "error"); return jsonify({"error": "Ошибка сервера"}), 500
    try:
        from utils.send_code import send_code; SMTP_MAIL_CODE, EMAIL_SENDER = get_smtp_data()
        log(f"[SEND_CODE] before thread: {time.time() - request_start:.3f}s")
        threading.Thread(target=send_code, args=(EMAIL_SENDER, SMTP_MAIL_CODE, email, int(code)), daemon=True).start()
        log(f"[SEND_CODE] returning response: {time.time() - request_start:.3f}s")
        return jsonify({"status": "ok"})
    except Exception as e: log(f"Внутренняя ошибка: {e}", "error"); return jsonify({"error": "Внутренняя ошибка"}), 500

@app.route('/api/verify-code', methods=['POST'])
def api_verify_code():
    data = request.get_json() or {}; email = str(data.get('email', '')).strip().lower(); input_code = str(data.get('code', '')).strip()
    conn = get_db(BASE_DIR); cursor = conn.cursor()
    cursor.execute("SELECT * FROM codes WHERE email = ? ORDER BY id DESC LIMIT 1", (email,)); record = cursor.fetchone()
    if not record: conn.close(); return jsonify({"error": "Код не запрашивался"}), 400
    db_code = record['code']; created_at_str = record['created_at']
    try: created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
    except ValueError: created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
    if datetime.utcnow() > created_at + timedelta(minutes=10):
        conn.execute("DELETE FROM codes WHERE id = ?", (record['id'],)); conn.commit(); conn.close()
        return jsonify({"error": "Срок действия кода истек"}), 400
    if db_code == input_code:
        cursor.execute("SELECT id, username FROM users WHERE mail = ?", (email,)); existing_user = cursor.fetchone()
        if existing_user: user_id = existing_user['id']; username = existing_user['username']
        else:
            cursor.execute("SELECT MAX(id) as max_id FROM users"); row = cursor.fetchone(); next_id = (row['max_id'] or 0) + 1
            username = f"user#{next_id}"
            cursor.execute("INSERT INTO users (id, username, mail, permissions) VALUES (?, ?, ?, ?)", (next_id, username, email, 'user')); user_id = next_id
        cursor.execute("DELETE FROM codes WHERE id = ?", (record['id'],)); conn.commit(); conn.close()
        session.permanent = True; session['user_id'] = user_id; session['username'] = username; session['mail'] = email
        return jsonify({"status": "ok", "message": "Успешный вход", "user_id": user_id, "username": username})
    conn.close(); return jsonify({"error": "Неверный код"}), 401

@app.route('/api/check-session')
def check_session():
    if 'user_id' in session: return jsonify({"logged_in": True, "user_id": session['user_id'], "username": session.get('username', '')})
    return jsonify({"logged_in": False})

@app.route('/adm-panel', methods=['GET'])
def adm_panel():
    if not session.get('is_admin'): return redirect(url_for('adm_login'))
        
    view_mode = request.args.get('view', 'users')
    conn = get_db(BASE_DIR); cursor = conn.cursor()
    data, headers, keys = [], [], []
    try:
        if view_mode == 'users':
            cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 50")
            headers = ['ID', 'Username', 'Email', 'Permissions']
            keys = ['id', 'username', 'mail', 'permissions']
        elif view_mode == 'codes':
            cursor.execute("SELECT * FROM codes ORDER BY created_at DESC LIMIT 50")
            headers = ['ID', 'Email', 'Code', 'Created At']
            keys = ['id', 'email', 'code', 'created_at']
        elif view_mode == 'active_rooms':
            cursor.execute("SELECT * FROM active_rooms ORDER BY id DESC LIMIT 50")
            headers = ['ID', 'Invite Code', 'Owner ID', 'Stage', 'Question ID']
            keys = ['id', 'invite_code', 'owner_id', 'stage', 'question_id']
        data = [dict(row) for row in cursor.fetchall()]
    except Exception as e: log(f"Admin panel DB error: {e}", "error")
    finally: conn.close()
    view_mode = request.args.get('view', 'users')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    log_limit = int(request.args.get('log_limit', 20))
    stats = get_admin_stats(BASE_DIR, date_from, date_to, log_limit)
    return render_template('adm_data.html', data=data, headers=headers, keys=keys, 
                          view_mode=view_mode, stats=stats,
                          current_log_limit=log_limit, filter_date_from=date_from,
                          filter_date_to=date_to)

@app.route('/api/delete-codes-bulk', methods=['POST'])
def delete_rooms_bulk():
    if not session.get('is_admin'): return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not ids: return jsonify({"error": "No IDs provided"}), 400
        
    conn = get_db(BASE_DIR)
    try:
        placeholders = ','.join('?' for _ in ids)
        conn.execute(f"DELETE FROM codes WHERE id IN ({placeholders})", ids)
        conn.commit()
        log(f"Bulk deleted {len(ids)} rooms", "info")
        return jsonify({"status": "ok", "deleted": len(ids)})
    except Exception as e:
        log(f"Bulk delete error: {e}", "error")
        return jsonify({"error": "DB Error"}), 500
    finally: conn.close()

@app.route('/api/delete-codes', methods=['POST'])
def api_delete_codes():
    if not session.get('is_admin'): return jsonify({"error": "Доступ запрещен"}), 403
    data = request.get_json() or {}; mode = data.get('mode'); conn = get_db(BASE_DIR); cursor = conn.cursor()
    try:
        if mode == 'all': cursor.execute("DELETE FROM codes"); deleted_count = cursor.rowcount
        elif mode == 'selected':
            ids = data.get('ids', [])
            if not ids: return jsonify({"error": "Не выбраны записи"}), 400
            placeholders = ','.join('?' for _ in ids); cursor.execute(f"DELETE FROM codes WHERE id IN ({placeholders})", ids); deleted_count = cursor.rowcount
        else: return jsonify({"error": "Неверный режим удаления"}), 400
        conn.commit(); return jsonify({"status": "ok", "deleted": deleted_count})
    except Exception as e: conn.rollback(); log(f"Ошибка удаления: {e}", "error"); return jsonify({"error": "Ошибка сервера при удалении"}), 500
    finally: conn.close()

@app.route('/api/update-user-data', methods=['POST'])
def api_update_user_data():
    ...

@app.route('/api/update-user-role', methods=['POST'])
def update_user_role():
    if not session.get('is_admin'): return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    user_id = data.get('user_id')
    new_role = data.get('role')
    if new_role not in ['user', 'admin']: return jsonify({"error": "Invalid role"}), 400
    conn = get_db(BASE_DIR)
    try:
        conn.execute("UPDATE users SET permissions = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        log(f"Role update error: {e}", "error")
        return jsonify({"error": "DB Error"}), 500
    finally: conn.close()

@app.route('/api/delete-room', methods=['POST'])
def delete_room_api():
    if not session.get('is_admin'): return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    code = data.get('code')
    if not code: return jsonify({"error": "No code provided"}), 400
    conn = get_db(BASE_DIR)
    try:
        conn.execute("DELETE FROM active_rooms WHERE invite_code = ?", (int(code),))
        conn.commit()
        log(f"Room {code} deleted by admin", "info")
        return jsonify({"status": "ok"})
    except Exception as e:
        log(f"Room deletion error: {e}", "error")
        return jsonify({"error": "DB Error"}), 500
    finally: conn.close()

@app.route('/adm-logout')
def adm_logout(): 
    session.pop('is_admin', None)
    return redirect(url_for('adm_login'))

def get_game_by_code(code):
    conn = get_db(BASE_DIR); cursor = conn.cursor(); cursor.execute("SELECT * FROM active_rooms WHERE invite_code = ?", (code,)); row = cursor.fetchone(); conn.close()
    return dict(row) if row else None

def load_room_state(game):
    try: state = json.loads(game.get('data') or '{}'); 
    except (TypeError, ValueError): state = {}
    return state if isinstance(state, dict) else {}

def save_room_state(code, state, stage=None, question_id=None):
    conn = get_db(BASE_DIR); fields = ["data = ?"]; values = [json.dumps(state, ensure_ascii=False)]
    if stage is not None: fields.append("stage = ?"); values.append(stage)
    if question_id is not None: fields.append("question_id = ?"); values.append(question_id)
    values.append(code); conn.execute(f"UPDATE active_rooms SET {', '.join(fields)} WHERE invite_code = ?", values); conn.commit(); conn.close()

def room_players(game):
    try: data = json.loads(game.get('session_data') or '{}')
    except (TypeError, ValueError): data = {}
    return data if isinstance(data, dict) else {}

def save_room_players(code, players):
    conn = get_db(BASE_DIR)
    conn.execute("UPDATE active_rooms SET participants_session = ?, session_data = ? WHERE invite_code = ?", (json.dumps(list(players.keys()), ensure_ascii=False), json.dumps(players, ensure_ascii=False), code))
    conn.commit(); conn.close()

def get_stage_list(quiz):
    stages = []
    if not isinstance(quiz, dict): return stages
    for key, value in quiz.items():
        if str(key).isdigit() and isinstance(value, dict) and 'Name_Stage' in value: stages.append((int(key), value))
    return sorted(stages, key=lambda item: item[0])

def get_question_list(stage):
    questions = []
    if not isinstance(stage, dict): return questions
    for key, value in stage.items():
        if str(key).isdigit() and isinstance(value, dict) and 'question' in value: questions.append((int(key), value))
    return sorted(questions, key=lambda item: item[0])

def get_current_content(state):
    quiz = quizzes_data.get(str(state.get('quiz_id')))
    if not quiz: return None, None, None
    stages = get_stage_list(quiz); stage_pos = int(state.get('stage_index', 0)); question_pos = int(state.get('question_index', 0))
    if stage_pos >= len(stages): return quiz, None, None
    stage = stages[stage_pos][1]; questions = get_question_list(stage)
    if question_pos >= len(questions): return quiz, stage, None
    return quiz, stage, questions[question_pos][1]

def public_question(question): return {'question': question.get('question', ''), 'question_options': question.get('question_options', [])}
def public_display_question(question): return {'question': question.get('question', '')}

def player_snapshot(players):
    result = [{'player_id': pid, 'nickname': p.get('nickname', 'Аноним'), 'score': int(p.get('score', 0)), 'answered': bool(p.get('answered', False)), 'connected': bool(p.get('connected', False)), 'joined_at': p.get('joined_at', 0)} for pid, p in players.items()]
    result.sort(key=lambda p: (p['score'] * -1, p['joined_at'])); return result

def get_owner_room(code):
    game = get_game_by_code(code)
    if not game: return None
    user_id = session.get('user_id')
    if not user_id or str(game['owner_id']) != str(user_id): return None
    return game

def emit_display_state(code, event, payload): socketio.emit(event, payload, room=f"display_{code}")

def update_player_state(code, player_id, updates):
    game = get_game_by_code(code)
    if not game: return None
    players = room_players(game)
    if player_id not in players: return None
    players[player_id].update(updates); save_room_players(code, players); return players[player_id]

def next_flow_token(state): token = int(state.get('flow_token', 0)) + 1; state['flow_token'] = token; return token

def worker_is_valid(code, expected_state, token):
    game = get_game_by_code(code)
    if not game: return None, None
    state = load_room_state(game)
    if state.get('state') != expected_state: return None, None
    if token is not None and int(state.get('flow_token', 0)) != int(token): return None, None
    return game, state

def build_display_state(game):
    state = load_room_state(game); quiz, stage, question = get_current_content(state); players = room_players(game)
    payload = {'room_code': int(game['invite_code']), 'state': state.get('state', 'WAITING'), 'quiz_name': quiz.get('Name', '') if quiz else '', 'players': player_snapshot(players), 'paused': state.get('state') == 'PAUSED', 'paused_from_state': state.get('paused_from_state')}
    if stage: payload['stage'] = {'name': stage.get('Name_Stage', ''), 'modify': stage.get('modify', []), 'time_to_answer': int(stage.get('time_to_answer', 30))}
    payload['quiz_id'] = str(state.get('quiz_id')) if state.get('quiz_id') is not None else None
    payload['stage_index'] = int(state.get('stage_index', 0)); payload['question_index'] = int(state.get('question_index', 0))
    if state.get('question_ends_at') is not None: payload['question_ends_at'] = float(state.get('question_ends_at'))
    if state.get('question_remaining') is not None: payload['question_remaining'] = float(state.get('question_remaining'))
    if stage: payload['duration'] = int(stage.get('time_to_answer', 30))
    if question: payload['question'] = public_display_question(question); payload['explanation'] = str(question.get('explanation', '') or '').strip()
    return payload

def build_player_state(game, player_id):
    state = load_room_state(game); players = room_players(game); player = players.get(player_id)
    if not player: return {'state': 'NOT_JOINED'}
    quiz, stage, question = get_current_content(state); current_state = state.get('state', 'WAITING')
    payload = {'state': current_state, 'room_code': int(game['invite_code']), 'nickname': player.get('nickname', 'Аноним'), 'score': int(player.get('score', 0)), 'quiz_id': str(state.get('quiz_id')) if state.get('quiz_id') is not None else None, 'stage_index': int(state.get('stage_index', 0)), 'question_index': int(state.get('question_index', 0))}
    if stage: payload['stage'] = {'name': stage.get('Name_Stage', ''), 'modify': stage.get('modify', []), 'time_to_answer': int(stage.get('time_to_answer', 30))}
    if current_state == 'QUESTION' and question:
        payload['question'] = public_question(question); payload['ends_at'] = float(state.get('question_ends_at', 0)); payload['duration'] = int(stage.get('time_to_answer', 30)) if stage else 30; payload['already_answered'] = bool(player.get('answered', False))
        if player.get('answered', False): payload['state'] = 'WAITING'
    elif current_state == 'QUESTION_RESULT':
        payload['state'] = 'WAITING'
        if player.get('last_result') is not None: payload['last_result'] = player.get('last_result')
    elif current_state == 'PAUSED':
        payload['state'] = 'PAUSED'; payload['paused_from_state'] = state.get('paused_from_state')
        if state.get('paused_from_state') == 'QUESTION':
            payload['question'] = public_question(question) if question else None; payload['remaining'] = float(state.get('question_remaining', 0)); payload['already_answered'] = bool(player.get('answered', False))
    elif current_state == 'FINAL': payload['state'] = 'FINAL'; payload['score'] = int(player.get('score', 0))
    return payload

def reset_question_players(players):
    for player in players.values(): player['answered'] = False; player['current_answer'] = None; player['answered_at'] = None; player['last_result'] = None

def schedule_next_stage_or_finish(code):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') == 'PAUSED': return
    quiz, stage, question = get_current_content(state)
    if not quiz: return
    stages = get_stage_list(quiz); stage_pos = int(state.get('stage_index', 0)); next_stage_pos = stage_pos + 1
    if next_stage_pos >= len(stages): finish_game_round(code); return
    state.update({'state': 'STAGE_PREVIEW', 'stage_index': next_stage_pos, 'question_index': 0, 'question_started_at': None, 'question_ends_at': None, 'question_remaining': None, 'paused_from_state': None})
    token = next_flow_token(state); save_room_state(code, state, stage=next_stage_pos + 1, question_id=1); start_stage_preview(code, token)

def start_stage_preview(code, token=None):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'STAGE_PREVIEW': return
    quiz, stage, question = get_current_content(state)
    if not stage: finish_game_round(code); return
    if token is None: token = next_flow_token(state); save_room_state(code, state, stage=int(state.get('stage_index', 0)) + 1, question_id=1)
    payload = {'stage_index': int(state.get('stage_index', 0)), 'name': stage.get('Name_Stage', ''), 'modify': stage.get('modify', []), 'time_to_answer': int(stage.get('time_to_answer', 30)), 'players': player_snapshot(room_players(game))}
    emit_display_state(code, 'stage_preview', payload); socketio.start_background_task(stage_preview_worker, code, token)

def stage_preview_worker(code, token):
    game, state = worker_is_valid(code, 'STAGE_PREVIEW', token)
    if not game: return
    start_question(code)

def start_question(code):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') == 'PAUSED': return
    quiz, stage, question = get_current_content(state)
    if not stage or not question: schedule_next_stage_or_finish(code); return
    players = room_players(game); reset_question_players(players); now = time.time(); duration = max(1, int(stage.get('time_to_answer', 30))); token = next_flow_token(state)
    state.update({'state': 'QUESTION', 'question_started_at': now, 'question_ends_at': now + duration, 'question_remaining': None, 'paused_from_state': None})
    save_room_state(code, state, stage=int(state.get('stage_index', 0)) + 1, question_id=int(state.get('question_index', 0)) + 1); save_room_players(code, players)
    socketio.emit('question_started', {'question': public_display_question(question), 'stage_index': int(state.get('stage_index', 0)), 'question_index': int(state.get('question_index', 0)), 'started_at': now, 'ends_at': now + duration, 'duration': duration, 'players': player_snapshot(players)}, room=f"display_{code}")
    for player_id, player in players.items():
        sid = player.get('sid')
        if not sid: continue
        socketio.emit('question', {'question': public_question(question), 'quiz_id': str(state.get('quiz_id')), 'stage_name': stage.get('Name_Stage', ''), 'stage_index': int(state.get('stage_index', 0)), 'question_index': int(state.get('question_index', 0)), 'ends_at': now + duration, 'duration': duration}, to=sid)
    socketio.start_background_task(question_timer_worker, code, now + duration, token)

def question_timer_worker(code, ends_at, token):
    while True:
        game = get_game_by_code(code)
        if not game: return
        state = load_room_state(game)
        if state.get('state') != 'QUESTION': return
        if int(state.get('flow_token', 0)) != int(token): return
        remaining = ends_at - time.time()
        if remaining <= 0: break
        gevent.sleep(min(0.25, remaining))
    finish_question(code, token)

def finish_question(code, token=None):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'QUESTION': return
    if token is not None and int(state.get('flow_token', 0)) != int(token): return
    quiz, stage, question = get_current_content(state)
    if not question: return
    players = room_players(game); correct_answer = str(question.get('answer', '')).strip()
    for player_id, player in players.items():
        answer = player.get('current_answer'); is_correct = (answer is not None and str(answer).strip() == correct_answer)
        player['last_result'] = {'correct': is_correct, 'answer': answer, 'correct_answer': correct_answer, 'explanation': question.get('explanation', '')}
        if is_correct: player['score'] = int(player.get('score', 0)) + 1; player['last_result']['points'] = 1
        else: player['last_result']['points'] = 0
    state['state'] = 'QUESTION_RESULT'; state['question_started_at'] = None; state['question_ends_at'] = None; state['question_remaining'] = None
    result_token = next_flow_token(state)
    conn = get_db(BASE_DIR); conn.execute("UPDATE active_rooms SET data = ?, session_data = ? WHERE invite_code = ?", (json.dumps(state, ensure_ascii=False), json.dumps(players, ensure_ascii=False), code)); conn.commit(); conn.close()
    explanation = str(question.get('explanation', '') or '').strip()
    socketio.emit('question_finished', {'players': player_snapshot(players), 'explanation': explanation}, room=f"display_{code}")
    for player_id, player in players.items():
        sid = player.get('sid')
        if not sid: continue
        socketio.emit('answer_result', player.get('last_result') or {}, to=sid)
    question_pos = int(state.get('question_index', 0)); questions = get_question_list(stage)
    if question_pos + 1 >= len(questions): socketio.start_background_task(leaderboard_worker, code, result_token, 0)
    else: socketio.start_background_task(next_question_worker, code, result_token)

def next_question_worker(code, token=None):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'QUESTION_RESULT': return
    if token is not None and int(state.get('flow_token', 0)) != int(token): return
    _, _, question = get_current_content(state); explanation = str(question.get('explanation', '') or '').strip() if question else ''
    gevent.sleep(5 if explanation else 2.5); game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'QUESTION_RESULT': return
    if token is not None and int(state.get('flow_token', 0)) != int(token): return
    quiz, stage, question = get_current_content(state)
    if not stage: return
    question_pos = int(state.get('question_index', 0)); questions = get_question_list(stage)
    if question_pos + 1 >= len(questions): leaderboard_worker(code, token, 0); return
    state['question_index'] = question_pos + 1; state['state'] = 'QUESTION'; state['question_remaining'] = None
    save_room_state(code, state, stage=int(state.get('stage_index', 0)) + 1, question_id=question_pos + 2); start_question(code)

def leaderboard_worker(code, token=None, start_position=0):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') == 'QUESTION_RESULT':
        _, _, question = get_current_content(state); explanation = str(question.get('explanation', '') or '').strip() if question else ''
        gevent.sleep(5 if explanation else 2.5); game = get_game_by_code(code)
        if not game: return
        state = load_room_state(game)
        if state.get('state') != 'QUESTION_RESULT': return
        state['state'] = 'LEADERBOARD'; state['leaderboard_position'] = int(start_position); token = next_flow_token(state); save_room_state(code, state)
    elif state.get('state') != 'LEADERBOARD': return
    if token is not None and int(state.get('flow_token', 0)) != int(token): return
    players = room_players(game); ranking = player_snapshot(players); position = int(state.get('leaderboard_position', start_position or 0))
    while position < len(ranking):
        game = get_game_by_code(code)
        if not game: return
        state = load_room_state(game)
        if state.get('state') != 'LEADERBOARD': return
        if token is not None and int(state.get('flow_token', 0)) != int(token): return
        players = room_players(game); ranking = player_snapshot(players)
        if position >= len(ranking): break
        player = ranking[position]; socketio.emit('leaderboard_player', {'position': position + 1, 'nickname': player['nickname'], 'score': player['score'], 'is_last': position == len(ranking) - 1}, room=f"display_{code}")
        position += 1; state['leaderboard_position'] = position; save_room_state(code, state); gevent.sleep(1.5)
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'LEADERBOARD': return
    quiz = quizzes_data.get(str(state.get('quiz_id'))); stages = get_stage_list(quiz) if quiz else []; stage_pos = int(state.get('stage_index', 0))
    stage = stages[stage_pos][1] if stage_pos < len(stages) else None; questions = get_question_list(stage) if stage else []; question_pos = int(state.get('question_index', 0))
    is_final = (stage_pos >= len(stages) - 1 and question_pos >= len(questions) - 1)
    if is_final: finish_game_round(code); return
    if question_pos + 1 < len(questions):
        state['question_index'] = question_pos + 1; state['state'] = 'QUESTION'; state['leaderboard_position'] = 0
        save_room_state(code, state, stage=stage_pos + 1, question_id=question_pos + 2); start_question(code); return
    schedule_next_stage_or_finish(code)

def finish_game_round(code):
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game); state['state'] = 'FINAL'; state['question_started_at'] = None; state['question_ends_at'] = None; state['question_remaining'] = None; state['paused_from_state'] = None; state['pause_started_at'] = None
    next_flow_token(state); save_room_state(code, state); players = room_players(game); ranking = player_snapshot(players)
    socketio.emit('final_results', {'players': ranking}, room=f"display_{code}")
    for player_id, player in players.items():
        sid = player.get('sid')
        if not sid: continue
        position = next((i + 1 for i, p in enumerate(ranking) if p['player_id'] == player_id), None)
        socketio.emit('final_results', {'position': position, 'score': player.get('score', 0), 'players': ranking}, to=sid)
    socketio.start_background_task(final_cleanup_worker, code)

def final_cleanup_worker(code):
    gevent.sleep(120); game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') == 'FINAL': delete_game(code)

def delete_game(code):
    conn = get_db(BASE_DIR); conn.execute("DELETE FROM active_rooms WHERE invite_code = ?", (code,)); conn.commit(); conn.close()

def pause_game(code):
    game = get_game_by_code(code)
    if not game: return False, "Игра не найдена"
    state = load_room_state(game); current_state = state.get('state', 'WAITING')
    if current_state in ('WAITING', 'PAUSED', 'FINAL'): return False, "Сейчас игру нельзя поставить на паузу"
    state['paused_from_state'] = current_state; state['pause_started_at'] = time.time()
    if current_state == 'QUESTION': ends_at = float(state.get('question_ends_at', 0) or 0); state['question_remaining'] = max(0, ends_at - time.time()); state['question_ends_at'] = None
    elif current_state == 'COUNTDOWN': state['countdown_paused'] = True
    elif current_state == 'LEADERBOARD': state['leaderboard_position'] = int(state.get('leaderboard_position', 0))
    state['state'] = 'PAUSED'; next_flow_token(state); save_room_state(code, state)
    socketio.emit('game_paused', {'message': 'Игра остановлена ждем ведущего', 'from_state': current_state, 'remaining': state.get('question_remaining')}, room=f"display_{code}")
    game = get_game_by_code(code)
    if game:
        players = room_players(game)
        for player in players.values():
            sid = player.get('sid')
            if sid: socketio.emit('game_paused', {'message': 'Игра остановлена ждем ведущего', 'from_state': current_state, 'remaining': state.get('question_remaining')}, to=sid)
    return True, None

def resume_game(code):
    game = get_game_by_code(code)
    if not game: return False, "Игра не найдена"
    state = load_room_state(game)
    if state.get('state') != 'PAUSED': return False, "Игра не находится на паузе"
    previous_state = state.get('paused_from_state')
    if not previous_state: return False, "Не удалось определить состояние игры"
    state['state'] = previous_state; state['pause_started_at'] = None; state['paused_from_state'] = None
    if previous_state == 'QUESTION':
        remaining = float(state.get('question_remaining', 0) or 0)
        if remaining <= 0: state['question_remaining'] = None; save_room_state(code, state); finish_question(code); return True, None
        now = time.time(); state['question_started_at'] = now; state['question_ends_at'] = now + remaining; state['question_remaining'] = None; token = next_flow_token(state); save_room_state(code, state)
        quiz, stage, question = get_current_content(state); duration = int(stage.get('time_to_answer', 30)) if stage else 30
        display_payload = {'state': 'QUESTION', 'quiz_id': str(state.get('quiz_id')) if state.get('quiz_id') is not None else None, 'stage_index': int(state.get('stage_index', 0)), 'question_index': int(state.get('question_index', 0)), 'question': public_display_question(question), 'ends_at': state['question_ends_at'], 'duration': duration, 'remaining': remaining, 'players': player_snapshot(room_players(game))}
        emit_display_state(code, 'game_resumed', display_payload); players = room_players(game)
        for player_id, player in players.items():
            sid = player.get('sid')
            if not sid: continue
            socketio.emit('game_resumed', {'state': 'QUESTION', 'quiz_id': str(state.get('quiz_id')) if state.get('quiz_id') is not None else None, 'stage_index': int(state.get('stage_index', 0)), 'question_index': int(state.get('question_index', 0)), 'question': public_question(question), 'ends_at': state['question_ends_at'], 'duration': duration, 'remaining': remaining, 'already_answered': bool(player.get('answered', False))}, to=sid)
        socketio.start_background_task(question_timer_worker, code, state['question_ends_at'], token); return True, None
    if previous_state == 'COUNTDOWN':
        token = next_flow_token(state); save_room_state(code, state); emit_display_state(code, 'game_resumed', {'state': 'COUNTDOWN'}); socketio.start_background_task(game_start_worker, code, token); return True, None
    if previous_state == 'STAGE_PREVIEW':
        token = next_flow_token(state); save_room_state(code, state); emit_display_state(code, 'game_resumed', {'state': 'STAGE_PREVIEW'}); socketio.start_background_task(stage_preview_worker, code, token); return True, None
    if previous_state == 'QUESTION_RESULT':
        token = next_flow_token(state); save_room_state(code, state); emit_display_state(code, 'game_resumed', {'state': 'QUESTION_RESULT'})
        game = get_game_by_code(code)
        if not game: return False, "Игра не найдена"
        _, _, question = get_current_content(state); explanation = str(question.get('explanation', '') or '').strip() if question else ''
        socketio.start_background_task(next_question_worker, code, token); return True, None
    if previous_state == 'LEADERBOARD':
        position = int(state.get('leaderboard_position', 0)); token = next_flow_token(state); save_room_state(code, state)
        emit_display_state(code, 'game_resumed', {'state': 'LEADERBOARD', 'position': position}); socketio.start_background_task(leaderboard_worker, code, token, position); return True, None
    save_room_state(code, state); emit_display_state(code, 'game_resumed', {'state': previous_state}); return True, None

@socketio.on('connect')
def handle_connect(): return

@socketio.on('create_game')
def handle_create_game(data):
    data = data or {}; quiz_id = data.get('quiz_id'); user_id = session.get('user_id')
    if not user_id: emit('error', {'msg': 'Ошибка сессии: вы не авторизованы'}); return
    if not quiz_id or str(quiz_id) not in quizzes_data: emit('error', {'msg': 'Указанный квиз не найден'}); return
    while True:
        code = random.randint(100000, 999999)
        if not get_game_by_code(code): break
    state = {'quiz_id': str(quiz_id), 'state': 'WAITING', 'stage_index': 0, 'question_index': 0, 'question_started_at': None, 'question_ends_at': None, 'question_remaining': None, 'paused_from_state': None, 'pause_started_at': None, 'leaderboard_position': 0, 'flow_token': 0}
    try:
        conn = get_db(BASE_DIR); conn.execute("INSERT INTO active_rooms (invite_code, owner_id, participants_session, session_data, stage, question_id, data) VALUES (?, ?, '[]', '{}', 1, 1, ?)", (code, str(user_id), json.dumps(state, ensure_ascii=False))); conn.commit(); conn.close()
        session['hosted_room_code'] = code; session.modified = True; join_room(f"display_{code}")
        emit('game_created', {'room_code': code, 'redirect_url': f'/active_session?id={code}'}); log(f"Комната {code} успешно создана в базе!")
    except Exception as e: log(str(e), "error"); emit('error', {'msg': 'Не удалось создать игру'})

@socketio.on('reconnect_display')
def handle_reconnect_display(data):
    data = data or {}; raw_code = data.get('room_code')
    if not raw_code: emit('error', {'msg': 'Код комнаты отсутствует'}); return
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код комнаты'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен или комната не найдена'}); return
    join_room(f"display_{code}"); emit('display_reconnected', build_display_state(game))

@socketio.on('start_game')
def handle_start_game(data):
    data = data or {}; raw_code = data.get('room_code')
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код комнаты'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен'}); return
    state = load_room_state(game)
    if state.get('state') != 'WAITING': emit('error', {'msg': 'Игра уже запущена'}); return
    players = room_players(game)
    if len(players) < 2:
        emit('not_enough_players', {'count': len(players), 'required': 2, 'msg': 'Нужно минимум 2 участника'})
        socketio.emit('not_enough_players', {'count': len(players), 'required': 2, 'msg': 'Нужно минимум 2 участника'}, room=f"display_{code}"); return
    state['state'] = 'COUNTDOWN'; state['countdown_value'] = 3; token = next_flow_token(state); save_room_state(code, state)
    emit_display_state(code, 'countdown', {'value': 3}); socketio.start_background_task(game_start_worker, code, token)

def game_start_worker(code, token=None):
    for value in (3, 2, 1):
        game = get_game_by_code(code)
        if not game: return
        state = load_room_state(game)
        if state.get('state') != 'COUNTDOWN': return
        if token is not None and int(state.get('flow_token', 0)) != int(token): return
        state['countdown_value'] = value; save_room_state(code, state); emit_display_state(code, 'countdown', {'value': value}); socketio.sleep(1)
    game = get_game_by_code(code)
    if not game: return
    state = load_room_state(game)
    if state.get('state') != 'COUNTDOWN': return
    if token is not None and int(state.get('flow_token', 0)) != int(token): return
    state['state'] = 'STAGE_PREVIEW'; state['stage_index'] = 0; state['question_index'] = 0; state['countdown_value'] = None
    preview_token = next_flow_token(state); save_room_state(code, state, stage=1, question_id=1); start_stage_preview(code, preview_token)

@socketio.on('pause_game')
def handle_pause_game(data):
    data = data or {}; raw_code = data.get('room_code')
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код игры'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен'}); return
    success, error = pause_game(code)
    if not success: emit('error', {'msg': error}); return
    emit('pause_changed', {'paused': True})

@socketio.on('resume_game')
def handle_resume_game(data):
    data = data or {}; raw_code = data.get('room_code')
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код игры'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен'}); return
    success, error = resume_game(code)
    if not success: emit('error', {'msg': error}); return
    emit('pause_changed', {'paused': False})

@socketio.on('toggle_pause')
def handle_toggle_pause(data):
    data = data or {}; raw_code = data.get('room_code')
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код игры'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен'}); return
    state = load_room_state(game)
    if state.get('state') == 'PAUSED': success, error = resume_game(code); paused = False
    else: success, error = pause_game(code); paused = True
    if not success: emit('error', {'msg': error}); return
    emit('pause_changed', {'paused': paused})

@socketio.on('submit_answer')
def handle_submit_answer(data):
    data = data or {}; raw_code = data.get('room_code'); player_id = str(data.get('player_id') or ''); answer = data.get('answer')
    if not raw_code or not player_id or answer is None: emit('answer_error', {'msg': 'Некорректный ответ'}); return
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('answer_error', {'msg': 'Некорректный код игры'}); return
    game = get_game_by_code(code)
    if not game: emit('answer_error', {'msg': 'Игра не найдена'}); return
    players = room_players(game); player = players.get(player_id)
    if not player or player.get('sid') != request.sid: emit('answer_error', {'msg': 'Игрок не найден'}); return
    state = load_room_state(game)
    if state.get('state') == 'PAUSED': emit('answer_error', {'msg': 'Игра остановлена. Ждем ведущего'}); return
    if state.get('state') != 'QUESTION': emit('answer_error', {'msg': 'Сейчас нельзя отвечать'}); return
    if player.get('answered'): emit('answer_error', {'msg': 'Ответ уже принят'}); return
    if time.time() >= float(state.get('question_ends_at') or 0): emit('answer_error', {'msg': 'Время вышло'}); return
    _, _, question = get_current_content(state); options = question.get('question_options', []) if question else []
    if str(answer) not in [str(option) for option in options]: emit('answer_error', {'msg': 'Такого варианта нет'}); return
    player['answered'] = True; player['current_answer'] = answer; player['answered_at'] = time.time(); save_room_players(code, players)
    emit('answer_accepted', {'answer': answer}); socketio.emit('player_answered', {'player_id': player_id, 'nickname': player.get('nickname', 'Аноним')}, room=f"display_{code}")

@socketio.on('reconnect_player')
def handle_reconnect_player(data):
    data = data or {}; raw_code = data.get('room_code'); player_id = str(data.get('player_id') or '')
    if not raw_code or not player_id: return
    try: code = int(raw_code)
    except (TypeError, ValueError): return
    game = get_game_by_code(code)
    if not game: emit('player_game_not_found', {'msg': 'Игра больше не существует'}); return
    players = room_players(game); player = players.get(player_id)
    if not player: emit('player_game_not_found', {'msg': 'Игрок не найден в этой игре'}); return
    player['sid'] = request.sid; player['connected'] = True; save_room_players(code, players); join_room(code)
    emit('reconnected', {'room_code': code, 'nickname': player.get('nickname', 'Аноним')})
    game = get_game_by_code(code)
    if game: emit('game_state', build_player_state(game, player_id))

@socketio.on('join_game')
def handle_join_game(data):
    data = data or {}; raw_code = data.get('code'); nickname = str(data.get('nickname', 'Аноним')).strip()[:15] or 'Аноним'; player_id = str(data.get('player_id') or '')
    if not raw_code or not player_id: emit('error', {'msg': 'Не удалось определить игрока'}); return
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код игры'}); return
    game = get_game_by_code(code)
    if not game: emit('error', {'msg': 'Игра с таким кодом не найдена'}); return
    players = room_players(game)
    if player_id in players:
        players[player_id]['sid'] = request.sid; players[player_id]['connected'] = True
        if players[player_id].get('nickname') != nickname and nickname != 'Аноним': players[player_id]['nickname'] = nickname
        save_room_players(code, players); join_room(code)
        emit('reconnected', {'room_code': code, 'nickname': players[player_id].get('nickname', 'Аноним')}); emit('game_state', build_player_state(get_game_by_code(code), player_id)); return
    state = load_room_state(game)
    if state.get('state') not in ('WAITING', 'COUNTDOWN', 'STAGE_PREVIEW'): emit('error', {'msg': 'Игра уже идет, присоединение закрыто'}); return
    players[player_id] = {'nickname': nickname, 'sid': request.sid, 'score': 0, 'joined_at': int(time.time() * 1000), 'connected': True, 'answered': False, 'current_answer': None, 'answered_at': None, 'last_result': None}
    save_room_players(code, players); join_room(code); emit('joined_success', {'room_code': code, 'nickname': nickname})
    socketio.emit('player_joined', {'player_id': player_id, 'nickname': nickname, 'count': len(players), 'joined_at': players[player_id]['joined_at']}, room=f"display_{code}")

@socketio.on('finish_game')
def handle_finish_game(data):
    data = data or {}; raw_code = data.get('room_code')
    try: code = int(raw_code)
    except (TypeError, ValueError): emit('error', {'msg': 'Некорректный код игры'}); return
    game = get_owner_room(code)
    if not game: emit('error', {'msg': 'Доступ запрещен'}); return
    state = load_room_state(game)
    if state.get('state') == 'FINAL': emit('error', {'msg': 'Игра уже завершена'}); return
    state['state'] = 'FINAL'; state['question_started_at'] = None; state['question_ends_at'] = None; state['question_remaining'] = None; state['paused_from_state'] = None; state['pause_started_at'] = None
    next_flow_token(state); save_room_state(code, state); players = room_players(game); ranking = player_snapshot(players)
    socketio.emit('game_finished', {}, room=code); socketio.emit('game_finished', {}, room=f"display_{code}"); socketio.emit('final_results', {'players': ranking}, room=f"display_{code}")
    for player_id, player in players.items():
        sid = player.get('sid')
        if not sid: continue
        position = next((i + 1 for i, p in enumerate(ranking) if p['player_id'] == player_id), None)
        socketio.emit('final_results', {'position': position, 'score': player.get('score', 0), 'players': ranking}, to=sid)
    session.pop('hosted_room_code', None); emit('finish_complete', {'room_code': code}); socketio.start_background_task(final_cleanup_worker, code)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid; conn = get_db(BASE_DIR); cursor = conn.cursor(); cursor.execute("SELECT id, invite_code, session_data FROM active_rooms"); changed = []
    for room in cursor.fetchall():
        room_changed = False; players = room_players(dict(room))
        for player_id, player in players.items():
            if player.get('sid') == sid: player['connected'] = False; changed.append((room['invite_code'], player_id)); room_changed = True
        if room_changed: conn.execute("UPDATE active_rooms SET session_data = ? WHERE id = ?", (json.dumps(players, ensure_ascii=False), room['id']))
    conn.commit(); conn.close()
    for code, player_id in changed: socketio.emit('player_status', {'player_id': player_id, 'connected': False}, room=f"display_{code}")

if __name__ == "__main__": socketio.run(app, host='0.0.0.0', port=5000)