# from flask import Flask, request, jsonify, render_template
# from flask_cors import CORS
# import os
# import sys
# import traceback
# from database import get_db_connection, initialize_database
# from services import send_email_otp, send_sms_otp
# from workflow import build_workflow, TicketState
# import datetime
# import random
# from psycopg2.extras import DictCursor
# from openai import OpenAI
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# print("--- Starting Application ---")

# # --- OpenRouter LLM Configuration ---
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# if not OPENROUTER_API_KEY:
#     print("WARNING: OPENROUTER_API_KEY not found. LLM features will be disabled.", file=sys.stderr)

# # Initialize the client only if the key exists
# openrouter_client = None
# if OPENROUTER_API_KEY:
#     openrouter_client = OpenAI(
#       base_url="https://openrouter.ai/api/v1",
#       api_key=OPENROUTER_API_KEY,
#     )

# def get_llm_reply(prompt):
#     """Generates a conversational reply using an OpenRouter model."""
#     if not openrouter_client:
#         # Fallback to hardcoded responses if OpenRouter is not configured
#         if "ask them for their user ID" in prompt:
#             return "I can help with that. Which user ID is locked?"
#         if "ask them for the OTP" in prompt:
#             return "An OTP has been sent to your registered email/phone. Please enter it below."
#         return "I can only help with locked accounts. Please try saying 'My account is locked'."

#     try:
#         chat_completion = openrouter_client.chat.completions.create(
#             model="mistralai/mistral-7b-instruct:free", # Using a free, high-quality model
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a friendly and helpful Account Unlock Assistant. Your goal is to guide users through account recovery. Be concise, clear, and conversational. Do not ask for personal information other than the user ID or OTP when prompted."
#                 },
#                 {
#                     "role": "user",
#                     "content": prompt,
#                 }
#             ],
#             temperature=0.7,
#             max_tokens=100,
#         )
#         return chat_completion.choices[0].message.content
#     except Exception as e:
#         print(f"Error calling OpenRouter API: {e}. This is likely due to an invalid or misconfigured OPENROUTER_API_KEY.", file=sys.stderr)
#         return "I'm sorry, I'm having a problem with my connection to the AI service. The API key may be invalid."

# # Initialize the Flask app and apply CORS
# app = Flask(__name__)
# CORS(app)
# print("Flask app and CORS initialized.")

# # This helper function is now part of app.py to avoid import errors
# def otp_verification_node(state: TicketState, otp_from_user: str):
#     user_id = state['user_id']
#     with get_db_connection() as conn:
#         with conn.cursor(cursor_factory=DictCursor) as cur:
#             cur.execute("SELECT otp, expiry_time FROM otps WHERE user_id = %s", (user_id,))
#             otp_data = cur.fetchone()
    
#     new_attempts = state.get('otp_attempts', 0) + 1
    
#     if otp_data and otp_data['otp'] == otp_from_user and datetime.datetime.now(datetime.timezone.utc) < otp_data['expiry_time']:
#         return { **state, "verified": True, "otp_attempts": new_attempts, "action_log": state.get('action_log', []) + ["OTP verification successful."]}
#     else:
#         return { **state, "verified": False, "otp_attempts": new_attempts, "action_log": state.get('action_log', []) + [f"OTP verification failed. Attempt {new_attempts}."]}

# # Initialize the database on startup
# print("Attempting to initialize database...")
# initialize_database()
# print("Database initialization successful.")

# # In-memory session storage for the chatbot state
# graph_sessions = {}
# print("Building LangGraph workflow...")
# workflow = build_workflow()
# print("Workflow built successfully. Application is ready.")


# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/chat', methods=['POST'])
# def chat():
#     try:
#         data = request.json
#         user_message = data.get('message', '').strip()
#         session_id = data.get('session_id')
        
#         if not all([session_id, user_message]):
#             return jsonify({"reply": "I'm sorry, I didn't receive a message."})

#         current_state = graph_sessions.get(session_id, {})
        
#         if current_state.get('awaiting_user_id'):
#             user_id = user_message.lower() # Normalize user ID
#             with get_db_connection() as conn:
#                 with conn.cursor() as cur:
#                     cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
#                     user_exists = cur.fetchone()
            
