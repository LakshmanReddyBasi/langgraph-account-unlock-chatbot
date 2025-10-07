from workflow import build_workflow, TicketState, otp_verification_node
import threading
import time
from database import create_tables, seed_data
from app import app
import os

def run_flask():
    """Runs the Flask app in a separate thread."""
    create_tables()
    seed_data()
    # Setting use_reloader=False is important for threaded mode
    app.run(port=5000, debug=False, use_reloader=False)

def main():
    """Main function to run the chatbot simulation."""
    print("Starting Flask server in a background thread...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    time.sleep(2)
    
    print("\n--- Account Unlock Chatbot ---")
    print("Type 'quit' to exit.")

    workflow = build_workflow()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'quit':
            break
        
        user_id = "john.doe" 
        
        if "locked" in user_input.lower():
            # Initial state to start the process
            initial_state = {"user_id": user_id}
            
            # Run the graph until it stops (which it will after sending the OTP or if the account is already active)
            state_after_otp_sent = workflow.invoke(initial_state)

            # Check if the flow ended early (e.g., account was already active and a final message is ready)
            if state_after_otp_sent.get('account_status') == 'active':
                 print(f"Chatbot: {state_after_otp_sent.get('message')}")
                 continue 

            print(f"Chatbot: {state_after_otp_sent.get('message')}")

            # Get OTP from user
            otp_from_user = input("You (enter OTP): ")
            
            # Call the verification function to get a result dictionary
            state_after_verification = otp_verification_node(state_after_otp_sent, otp_from_user)
            
            if state_after_verification.get('verified'):
                print("Chatbot: OTP Verified. Unlocking account...")

                final_state = workflow.invoke(state_after_verification)
                print(f"Chatbot: {final_state.get('message')}")
            else:
                print("Chatbot: OTP verification failed.")
                final_state = workflow.invoke(state_after_verification, config={"configurable": {"node": "escalate"}})
                print(f"Chatbot: {final_state.get('message')}")


if __name__ == "__main__":
    main()

