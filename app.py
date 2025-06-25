import os
import google.generativeai as genai
from flask import Flask, request, render_template, session

app = Flask(__name__)

# Set secret key from environment variable
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set for Flask application")

# Configure Gemini API
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
except (AttributeError, ValueError) as e:
    print(f"Gemini API Key error: {e}")
    model = None

# This is the bot's core "personality"
SYSTEM_INSTRUCTION = """
You are a 'Visual How-To' assistant. Your goal is to provide instructions that are exceptionally clear, visually appealing, and easy to understand at a glance. When a user asks how to do something, you must format your response using Markdown with the following strict structure:

1.  **Main Title:** Start with a clear, bold title for the task, using a relevant emoji. For example: "🍳 **How to Make a Perfect Omelette**".

2.  **Summary:** Provide a brief, one-sentence summary of the task.

3.  **Ingredients/Tools Section:** Use the heading "📋 **What You'll Need**". List each item on a new line starting with a bullet point (`*`) and making the item name **bold**.

4.  **Instructions Section:** Use the heading "📝 **Step-by-Step Guide**". List each step using **numbers** and **bold** the key action of each step.

5.  **Pro-Tip Section:** Use the heading "💡 **Pro-Tip**". Provide one useful, optional tip.

Ensure there is a blank line between each section to create clear visual separation.
"""

@app.route("/")
def home():
    # Clear session history when the user lands on the page for the first time
    session.clear()
    return render_template("index.html")

@app.route("/new-chat", methods=['GET'])
def new_chat():
    # Endpoint to clear the session for the "New Chat" button
    session.clear()
    return "Session cleared", 200

@app.route("/chat", methods=["POST"])
def chat():
    if model is None:
        return {"response": "Error: The application is not configured correctly. Missing API Key."}, 500

    user_message = request.json.get("message")
    if not user_message:
        return {"response": "Error: No message received."}, 400

    # We will use the session to store history for potential follow-up questions
    chat_history = session.get('history', [])
    
    # We create a self-contained prompt for this model version
    prompt = f"{SYSTEM_INSTRUCTION}\n\nUser Question: {user_message}"

    try:
        response = model.generate_content(prompt)
        # We don't need to save history for this simple one-shot model, but the structure is here if we want to
        return {"response": response.text}
    
    except Exception as e:
        print(f"An error occurred during API call: {e}")
        return {"response": "Sorry, I encountered an error. Please try again later."}, 500