#             if user_exists:
#                 initial_state = {"user_id": user_id}
#                 state_after_otp_sent = workflow.invoke(initial_state)
#                 graph_sessions[session_id] = state_after_otp_sent
#                 bot_reply = state_after_otp_sent.get('message')
#                 if state_after_otp_sent.get('account_status') == 'active':
#                     graph_sessions.pop(session_id, None)
#             else:
#                 prompt = f"The user entered an invalid user ID: '{user_id}'. Politely tell them it was not found and ask them to try again."
#                 bot_reply = get_llm_reply(prompt)

#             return jsonify({"reply": bot_reply})

#         is_waiting_for_otp = current_state.get('account_status') == 'locked' and not current_state.get('verified')
#         if is_waiting_for_otp:
#             state_after_verification = otp_verification_node(current_state, user_message)
            
#             if state_after_verification.get('verified'):
#                 final_state = workflow.invoke(state_after_verification)
#                 bot_reply = final_state.get('message', 'Your account has been unlocked!')
#             else:
#                 final_state = workflow.invoke(state_after_verification, config={"configurable": {"node": "escalate"}})
#                 bot_reply = final_state.get('message')
            
#             graph_sessions.pop(session_id, None)
#             return jsonify({"reply": bot_reply})

#         if "locked" in user_message.lower():
#             graph_sessions[session_id] = {'awaiting_user_id': True}
#             prompt = "The user said their account is locked. Greet them and ask them for their user ID."
#             bot_reply = get_llm_reply(prompt)
#             return jsonify({"reply": bot_reply})

#         prompt = f"The user sent an off-topic message: '{user_message}'. Gently guide them back to the topic of unlocking their account."
#         bot_reply = get_llm_reply(prompt)
#         return jsonify({"reply": bot_reply})

#     except Exception as e:
#         print(f"An error occurred in /chat: {e}", file=sys.stderr)
#         traceback.print_exc(file=sys.stderr)
#         return jsonify({"reply": "Sorry, a critical server error occurred. Please try again later."}), 500

# # --- API Endpoints are unchanged ---
# @app.route('/check_account_status', methods=['POST'])
# def check_account_status():
#     user_id = request.json.get('user_id')
#     with get_db_connection() as conn:
#         with conn.cursor(cursor_factory=DictCursor) as cur:
#             cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
#             user = cur.fetchone()
#     if user:
#         return jsonify({"user_id": user_id, "status": user['status']})
#     return jsonify({"error": "User not found"}), 404

# @app.route('/send_otp', methods=['POST'])
# def handle_send_otp():
#     user_id = request.json.get('user_id')
#     with get_db_connection() as conn:
#         with conn.cursor(cursor_factory=DictCursor) as cur:
#             cur.execute("SELECT email, phone_number FROM users WHERE user_id = %s", (user_id,))
#             user = cur.fetchone()
#             if not user: return jsonify({"error": "User not found"}), 404
            
#             otp = str(random.randint(100000, 999999))
#             expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
            
#             cur.execute(
#                 "INSERT INTO otps (user_id, otp, expiry_time) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET otp = EXCLUDED.otp, expiry_time = EXCLUDED.expiry_time",
#                 (user_id, otp, expiry)
#             )
#         conn.commit()
        
#     send_email_otp(user['email'], otp)
#     send_sms_otp(user['phone_number'], otp)
    
#     # Generate a user-friendly message with the LLM
#     prompt = "You have just sent an OTP to the user's email and phone. Inform them of this and ask them to enter the OTP they received."
#     message = get_llm_reply(prompt)
#     return jsonify({"message": message})


# @app.route('/unlock_account', methods=['POST'])
# def unlock_account():
#     user_id = request.json.get('user_id')
#     with get_db_connection() as conn:
#         with conn.cursor() as cur:
#             cur.execute("UPDATE users SET status = 'active' WHERE user_id = %s", (user_id,))
#         conn.commit()
#     return jsonify({"status": "success", "message": "Account unlocked."})

