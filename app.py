import os
import json
import google.generativeai as genai
from flask import Flask, request, render_template, session
import firebase_admin
from firebase_admin import credentials, auth, firestore

# --- Firebase Admin SDK Initialization ---
try:
    # Get the JSON credentials from the environment variable
    creds_json_str = os.environ.get('FIREBASE_CREDS_JSON')
    if not creds_json_str:
        raise ValueError("FIREBASE_CREDS_JSON environment variable not set.")

    creds_dict = json.loads(creds_json_str)
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    db = None

# --- Flask App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

# --- Gemini API Initialization ---
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
except (AttributeError, ValueError) as e:
    print(f"Gemini API Key error: {e}")
    model = None

SYSTEM_INSTRUCTION = """
You are a 'Visual How-To' assistant... 
(Your detailed prompt from the previous step goes here. I've shortened it for brevity.)
"""

@app.route("/")
def home():
    return render_template("index.html")

# This is our new, secure chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    # --- Authentication Check ---
    id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    if not id_token:
        return {"error": "Authorization token not provided."}, 401

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        print(f"Token verification failed: {e}")
        return {"error": "Invalid or expired token."}, 401

    # --- Main Logic ---
    user_message = request.json.get("message")
    if not user_message:
        return {"error": "No message received."}, 400

    # Get chat history from Firestore
    chat_ref = db.collection('chats').document(uid)
    chat_doc = chat_ref.get()

    if chat_doc.exists:
        chat_history = chat_doc.to_dict().get('messages', [])
    else:
        chat_history = []

    prompt = f"{SYSTEM_INSTRUCTION}\n\nUser Question: {user_message}"

    try:
        response = model.generate_content(prompt)
        bot_response = response.text

        # Save new messages to history
        chat_history.append({"role": "user", "text": user_message})
        chat_history.append({"role": "bot", "text": bot_response})

        # Update the document in Firestore
        chat_ref.set({"messages": chat_history}, merge=True)

        return {"response": bot_response}
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        return {"response": "Sorry, an error occurred."}, 500

# New endpoint to fetch history
@app.route("/get-history", methods=['GET'])
def get_history():
    id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    if not id_token:
        return {"error": "Authorization token not provided."}, 401
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        chat_ref = db.collection('chats').document(uid)
        chat_doc = chat_ref.get()
        if chat_doc.exists:
            return {"history": chat_doc.to_dict().get('messages', [])}
        else:
            return {"history": []}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}, 401

@app.route("/new-chat", methods=['GET'])
def new_chat():
    id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    if not id_token: return "Unauthorized", 401
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        # In Phase 3, we will create a NEW chat doc. For now, we just clear the old one.
        db.collection('chats').document(uid).delete()
        return "Session cleared", 200
    except Exception:
        return "Unauthorized", 401