from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import requests
import uuid

API_BASE = "http://127.0.0.1:5000"

class TicketState(TypedDict):
    ticket_id: str
    user_id: str
    account_status: str
    message: str
    action_log: List[str]

def chatbot_input(state: TicketState):
    return {
        **state,
        "ticket_id": f"T-{uuid.uuid4().hex[:6].upper()}",
        "action_log": ["Ticket initiated."]
    }

def check_status(state: TicketState):
    resp = requests.post(f"{API_BASE}/check_account_status", json={"user_id": state["user_id"]})
    status = resp.json().get("status", "error")
    msg = f"Account status: {status}"
    return {
        **state,
        "account_status": status,
        "message": msg,
        "action_log": state["action_log"] + [msg]
    }

def send_otp(state: TicketState):
    requests.post(f"{API_BASE}/send_otp", json={"user_id": state["user_id"]})
    return {
        **state,
        "message": "OTP sent to your email/phone. Please enter it.",
        "action_log": state["action_log"] + ["OTP sent."]
    }

def notify(state: TicketState):
    if state["account_status"] == "active":
        msg = "Your account is already active."
    else:
        msg = "Account unlocked successfully."
    return {**state, "message": msg}

def escalate(state: TicketState):
    requests.post(f"{API_BASE}/create_escalation_ticket", json={
        "user_id": state["user_id"],
        "issue": "System error during unlock"
    })
    return {
        **state,
        "message": "Your issue has been escalated to IT support.",
        "action_log": state["action_log"] + ["Escalated."]
    }

def route_after_check(state: TicketState):
    if state["account_status"] == "locked":
        return "send_otp"
    elif state["account_status"] == "active":
        return "notify"
    else:
        return "escalate"

def build_workflow():
    wf = StateGraph(TicketState)
    wf.add_node("chatbot_input", chatbot_input)
    wf.add_node("check_status", check_status)
    wf.add_node("send_otp", send_otp)
    wf.add_node("notify", notify)
    wf.add_node("escalate", escalate)

    wf.set_entry_point("chatbot_input")
    wf.add_edge("chatbot_input", "check_status")
    wf.add_conditional_edges("check_status", route_after_check, {
        "send_otp": "send_otp",
        "notify": "notify",
        "escalate": "escalate"
    })
    wf.add_edge("send_otp", END)
    wf.add_edge("notify", END)
    wf.add_edge("escalate", END)
    return wf.compile()