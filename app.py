import os
import json
import uuid
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timezone

# --- All initialization code is correct ---
app = Flask(__name__)
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

# --- Helper function is correct ---
def get_user_id_from_token(request):
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

# <<< --- THIS IS THE RESTORED CODE --- >>>
@app.route("/api/get-recent-chats", methods=['GET'])
def get_recent_chats():
    """Gets a list of all chats for the logged-in user, sorted by date."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]
    
    # We are now restoring the .order_by() clause.
    # Because the index is now correct, this will work.
    chats_ref = db.collection('chats').where('userId', '==', uid).order_by('createdAt', direction=firestore.Query.DESCENDING).limit(20)
    
    try:
        chats = [{"id": doc.id, "title": doc.to_dict().get("title", "Untitled")} for doc in chats_ref.stream()]
        return jsonify(chats)
    except Exception as e:
        print(f"DATABASE QUERY FAILED (with sorting): {e}")
        return jsonify({"error": "Failed to query database."}), 500

# --- The rest of your API endpoints are correct ---
@app.route("/api/new-chat", methods=['POST'])
def new_chat():
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

@app.route("/api/get-chat/<chat_id>", methods=['GET'])
def get_chat(chat_id):
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]

    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if not chat_doc.exists or chat_doc.to_dict().get('userId') != uid:
        return jsonify({"error": "Chat not found or access denied"}), 404
        
    return jsonify(chat_doc.to_dict())

@app.route("/api/chat", methods=["POST"])
def chat():
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]

    data = request.json
    user_message = data.get("message")
    chat_id = data.get("chatId")

    if not all([user_message, chat_id]):
        return jsonify({"error": "Message and chatId are required."}), 400

    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if not chat_doc.exists or chat_doc.to_dict().get('userId') != uid:
        return jsonify({"error": "Chat not found or access denied"}), 404

    prompt = f"User asks: {user_message}"
    try:
        response = model.generate_content(prompt)
        bot_response = response.text
        
        chat_ref.update({
            'messages': firestore.ArrayUnion([
                {"role": "user", "text": user_message},
                {"role": "bot", "text": bot_response}
            ])
        })
        
        messages_count = len(chat_doc.to_dict().get('messages', []))
        if messages_count == 0:
            title_prompt = f"Generate a very short, clever title (4 words max) for a conversation that starts with this user message: '{user_message}'"
            title_response = model.generate_content(title_prompt)
            new_title = title_response.text.strip().replace('"', '')
            chat_ref.update({"title": new_title})
        
        return jsonify({"response": bot_response})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500