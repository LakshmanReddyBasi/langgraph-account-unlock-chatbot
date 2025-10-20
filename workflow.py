# from langgraph.graph import StateGraph, END
# from typing import TypedDict, List, Optional
# import requests
# import uuid

# # The API base URL for the Flask app. Using localhost is fine for Render
# # as the service runs in a container that can resolve this address.
# API_BASE_URL = "http://127.0.0.1:5000"

# class TicketState(TypedDict):
#     """
#     Defines the complete state of an account unlock ticket.
#     This state is managed by LangGraph.
#     """
#     user_id: str
#     action_log: List[str]
    
#     # Fields that are added by graph nodes
#     ticket_id: Optional[str]
#     account_status: Optional[str]
#     resolution_status: Optional[str]
#     verified: Optional[bool]
#     otp_attempts: Optional[int]
#     message: Optional[str]

# # --- Node Definitions ---

# def chatbot_input_node(state: TicketState) -> TicketState:
#     """Initializes the ticket with a unique ID."""
#     return {
#         **state,
#         "ticket_id": state.get('ticket_id', f"T-{uuid.uuid4().hex[:6].upper()}"),
#         "action_log": ["Ticket initiated by user."]
#     }

# def account_status_checker_node(state: TicketState) -> TicketState:
#     """Calls the API to check the user's account status."""
#     response = requests.post(f"{API_BASE_URL}/check_account_status", json={"user_id": state["user_id"]})
#     status = response.json().get("status", "error")
#     return {
#         **state,
#         "account_status": status,
#         "action_log": state["action_log"] + [f"Account status checked: {status}"]
#     }

# def otp_generation_node(state: TicketState) -> TicketState:
#     """Calls the API to send an OTP to the user."""
#     response = requests.post(f"{API_BASE_URL}/send_otp", json={"user_id": state["user_id"]})
#     message = response.json().get("message", "An OTP has been sent.")
#     return {
#         **state,
#         "message": message,
#         "action_log": state["action_log"] + ["OTP generation triggered."]
#     }
    
# def resolution_node(state: TicketState) -> TicketState:
#     """Calls the API to unlock the user's account."""
#     response = requests.post(f"{API_BASE_URL}/unlock_account", json={"user_id": state["user_id"]})
#     status = response.json().get("status", "failure")
#     return {
#         **state,
#         "resolution_status": "unlocked" if status == "success" else "failed",
#         "action_log": state["action_log"] + [f"Account unlock attempt: {status}"]
#     }

# def notification_node(state: TicketState) -> TicketState:
#     """A terminal node for successful resolutions."""
#     return {**state, "action_log": state["action_log"] + ["Workflow finished: Success."]}

# def escalation_node(state: TicketState) -> TicketState:
#     """Calls the API to create an escalation ticket for unresolved issues."""
#     attempts = state.get("otp_attempts", 0)
#     issue = f"OTP verification failed after {attempts} attempts." if attempts > 0 else "Account unlock process failed due to a system error."
    
#     requests.post(f"{API_BASE_URL}/create_escalation_ticket", json={"user_id": state["user_id"], "issue": issue})
    
#     return {
#         **state,
#         "message": "I'm sorry, but after multiple failed attempts, I was unable to unlock your account. For your security, I've escalated this issue to our support team. They will get in touch with you shortly.",
#         "action_log": state["action_log"] + ["Workflow finished: Escalated."]
#     }

# # --- Conditional Edges ---

# def decide_after_status_check(state: TicketState) -> str:
#     """Routes the workflow after checking the account status."""
#     if state.get("verified"):
#         return "resolve"
#     if state["account_status"] == "locked":
#         return "send_otp"
#     else:
#         return "end_flow_early"
        
# def decide_after_resolution(state: TicketState) -> str:
#     """Routes the workflow after the unlock attempt."""
#     if state["resolution_status"] == "unlocked":
#         return "notify"
#     else:
#         return "escalate"

# # --- Graph Definition ---

# def build_workflow():
#     """Builds and compiles the LangGraph state machine."""
#     workflow = StateGraph(TicketState)

#     workflow.add_node("chatbot_input", chatbot_input_node)
#     workflow.add_node("check_status", account_status_checker_node)
#     workflow.add_node("send_otp", otp_generation_node)
#     workflow.add_node("resolve", resolution_node)
#     workflow.add_node("notify", notification_node)
#     workflow.add_node("escalate", escalation_node)

#     workflow.set_entry_point("chatbot_input")
    
#     workflow.add_edge("chatbot_input", "check_status")
    
#     workflow.add_conditional_edges(
#         "check_status",
#         decide_after_status_check,
#         {
#             "send_otp": "send_otp",
#             "resolve": "resolve",
#             "end_flow_early": END
#         }
#     )
    
#     workflow.add_conditional_edges(
#         "resolve",
#         decide_after_resolution,
#         {
#             "notify": "notify",
#             "escalate": "escalate"
#         }
#     )
    
#     # Terminal nodes
#     workflow.add_edge("send_otp", END)
#     workflow.add_edge("notify", END)
#     workflow.add_edge("escalate", END)
    
#     return workflow.compile()
# workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
import requests
import uuid
import os

# Use environment-provided base URL (for Render compatibility)
# Default to localhost for local dev
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

class TicketState(TypedDict):
    user_id: str
    ticket_id: Optional[str]
    action_log: List[str]

def chatbot_input_node(state: TicketState) -> TicketState:
    """Initialize ticket with ID."""
    return {
        **state,
        "ticket_id": f"T-{uuid.uuid4().hex[:6].upper()}",
        "action_log": ["Ticket initiated."]
    }

def send_otp_node(state: TicketState) -> TicketState:
    """Trigger OTP sending via API."""
    try:
        requests.post(f"{API_BASE_URL}/send_otp", json={"user_id": state["user_id"]}, timeout=10)
    except Exception as e:
        print(f"[WORKFLOW] OTP send failed: {e}")
    return {**state, "action_log": state["action_log"] + ["OTP sent via API"]}

def escalate_node(state: TicketState) -> TicketState:
    """Create escalation ticket."""
    issue = "OTP verification failed after multiple attempts."
    try:
        requests.post(
            f"{API_BASE_URL}/create_escalation_ticket",
            json={"user_id": state["user_id"], "issue": issue},
            timeout=10
        )
    except Exception as e:
        print(f"[WORKFLOW] Escalation failed: {e}")
    return {
        **state,
        "action_log": state["action_log"] + ["Escalation ticket created"]
    }

def unlock_node(state: TicketState) -> TicketState:
    """Unlock the account."""
    try:
        requests.post(f"{API_BASE_URL}/unlock_account", json={"user_id": state["user_id"]}, timeout=10)
    except Exception as e:
        print(f"[WORKFLOW] Unlock failed: {e}")
    return {**state, "action_log": state["action_log"] + ["Account unlocked"]}

def build_workflow():
    workflow = StateGraph(TicketState)

    workflow.add_node("start", chatbot_input_node)
    workflow.add_node("send_otp", send_otp_node)
    workflow.add_node("escalate", escalate_node)
    workflow.add_node("unlock", unlock_node)

    workflow.set_entry_point("start")
    workflow.add_edge("start", "send_otp")
    workflow.add_edge("send_otp", END)
    workflow.add_edge("escalate", END)
    workflow.add_edge("unlock", END)

    return workflow.compile()