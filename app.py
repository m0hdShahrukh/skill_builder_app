import os
import json
import uuid
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timezone

# --- All initialization code is the same ---
app = Flask(__name__)
# ... (rest of the initialization for Flask, Firebase, and Gemini)
# Make sure your full initialization block from the last step is here.
# For clarity, here is the full block:
app_secret_key = os.environ.get('SECRET_KEY')
if not app_secret_key:
    raise ValueError("No SECRET_KEY set for Flask application.")
app.config['SECRET_KEY'] = app_secret_key

try:
    creds_json_str = os.environ.get('FIREBASE_CREDS_JSON')
    creds_dict = json.loads(creds_json_str)
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase Admin SDK: {e}")
    db = None

try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini model initialized successfully.")
except Exception as e:
    print(f"Gemini API Key error: {e}")
    model = None


# --- Helper function is the same ---
def get_user_id_from_token(request):
    # ... (same function as before)
    id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    if not id_token:
        return None, ({"error": "Authorization token not provided."}, 401)
    try:
        return auth.verify_id_token(id_token)['uid'], None
    except Exception as e:
        return None, ({"error": f"Invalid token: {e}"}, 401)


# --- API Endpoints ---
@app.route("/")
def home():
    return render_template("index.html")

# <<< --- THIS IS THE TEMPORARY CHANGE --- >>>
@app.route("/api/get-recent-chats", methods=['GET'])
def get_recent_chats():
    """Gets a list of all chats for the logged-in user."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]
    
    # We are temporarily removing the .order_by() clause to test the query
    print(f"DEBUG: Getting chats for user {uid} without sorting.")
    chats_ref = db.collection('chats').where('userId', '==', uid).limit(20)
    
    try:
        chats = [{"id": doc.id, "title": doc.to_dict().get("title", "Untitled")} for doc in chats_ref.stream()]
        print(f"DEBUG: Found {len(chats)} chats.")
        return jsonify(chats)
    except Exception as e:
        # This will print the REAL database error to your Render logs
        print(f"DATABASE QUERY FAILED: {e}")
        return jsonify({"error": "Failed to query database."}), 500

# --- The rest of your API endpoints are the same ---
@app.route("/api/new-chat", methods=['POST'])
def new_chat():
    # ... (same as before)
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]
    chat_id = str(uuid.uuid4())
    chat_data = {
        "userId": uid,
        "title": "New Chat",
        "createdAt": datetime.now(timezone.utc),
        "messages": []
    }
    db.collection('chats').document(chat_id).set(chat_data)
    return jsonify({"chatId": chat_id, "title": "New Chat"})

# ... (include the rest of your routes: /api/get-chat/, /api/chat, etc.)
# It is critical that the rest of the file is identical to the last one I sent.