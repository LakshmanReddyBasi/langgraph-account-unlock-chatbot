# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import random
# import datetime
# from database import get_db_connection, create_tables, seed_data
# from services import send_email_otp, send_sms_otp
# from workflow import build_workflow

# app = Flask(__name__)
# CORS(app)
# workflow = build_workflow()

# # In-memory session store
# sessions = {}

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/chat', methods=['POST'])
# def chat():
#     data = request.json
#     message = data.get("message", "").strip()
#     session_id = data.get("session_id")

#     if not session_id:
#         return jsonify({"error": "session_id required"}), 400

#     # Extract user_id (for demo, assume "john.doe" if locked mentioned)
#     user_id = "john.doe" if "locked" in message.lower() else None

#     current = sessions.get(session_id)

#     # Case 1: Waiting for OTP
#     if current and current.get("waiting_for_otp"):
#         otp = message
#         user_id = current["user_id"]
#         conn = get_db_connection()
#         row = conn.execute("SELECT otp, expiry_time FROM otps WHERE user_id = ?", (user_id,)).fetchone()
#         valid = False
#         if row:
#             stored_otp, expiry = row["otp"], datetime.datetime.fromisoformat(row["expiry_time"])
#             if otp == stored_otp and datetime.datetime.now() < expiry:
#                 valid = True
#         conn.close()

#         attempts = current.get("otp_attempts", 0) + 1

#         if valid:
#             # Unlock account
#             conn = get_db_connection()
#             conn.execute("UPDATE users SET status = 'active' WHERE user_id = ?", (user_id,))
#             conn.commit()
#             conn.close()
#             del sessions[session_id]
#             return jsonify({"reply": "✅ Your account has been unlocked!"})
#         else:
#             if attempts >= 2:
#                 # Escalate
#                 conn = get_db_connection()
#                 conn.execute("INSERT INTO escalation_tickets (user_id, issue_description) VALUES (?, ?)",
#                              (user_id, "OTP failed 2+ times"))
#                 conn.commit()
#                 conn.close()
#                 del sessions[session_id]
#                 return jsonify({"reply": "❌ Too many failed attempts. Your issue has been escalated to IT support."})
#             else:
#                 sessions[session_id] = {
#                     "user_id": user_id,
#                     "waiting_for_otp": True,
#                     "otp_attempts": attempts
#                 }
#                 return jsonify({"reply": f"❌ Invalid OTP. Attempt {attempts}/2. Please try again."})

#     # Case 2: New request
#     if "locked" in message.lower() and user_id:
#         initial = {"user_id": user_id}
#         result = workflow.invoke(initial)
#         if result["account_status"] == "locked":
#             sessions[session_id] = {
#                 "user_id": user_id,
#                 "waiting_for_otp": True,
#                 "otp_attempts": 0
#             }
#             return jsonify({"reply": result["message"]})
#         else:
#             return jsonify({"reply": result["message"]})

#     return jsonify({"reply": "I can help if your account is locked. Say: 'My account is locked'."})

# # --- Internal APIs ---
# @app.route('/check_account_status', methods=['POST'])
# def check_account_status():
#     user_id = request.json["user_id"]
#     conn = get_db_connection()
#     row = conn.execute("SELECT status FROM users WHERE user_id = ?", (user_id,)).fetchone()
#     conn.close()
#     if row:
#         return jsonify({"status": row["status"]})
#     return jsonify({"error": "User not found"}), 404

# @app.route('/send_otp', methods=['POST'])
# def send_otp():
#     user_id = request.json["user_id"]
#     conn = get_db_connection()
#     user = conn.execute("SELECT email, phone_number FROM users WHERE user_id = ?", (user_id,)).fetchone()
#     if not user:
#         return jsonify({"error": "User not found"}), 404
#     otp = str(random.randint(100000, 999999))
#     expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
#     conn.execute("INSERT OR REPLACE INTO otps (user_id, otp, expiry_time) VALUES (?, ?, ?)",
#                  (user_id, otp, expiry.isoformat()))
#     conn.commit()
#     conn.close()
#     send_email_otp(user["email"], otp)
#     send_sms_otp(user["phone_number"], otp)
#     return jsonify({"ok": True})

# @app.route('/create_escalation_ticket', methods=['POST'])
# def create_escalation_ticket():
#     data = request.json
#     conn = get_db_connection()
#     conn.execute("INSERT INTO escalation_tickets (user_id, issue_description) VALUES (?, ?)",
#                  (data["user_id"], data["issue"]))
#     conn.commit()
#     conn.close()
#     return jsonify({"ok": True})

# if __name__ == '__main__':
#     create_tables()
#     seed_data()
#     app.run(port=5000, debug=True, threaded=True)

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
from database import get_db_connection, initialize_database
from services import send_email_otp, send_sms_otp
from workflow import build_workflow, otp_verification_node, TicketState
import datetime
import random

