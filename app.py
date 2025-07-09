import os
import json
import uuid
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timezone
# Triggering a new deploy
# --- Initialization ---
app = Flask(__name__)
app_secret_key = os.environ.get('SECRET_KEY')
if not app_secret_key:
    raise ValueError("No SECRET_KEY set for Flask application. Please set it in Render.")
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

# --- AI Personalities Definition ---
AI_PERSONALITIES = {
    "how_to_expert": {
        "name": "How-To Expert",
        "prompt": """
        You are a 'Visual How-To' assistant. Your goal is to provide instructions that are exceptionally clear, visually appealing, and easy to understand at a glance.
        When a user asks how to do something, you must format your response using Markdown with the following strict structure:
        1. Main Title: Start with a clear, bold title for the task, using a relevant emoji.
        2. Summary: Provide a brief, one-sentence summary of the task.
        3. Ingredients/Tools Section: Use the heading "📋 **What You'll Need**". List each item on a new line.
        4. Instructions Section: Use the heading "📝 **Step-by-Step Guide**". List each step using numbers.
        5. Pro-Tip Section: Use the heading "💡 **Pro-Tip**". Provide one useful, optional tip.
        Ensure there is a blank line between each section.
        """
    },
    "social_media_helper": {
        "name": "Social Media Helper",
        "prompt": """
        You are a 'Social Media Helper' AI. Your goal is to assist users with creating content for platforms like Twitter, Instagram, and LinkedIn.
        When a user gives you a topic, generate a few distinct post options for different platforms.
        For each post, include:
        - A platform name (e.g., **Instagram Post:**)
        - Engaging post text.
        - A list of relevant hashtags (e.g., `*#Hashtag1 #Hashtag2*`).
        Format the entire response clearly using Markdown.
        """
    }
}

# --- Helper Function ---
def get_user_id_from_token(request):
    """Verifies Firebase ID token and returns UID."""
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
    """Serves the main index.html file."""
    return render_template("index.html")

@app.route("/api/new-chat", methods=['POST'])
def new_chat():
    """Creates a new, empty chat document in Firestore for the user."""
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

@app.route("/api/get-recent-chats", methods=['GET'])
def get_recent_chats():
    """Gets a list of all chats for the logged-in user."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]
    
    chats_ref = db.collection('chats').where('userId', '==', uid).order_by('createdAt', direction=firestore.Query.DESCENDING).limit(20)
    chats = [{"id": doc.id, "title": doc.to_dict().get("title", "Untitled")} for doc in chats_ref.stream()]
    return jsonify(chats)

@app.route("/api/get-chat/<chat_id>", methods=['GET'])
def get_chat(chat_id):
    """Gets the full message history for a specific chat."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]

    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if not chat_doc.exists or chat_doc.to_dict().get('userId') != uid:
        return jsonify({"error": "Chat not found or access denied"}), 404
        
    return jsonify(chat_doc.to_dict())

@app.route("/api/delete-chat/<chat_id>", methods=['DELETE'])
def delete_chat(chat_id):
    """Deletes a chat document from Firestore."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]

    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if not chat_doc.exists or chat_doc.to_dict().get('userId') != uid:
        return jsonify({"error": "Chat not found or access denied"}), 404

    try:
        chat_ref.delete()
        return jsonify({"success": True, "message": "Chat deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete chat: {e}"}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    """Handles sending a message to a specific chat using a specific AI personality."""
    uid, error = get_user_id_from_token(request)
    if error: return jsonify(error[0]), error[1]

    data = request.json
    user_message = data.get("message")
    chat_id = data.get("chatId")
    model_id = data.get("modelId", "how_to_expert") # Default to how_to_expert

    if not all([user_message, chat_id]):
        return jsonify({"error": "Message and chatId are required."}), 400

    personality = AI_PERSONALITIES.get(model_id, AI_PERSONALITIES["how_to_expert"])
    system_prompt = personality["prompt"]
    prompt = f"{system_prompt}\n\nUser Question: {user_message}"
    
    chat_ref = db.collection('chats').document(chat_id)
    chat_doc = chat_ref.get()

    if not chat_doc.exists or chat_doc.to_dict().get('userId') != uid:
        return jsonify({"error": "Chat not found or access denied"}), 404

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
        return jsonify({"error": f"An error occurred during API call: {e}"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))