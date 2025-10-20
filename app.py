# app.py

import os
import sys
import traceback
import random
import datetime
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from database import get_db_connection, initialize_database
from services import send_email_otp, send_sms_otp
from workflow import build_workflow
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
import bcrypt

load_dotenv()

print("--- Starting Application ---")

app = Flask(__name__)
CORS(app)

# Build workflow once
workflow = build_workflow()
graph_sessions = {}

# Initialize DB
initialize_database()
print("Application ready.")

# === Fixed Messages ===
MESSAGES = {
    "greeting": "Hello! I'm your Account Unlock Assistant. Say 'My account is locked' or provide your user ID to begin.",
    "ask_user_id": "Please provide your user ID (e.g., john.doe).",
    "user_not_found": "I couldn't find an account with that user ID. Please check and try again.",
    "account_active": "Good news! Your account is already active.",
    "confirm_send_otp": "I found your account: {full_name}. Shall I send a verification code to your email and phone? (Reply YES or NO)",
    "otp_sent": "A 6-digit OTP has been sent to your email and phone. Please enter it here.",
    "otp_incorrect": "The OTP you entered is incorrect. Please try again ({attempts}/3).",
    "otp_expired_or_failed": "Too many failed attempts. Your request has been escalated to support.",
    "unlock_success": "Mr. {full_name}, your account has been successfully unlocked. Thank you!",
    "escalated": "I'm sorry, but after multiple failed attempts, I've escalated this to our support team. They'll contact you shortly.",
    "resend_otp": "A new OTP has been sent. Please check your email/phone and enter the code.",
    "awaiting_otp": "Please enter the 6-digit OTP you received."
}

SESSION_TIMEOUT = 600  # 10 minutes

def cleanup_expired_sessions():
    """Remove sessions older than SESSION_TIMEOUT."""
    now = time.time()
    expired = [sid for sid, sess in graph_sessions.items() if now - sess.get("last_activity", 0) > SESSION_TIMEOUT]
    for sid in expired:
        graph_sessions.pop(sid, None)

@app.route('/health')
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "ok", "db": "connected", "sessions": len(graph_sessions)})
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

def get_reply(session, message=""):
    state = session.get("state", "INIT")
    if state == "INIT":
        if any(kw in message.lower() for kw in ["locked", "unlock", "help"]):
            return MESSAGES["ask_user_id"]
        else:
            return MESSAGES["greeting"]
    elif state == "AWAITING_USER_ID":
        return MESSAGES["ask_user_id"]
    elif state == "AWAITING_CONFIRMATION":
        full_name = session.get("full_name", "user")
        return MESSAGES["confirm_send_otp"].format(full_name=full_name)
    elif state == "AWAITING_OTP":
        return MESSAGES["awaiting_otp"]
    return "How can I help you?"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        cleanup_expired_sessions()
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"reply": "Session ID is missing."}), 400

        session = graph_sessions.get(session_id, {"state": "INIT", "last_activity": time.time()})
        session["last_activity"] = time.time()

        if session["state"] == "INIT":
            if any(kw in user_message.lower() for kw in ["locked", "unlock", "my account"]):
                session["state"] = "AWAITING_USER_ID"
                reply = MESSAGES["ask_user_id"]
            else:
                reply = MESSAGES["greeting"]

        elif session["state"] == "AWAITING_USER_ID":
            user_id = user_message.lower()
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT full_name, status FROM users WHERE user_id = %s", (user_id,))
                    user = cur.fetchone()
            
            if user:
                if user["status"] == "active":
                    reply = MESSAGES["account_active"]
                    graph_sessions.pop(session_id, None)
                else:
                    session.update({
                        "user_id": user_id,
                        "full_name": user["full_name"],
                        "state": "AWAITING_CONFIRMATION"
                    })
                    reply = MESSAGES["confirm_send_otp"].format(full_name=user["full_name"])
            else:
                reply = MESSAGES["user_not_found"]

        elif session["state"] == "AWAITING_CONFIRMATION":
            if any(kw in user_message.lower() for kw in ["yes", "ok", "sure", "y"]):
                initial_state = {"user_id": session["user_id"]}
                graph_state = workflow.invoke(initial_state)
                session["langgraph_state"] = graph_state
                session["state"] = "AWAITING_OTP"
                session["otp_attempts"] = 0
                reply = MESSAGES["otp_sent"]
            else:
                reply = "Understood. Let me know when you're ready."
                graph_sessions.pop(session_id, None)

        elif session["state"] == "AWAITING_OTP":
            if any(kw in user_message.lower() for kw in ["resend", "send again", "didn't get"]):
                langgraph_state = session.get("langgraph_state", {})
                new_state = workflow.invoke(langgraph_state, config={"configurable": {"node": "send_otp"}})
                session["langgraph_state"] = new_state
                reply = MESSAGES["resend_otp"]
            else:
                otp = ''.join(filter(str.isdigit, user_message))
                if len(otp) == 6:
                    session["otp_attempts"] = session.get("otp_attempts", 0) + 1
                    verified = verify_otp(session["user_id"], otp)
                    
                    if verified:
                        with get_db_connection() as conn:
                            with conn.cursor() as cur:
                                cur.execute("UPDATE users SET status = 'active' WHERE user_id = %s", (session["user_id"],))
                            conn.commit()
                        reply = MESSAGES["unlock_success"].format(full_name=session["full_name"])
                        graph_sessions.pop(session_id, None)
                    else:
                        if session["otp_attempts"] >= 3:
                            workflow.invoke(session.get("langgraph_state", {}), config={"configurable": {"node": "escalate"}})
                            reply = MESSAGES["escalated"]
                            graph_sessions.pop(session_id, None)
                        else:
                            reply = MESSAGES["otp_incorrect"].format(attempts=session["otp_attempts"])
                else:
                    reply = MESSAGES["awaiting_otp"]

        if session.get("state") != "ENDED":
            graph_sessions[session_id] = session

        print(f"[CHAT] User: {user_message} → Bot: {reply}")  # Structured log
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"[ERROR] /chat: {e}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"reply": "Sorry, an error occurred. Please try again."}), 500