# Initialize the database on startup if it doesn't exist
# This is crucial for cloud deployment environments.
if not os.path.exists('account_unlock.db'):
    initialize_database()

app = Flask(__name__)
CORS(app) 

# In-memory session storage for the demo.
# In a real production app, you might use a more persistent store like Redis.
graph_sessions = {}
workflow = build_workflow()

@app.route('/')
def index():
    """Serves the frontend HTML page."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handles the chatbot conversation logic and session management."""
    data = request.json
    user_message = data.get('message')
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    current_state = graph_sessions.get(session_id, {})
    
    # Check if the bot is waiting for an OTP
    is_waiting_for_otp = current_state.get('account_status') == 'locked' and not current_state.get('verified')

    if is_waiting_for_otp:
        # The user's message is assumed to be the OTP
        state_after_verification = otp_verification_node(current_state, user_message)
        
        if state_after_verification.get('verified'):
            # If verified, continue the workflow to unlock the account
            final_state = workflow.invoke(state_after_verification)
            bot_reply = final_state.get('message', 'Your account has been unlocked!')
            graph_sessions.pop(session_id, None) # Clear session on completion
        else:
            # If not verified, escalate
            final_state = workflow.invoke(state_after_verification, config={"configurable": {"node": "escalate"}})
            bot_reply = final_state.get('message')
            graph_sessions.pop(session_id, None) # Clear session on completion
        
        return jsonify({"reply": bot_reply})

    # Start a new conversation if the user mentions their account is locked
    if "locked" in user_message.lower():
        initial_state = {"user_id": "john.doe"} # Hardcoded for the demo
        
        # Run the workflow until it stops to send the OTP or if the account is already active
        state_after_otp_sent = workflow.invoke(initial_state)
        
        # Store the current state in our session manager
        graph_sessions[session_id] = state_after_otp_sent
        
        bot_reply = state_after_otp_sent.get('message')
        # If the account was already active, the flow ends, so we can clear the session
        if state_after_otp_sent.get('account_status') == 'active':
            graph_sessions.pop(session_id, None)

        return jsonify({"reply": bot_reply})

    # Default reply for messages that don't start the workflow
    return jsonify({"reply": "I can help with locked accounts. Please say something like 'My account is locked'."})

# --- All API Endpoints remain the same from your file ---
@app.route('/check_account_status', methods=['POST'])
def check_account_status():
    data = request.json; user_id = data.get('user_id')
    conn = get_db_connection(); user = conn.execute("SELECT status FROM users WHERE user_id = ?", (user_id,)).fetchone(); conn.close()
    return jsonify({"user_id": user_id, "status": user['status']}) if user else (jsonify({"error": "User not found"}), 404)

@app.route('/send_otp', methods=['POST'])
def handle_send_otp():
    data = request.json; user_id = data.get('user_id')
    conn = get_db_connection(); user = conn.execute("SELECT email, phone_number FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not user: conn.close(); return jsonify({"error": "User not found"}), 404
    otp = str(random.randint(100000, 999999))
    expiry = (datetime.datetime.now() + datetime.timedelta(minutes=10)).isoformat()
    conn.execute("INSERT OR REPLACE INTO otps (user_id, otp, expiry_time) VALUES (?, ?, ?)",(user_id, otp, expiry))
    conn.commit(); conn.close()
    send_email_otp(user['email'], otp); send_sms_otp(user['phone_number'], otp)
    return jsonify({"message": "OTP sent successfully."})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json; user_id = data.get('user_id'); otp_submitted = data.get('otp')
    conn = get_db_connection(); otp_data = conn.execute("SELECT otp, expiry_time FROM otps WHERE user_id = ?", (user_id,)).fetchone(); conn.close()
    if not otp_data: return jsonify({"verified": False, "error": "No OTP found."}), 404
    is_valid = otp_data['otp'] == otp_submitted and datetime.datetime.now() < datetime.datetime.fromisoformat(otp_data['expiry_time'])
    return jsonify({"verified": True}) if is_valid else jsonify({"verified": False, "error": "Invalid or expired OTP."})

@app.route('/unlock_account', methods=['POST'])
def unlock_account():
    data = request.json; user_id = data.get('user_id')
    conn = get_db_connection(); conn.execute("UPDATE users SET status = 'active' WHERE user_id = ?", (user_id,)); conn.commit(); conn.close()
    return jsonify({"status": "success", "message": "Account unlocked."})

@app.route('/create_escalation_ticket', methods=['POST'])
def create_escalation_ticket():
    data = request.json; user_id = data.get('user_id'); issue = data.get('issue')
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("INSERT INTO escalation_tickets (user_id, issue_description) VALUES (?, ?)", (user_id, issue)); conn.commit()
    ticket_id = cursor.lastrowid; conn.close()
    return jsonify({"status": "success", "ticket_id": ticket_id})

# The if __name__ == '__main__' block is removed as Gunicorn will run the app

