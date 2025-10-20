# LangGraph Account Unlock Chatbot

This project is a sophisticated, AI-powered chatbot that helps users unlock their accounts. It uses a LangGraph workflow to manage the state of the conversation, a Flask backend for the application logic, a PostgreSQL database for persistent storage, and an LLM (via OpenRouter) to provide intelligent, conversational responses.

---

## 🚀 Key Features

- **🤖 Intelligent Conversation**: Powered by Mistral 7B via OpenRouter for natural and context-aware interactions.  
- **🧭 Robust Workflow**: Uses LangGraph to manage a clear, multi-step account unlock process.  
- **🔒 Secure Verification**: Implements OTP (One-Time Password) verification via Twilio (SMS) and SendGrid (Email).  
- **💾 Persistent Storage**: Uses a PostgreSQL database to store user and ticket information.  
- **💬 Modern Frontend**: A clean, responsive, and user-friendly chat interface.  
- **🧪 Rich Test Data**: Automatically seeds over 30 realistic fake users for testing.

---

## ⚙️ Final Workflow

1. **Intent Recognition** – The chatbot uses an LLM to detect if the user wants to unlock their account.  
2. **User ID Collection** – Asks for and validates the user’s ID.  
3. **User Confirmation** – Requests confirmation before sending sensitive data.  
4. **OTP Verification** – Sends OTP to the registered contact; handles resend and retry logic.  
5. **Resolution & Notification** – Unlocks the account and sends a personalized message.  
6. **Escalation** – After 3 failed OTP attempts, the issue is automatically escalated.

---

## 📁 Folder Structure

```
/langgraph-account-unlock/
|-- templates/
|   |-- index.html        # Frontend UI
|-- .env                  # Secret API keys (DO NOT COMMIT)
|-- .gitignore            # Ignore sensitive files
|-- Procfile              # Production server command (e.g., Render)
|-- app.py                # Flask application and chat logic
|-- database.py           # PostgreSQL connection and seeding logic
|-- requirements.txt      # Python dependencies
|-- services.py           # Twilio and SendGrid logic
|-- workflow.py           # LangGraph workflow definition
```

---

## 🧩 Setup Instructions

### 1. Environment Variables

Create a `.env` file in the project root and include the following:

```
DATABASE_URL=postgresql://username:password@localhost:5432/langgraph_chatbot
OPENROUTER_API_KEY=your_openrouter_api_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
SENDGRID_API_KEY=your_sendgrid_api_key
```

---

### 2. Local Development

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Initialize Database

Ensure your `DATABASE_URL` in `.env` points to your PostgreSQL instance. Then run:

```bash
python database.py
```

#### Run the Application

```bash
python app.py
```

---

## 🧠 Technologies Used

- **Flask** – Backend framework  
- **LangGraph** – Workflow orchestration  
- **PostgreSQL** – Persistent database  
- **OpenRouter (Mistral 7B)** – AI model integration  
- **Twilio / SendGrid** – OTP verification  
- **HTML / CSS / JS** – Frontend interface  

---

## 🧰 Future Enhancements

- Add user authentication for admins  
- Integrate multi-language support  
- Add analytics for failed unlock attempts  

---

## 👨‍💻 Author

**Basi Lakshman Reddy**  
📍 Jangareddigudem, Andhra Pradesh  
🔗 [GitHub](https://github.com/LakshmanReddyBasi)

---

### 🪪 License

This project is open-source and available under the **MIT License**.