# @app.route('/create_escalation_ticket', methods=['POST'])
# def create_escalation_ticket():
#     user_id = request.json.get('user_id')
#     issue = request.json.get('issue')
#     with get_db_connection() as conn:
#         with conn.cursor() as cur:
#             cur.execute(
#                 "INSERT INTO escalation_tickets (user_id, issue_description) VALUES (%s, %s) RETURNING ticket_id",
#                 (user_id, issue)
#             )
#             ticket_id = cur.fetchone()[0]
#         conn.commit()
#     return jsonify({"status": "success", "ticket_id": ticket_id})

# if __name__ == '__main__':
#     app.run(port=5000, debug=True, threaded=True)
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys
import traceback
from database import get_db_connection, initialize_database
from services import send_email_otp, send_sms_otp
from workflow import build_workflow, TicketState
import datetime
import random
from psycopg2.extras import DictCursor
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("--- Starting Application ---")

# --- OpenRouter LLM Configuration ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
openrouter_client = None
if OPENROUTER_API_KEY:
    openrouter_client = OpenAI(
      base_url="https://openrouter.ai/api/v1",
      api_key=OPENROUTER_API_KEY,
    )
else:
    print("WARNING: OPENROUTER_API_KEY not found. LLM features will be disabled.", file=sys.stderr)


# --- State Machine Definitions ---
STATE_INIT = "INIT"
STATE_AWAITING_USER_ID = "AWAITING_USER_ID"
STATE_AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
STATE_AWAITING_OTP = "AWAITING_OTP"


def get_llm_reply(prompt_template, **kwargs):
    """Generates a conversational reply using an OpenRouter model."""
    if not openrouter_client:
        return "LLM service is not configured. Please contact support."

    prompt = prompt_template.format(**kwargs)

    try:
        chat_completion = openrouter_client.chat.completions.create(
            model="mistralai/mistral-7b-instruct:free",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional and friendly Account Unlock Assistant. Your primary goal is to securely guide users through unlocking their account. You must follow the user's instructions precisely. Be concise and clear. Do not add any markdown like [OUT] or [MESSAGE]."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.4, # Reduced for more predictable responses
            max_tokens=150,
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}", file=sys.stderr)
        return "I'm sorry, I'm having a problem with my connection to the AI service. Please try again in a moment."

# Initialize the Flask app and apply CORS
app = Flask(__name__)
CORS(app)

# Initialize the database on startup
initialize_database()

