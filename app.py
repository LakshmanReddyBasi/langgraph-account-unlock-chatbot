from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from database import get_db_connection, initialize_database
from services import send_email_otp, send_sms_otp
# The problematic import is removed from here
from workflow import build_workflow, TicketState 
import datetime
import random
from psycopg2.extras import DictCursor

# This function is now defined directly inside app.py
def otp_verification_node(state: TicketState, otp_from_user: str):
    """
    Verifies the OTP provided by the user against the database.
    This is a helper function, not a graph node.
    """
    user_id = state['user_id']
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT otp, expiry_time FROM otps WHERE user_id = %s", (user_id,))
            otp_data = cur.fetchone()
    
    new_attempts = state.get('otp_attempts', 0) + 1
    
    if otp_data and otp_data['otp'] == otp_from_user and datetime.datetime.now(datetime.timezone.utc) < otp_data['expiry_time']:
        return {
            **state,
            "verified": True,
            "otp_attempts": new_attempts,
            "action_log": state.get('action_log', []) + ["OTP verification successful."]
        }
    else:
        return {
            **state,
            "verified": False,
            "otp_attempts": new_attempts,
            "action_log": state.get('action_log', []) + [f"OTP verification failed. Attempt {new_attempts}."]
        }


# Initialize the database on startup
initialize_database()

app = Flask(__name__)
CORS(app) 

graph_sessions = {}
workflow = build_workflow()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # Chat logic remains the same
    data = request.json
    user_message = data.get('message')
    session_id = data.get('session_id')
    if not session_id: return jsonify({"error": "session_id is required"}), 400
    current_state = graph_sessions.get(session_id, {})
    is_waiting_for_otp = current_state.get('account_status') == 'locked' and not current_state.get('verified')
    if is_waiting_for_otp:
        state_after_verification = otp_verification_node(current_state, user_message)
        if state_after_verification.get('verified'):
            final_state = workflow.invoke(state_after_verification)
            bot_reply = final_state.get('message', 'Your account has been unlocked!')
        else:
            final_state = workflow.invoke(state_after_verification, config={"configurable": {"node": "escalate"}})
            bot_reply = final_state.get('message')
        graph_sessions.pop(session_id, None)
        return jsonify({"reply": bot_reply})
    if "locked" in user_message.lower():
        initial_state = {"user_id": "john.doe"}
        state_after_otp_sent = workflow.invoke(initial_state)
        graph_sessions[session_id] = state_after_otp_sent
        bot_reply = state_after_otp_sent.get('message')
        if state_after_otp_sent.get('account_status') == 'active':
            graph_sessions.pop(session_id, None)
        return jsonify({"reply": bot_reply})
    return jsonify({"reply": "I can help with locked accounts. Try 'My account is locked'."})

# --- API Endpoints (PostgreSQL version) ---
@app.route('/check_account_status', methods=['POST'])
def check_account_status():
    user_id = request.json.get('user_id')
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
    if user:
        return jsonify({"user_id": user_id, "status": user['status']})
    return jsonify({"error": "User not found"}), 404

@app.route('/send_otp', methods=['POST'])
def handle_send_otp():
    user_id = request.json.get('user_id')
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT email, phone_number FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if not user: return jsonify({"error": "User not found"}), 404
            otp = str(random.randint(100000, 999999))
            expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
            cur.execute("INSERT INTO otps (user_id, otp, expiry_time) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET otp = EXCLUDED.otp, expiry_time = EXCLUDED.expiry_time", (user_id, otp, expiry))
        conn.commit()
    send_email_otp(user['email'], otp)
    send_sms_otp(user['phone_number'], otp)
    return jsonify({"message": "OTP sent successfully."})

# Note: The original /verify_otp endpoint is no longer called by the app, 
# as the logic is now in otp_verification_node. It can be kept for API testing.
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_id = request.json.get('user_id'); otp_submitted = request.json.get('otp')
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT otp, expiry_time FROM otps WHERE user_id = %s", (user_id,))
            otp_data = cur.fetchone()
    if not otp_data: return jsonify({"verified": False, "error": "No OTP found."}), 404
    is_valid = otp_data['otp'] == otp_submitted and datetime.datetime.now(datetime.timezone.utc) < otp_data['expiry_time']
    return jsonify({"verified": True}) if is_valid else jsonify({"verified": False, "error": "Invalid or expired OTP."})

@app.route('/unlock_account', methods=['POST'])
def unlock_account():
    user_id = request.json.get('user_id')
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status = 'active' WHERE user_id = %s", (user_id,))
        conn.commit()
    return jsonify({"status": "success", "message": "Account unlocked."})

@app.route('/create_escalation_ticket', methods=['POST'])
def create_escalation_ticket():
    user_id = request.json.get('user_id')
    issue = request.json.get('issue')
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO escalation_tickets (user_id, issue_description) VALUES (%s, %s) RETURNING ticket_id", (user_id, issue))
            ticket_id = cur.fetchone()[0]
        conn.commit()
    return jsonify({"status": "success", "ticket_id": ticket_id})