def verify_otp(user_id, otp):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT otp_hash, expiry_time FROM otps WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
    if not row:
        return False
    is_valid = (
        datetime.datetime.now(datetime.timezone.utc) < row["expiry_time"] and
        bcrypt.checkpw(otp.encode(), row["otp_hash"].tobytes())
    )
    return is_valid

@app.route('/send_otp', methods=['POST'])
def handle_send_otp():
    user_id = request.json.get('user_id')
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT email, phone_number, last_otp_request FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Rate limiting: max 2 OTPs/hour
            now = datetime.datetime.now(datetime.timezone.utc)
            last_request = user["last_otp_request"]
            if last_request and (now - last_request).total_seconds() < 3600:
                cur.execute("SELECT COUNT(*) FROM otps WHERE user_id = %s AND expiry_time > %s", (user_id, now))
                count = cur.fetchone()[0]
                if count >= 2:
                    return jsonify({"message": "Too many OTP requests. Please try again later."}), 429

            otp = str(random.randint(100000, 999999))
            expiry = now + datetime.timedelta(minutes=10)
            otp_hash = bcrypt.hashpw(otp.encode(), bcrypt.gensalt())

            cur.execute(
                """INSERT INTO otps (user_id, otp_hash, expiry_time) 
                   VALUES (%s, %s, %s) 
                   ON CONFLICT (user_id) 
                   DO UPDATE SET otp_hash = EXCLUDED.otp_hash, expiry_time = EXCLUDED.expiry_time""",
                (user_id, otp_hash, expiry)
            )
            cur.execute(
                "UPDATE users SET last_otp_request = %s WHERE user_id = %s",
                (now, user_id)
            )
        conn.commit()
        
    send_email_otp(user['email'], otp)
    send_sms_otp(user['phone_number'], otp)
    
    return jsonify({"message": "A 6-digit OTP has been sent to your email and phone. Please enter it here."})

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
            cur.execute(
                "INSERT INTO escalation_tickets (user_id, issue_description) VALUES (%s, %s) RETURNING ticket_id",
                (user_id, issue)
            )
            ticket_id = cur.fetchone()[0]
        conn.commit()
    return jsonify({"status": "success", "ticket_id": ticket_id})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)