# In-memory session storage for the chatbot state
graph_sessions = {}
workflow = build_workflow()
print("Workflow built successfully. Application is ready.")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"reply": "Session ID is missing."}), 400

        session = graph_sessions.get(session_id, {"state": STATE_INIT})
        current_state = session.get("state")
        bot_reply = ""

        # --- Main State Machine Logic ---

        if current_state == STATE_INIT:
            prompt = f"Analyze the user's intent from their message: '{user_message}'. Respond with one word only: UNLOCK, GREETING, or OTHER."
            intent = get_llm_reply(prompt).upper()
            
            if "UNLOCK" in intent:
                session["state"] = STATE_AWAITING_USER_ID
                prompt = "The user wants to unlock their account. Ask them for their user ID."
                bot_reply = get_llm_reply(prompt)
            else:
                prompt = f"The user said: '{user_message}'. Respond with a friendly greeting and briefly state that you can help with locked accounts."
                bot_reply = get_llm_reply(prompt)

        elif current_state == STATE_AWAITING_USER_ID:
            user_id = user_message.lower()
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT full_name FROM users WHERE user_id = %s", (user_id,))
                    user = cur.fetchone()
            
            if user:
                session["user_id"] = user_id
                session["full_name"] = user["full_name"]
                session["state"] = STATE_AWAITING_CONFIRMATION
                prompt = f"The user's ID is '{user_id}'. Confirm you've found the account for '{user['full_name']}' and ask if you should proceed with sending an OTP. Instruct them to reply with 'yes' or 'no'."
                bot_reply = get_llm_reply(prompt)
            else:
                prompt = f"The user entered an invalid user ID: '{user_id}'. Politely inform them it was not found and ask them to provide a correct one."
                bot_reply = get_llm_reply(prompt)

        elif current_state == STATE_AWAITING_CONFIRMATION:
            prompt = f"The user responded with '{user_message}'. Does this indicate a positive confirmation (like 'yes', 'ok', 'proceed')? Respond with one word only: YES or NO."
            confirmation = get_llm_reply(prompt).upper()
            
            if "YES" in confirmation:
                initial_state = {"user_id": session["user_id"]}
                graph_state = workflow.invoke(initial_state)

                if graph_state.get('account_status') == 'active':
                    bot_reply = "Good news! It looks like that account is already active, so no further action is needed."
                    graph_sessions.pop(session_id, None)
                else:
                    session["langgraph_state"] = graph_state
                    session["state"] = STATE_AWAITING_OTP
                    bot_reply = graph_state.get("message")
            else:
                bot_reply = "Understood. I will not proceed. Please let me know if you change your mind."
                graph_sessions.pop(session_id, None)

        elif current_state == STATE_AWAITING_OTP:
            prompt = f"The user sent this message: '{user_message}'. Analyze their intent. Respond with one word only: PROVIDE_OTP, RESEND_OTP, or OTHER_QUERY."
            intent = get_llm_reply(prompt).upper()
            langgraph_state = session.get("langgraph_state", {})

            if "PROVIDE_OTP" in intent:
                state_after_verification = otp_verification_node(langgraph_state, user_message)
                
                if state_after_verification.get('verified'):
                    final_state = workflow.invoke(state_after_verification)
                    prompt = "The user '{full_name}' ({user_id}) has been successfully verified and their account is unlocked. Provide a warm, personalized confirmation message.".format(
                        full_name=session.get("full_name", "user"), user_id=session.get("user_id")
                    )
                    bot_reply = get_llm_reply(prompt)
                    graph_sessions.pop(session_id, None)
                else:
                    session["langgraph_state"] = state_after_verification
                    if state_after_verification.get('otp_attempts', 0) >= 3:
                        final_state = workflow.invoke(state_after_verification, config={"configurable": {"node": "escalate"}})
                        bot_reply = final_state.get('message')
                        graph_sessions.pop(session_id, None)
                    else:
                        prompt = "The user entered an incorrect OTP. Inform them it was wrong and ask them to please try again."
                        bot_reply = get_llm_reply(prompt)
            
            elif "RESEND_OTP" in intent:
                graph_state = workflow.invoke(langgraph_state, config={"configurable": {"node": "send_otp"}})
                session["langgraph_state"] = graph_state
                bot_reply = graph_state.get("message")
            
            else: # OTHER_QUERY
                prompt = f"The user is in the OTP step but asked: '{user_message}'. Gently guide them back, reminding them you're waiting for their 6-digit code."
                bot_reply = get_llm_reply(prompt)

        graph_sessions[session_id] = session
        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"An error occurred in /chat: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"reply": "Sorry, a critical server error occurred. Please try again later."}), 500

def otp_verification_node(state: TicketState, otp_from_user: str):
    user_id = state['user_id']
    otp = ''.join(filter(str.isdigit, otp_from_user))
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT otp, expiry_time FROM otps WHERE user_id = %s", (user_id,))
            otp_data = cur.fetchone()
    new_attempts = state.get('otp_attempts', 0) + 1
    if otp_data and otp_data['otp'] == otp and datetime.datetime.now(datetime.timezone.utc) < otp_data['expiry_time']:
        return {**state, "verified": True, "otp_attempts": new_attempts}
    return {**state, "verified": False, "otp_attempts": new_attempts}

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
            
            cur.execute(
                "INSERT INTO otps (user_id, otp, expiry_time) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET otp = EXCLUDED.otp, expiry_time = EXCLUDED.expiry_time",
                (user_id, otp, expiry)
            )
        conn.commit()
        
    send_email_otp(user['email'], otp)
    send_sms_otp(user['phone_number'], otp)
    
    prompt = "You have just sent an OTP to the user's email and phone. Inform them of this and ask them to enter the 6-digit code they received."
    message = get_llm_reply(prompt)
    return jsonify({"message": message})
    
@app.route('/check_account_status', methods=['POST'])
def check_account_status():
    user_id = request.json.get('user_id')
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT status FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
    if user: return jsonify({"user_id": user_id, "status": user['status']})
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
    app.run(port=5000, debug=True, threaded=True)

