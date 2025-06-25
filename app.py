import os
import json
import google.generativeai as genai
from flask import Flask, request, render_template, session
import firebase_admin
from firebase_admin import credentials, auth, firestore

# --- Firebase Admin SDK Initialization ---
# This part is critical for your backend to securely communicate with Firebase
try:
    # Get the JSON credentials from the environment variable on Render
    creds_json_str = os.environ.get('FIREBASE_CREDS_JSON')
    if not creds_json_str:
        raise ValueError("FIREBASE_CREDS_JSON environment variable not set. Please check Render setup.")
    
    creds_dict = json.loads(creds_json_str)
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase Admin SDK: {e}")
    db = None

# --- Flask App Initialization ---
app = Flask(__name__)
# Get the secret key from environment variables
app_secret_key = os.environ.get('SECRET_KEY')
if not app_secret_key:
    raise ValueError("No SECRET_KEY set for Flask application. Please set it in Render.")
app.config['SECRET_KEY'] = app_secret_key

# --- Gemini API Initialization ---
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini API Key error: {e}")
    model = None

# --- BOT's Core Personality ---
SYSTEM_INSTRUCTION = """
You are a 'Visual How-To' assistant. Your goal is to provide instructions that are exceptionally clear, visually appealing, and easy to understand at a glance.

When a user asks how to do something, you must format your response using Markdown with the following strict structure:

1.  **Main Title:** Start with a clear, bold title for the task, using a relevant emoji. For example: "🍳 **How to Make a Perfect Omelette**".

2.  **Summary:** Provide a brief, one-sentence summary of the task.

3.  **Ingredients/Tools Section:**
    * Use the heading "📋 **What You'll Need**".
    * List each item (ingredient or tool) on a new line.
    * Start each item with a bullet point (`*`).
    * Make the name of the item **bold**. For example: `* **2-3 Large Eggs**`

4.  **Instructions Section:**
    * Use the heading "📝 **Step-by-Step Guide**".
    * List each step using **numbers**.
    * **Bold** the key action of each step. For example: `1. **Crack** the eggs into a bowl...`
    * Keep the text for each step concise and clear.

5.  **Pro-Tip Section:**
    * Use the heading "💡 **Pro-Tip**".
    * Provide one useful, optional tip to help the user get an even better result.

Ensure there is a blank line between each section to create clear visual separation. The final output should be clean, structured, and very easy to read.
"""

@app.route("/")
def home():
    return render_template("index.html")

# Helper function to get user ID from token
def get_user_id_from_token(request):
    id_token = request.headers.get('Authorization', '').split('Bearer ')[-1]
    if not id_token:
        return None, ({"error": "Authorization token not provided."}, 401)
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid'], None
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None, ({"error": "Invalid or expired token."}, 401)

@app.route("/chat", methods=["POST"])
def chat():
    uid, error = get_user_id_from_token(request)
    if error: return error

    user_message = request.json.get("message")
    if not user_message: return {"error": "No message received."}, 400
    
    # Use a single document per user for simplicity in this phase
    chat_ref = db.collection('chats').document(uid)
    chat_doc = chat_ref.get()
    
    chat_history = chat_doc.to_dict().get('messages', []) if chat_doc.exists else []
    prompt = f"{SYSTEM_INSTRUCTION}\n\nUser Question: {user_message}"
    
    try:
        response = model.generate_content(prompt)
        bot_response = response.text
        
        chat_history.append({"role": "user", "text": user_message})
        chat_history.append({"role": "bot", "text": bot_response})
        
        chat_ref.set({"messages": chat_history}, merge=True)
        return {"response": bot_response}
    except Exception as e:
        print(f"API call error: {e}")
        return {"response": "Sorry, an error occurred while contacting the AI."}, 500
        
@app.route("/get-history", methods=['GET'])
def get_history():
    uid, error = get_user_id_from_token(request)
    if error: return error
    
    chat_doc = db.collection('chats').document(uid).get()
    if chat_doc.exists:
        return {"history": chat_doc.to_dict().get('messages', [])}
    else:
        return {"history": []}

@app.route("/new-chat", methods=['GET'])
def new_chat():
    uid, error = get_user_id_from_token(request)
    if error: return error
    
    # In Phase 3, this will create a new chat entry. For now, it deletes the one chat history doc.
    db.collection('chats').document(uid).delete()
    return "Session cleared", 200