import os
import google.generativeai as genai
from flask import Flask, request, render_template, session

app = Flask(__name__)

# Get the secret key you just created in Render
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Configure the Gemini API key
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    # Use the new, correct model name
    model = genai.GenerativeModel('gemini-1.5-flash')
except AttributeError:
    print("Google API Key not configured. Please set the GOOGLE_API_KEY environment variable.")
    model = None

# This is the initial instruction for the robot. It will start every new conversation this way.
SYSTEM_INSTRUCTION = """
You are a friendly and encouraging 'Skill Builder' coach.
Your goal is to help a user learn a new skill by providing one, very simple, step-by-step instruction at a time.
When the user first states what they want to learn, provide the absolute first, tiny step.
When they indicate they have completed a step, provide the next single step.
Keep your instructions small, clear, and easy to follow. Always end by encouraging them to let you know when they've completed the step.
Do not ask them to find a recipe or look up instructions elsewhere. You are the source of the instructions.
"""

@app.route("/")
def home():
    # Clear the old chat history when the user visits the main page
    session.pop('chat_history', None)
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if model is None:
        return {"response": "Error: The application is not configured correctly. Missing API Key."}, 500

    user_message = request.json["message"]

    # Retrieve the chat history from the user's "notebook" (session)
    chat_history = session.get('chat_history', [])

    # If the history is empty, it's a new chat. Start with the system instruction.
    if not chat_history:
        chat_history.append({'role': 'user', 'parts': [SYSTEM_INSTRUCTION, f"The user wants to learn: {user_message}"]})
    else:
        chat_history.append({'role': 'user', 'parts': [user_message]})
    
    # Start the chat with the full history
    chat_session = model.start_chat(history=chat_history)
    
    # Send the message to Gemini
    try:
        # We only send the last message, as the history is already in the session
        response = chat_session.send_message(user_message)
        
        # Add the bot's response to our history
        chat_history.append({'role': 'model', 'parts': [response.text]})

        # Save the updated history back into the user's "notebook"
        session['chat_history'] = chat_history
        
        return {"response": response.text}
    
    except Exception as e:
        # If there's an error, print it to the logs and inform the user
        print(f"An error occurred: {e}")
        return {"response": "Sorry, I encountered an error while trying to think. Please try again."}, 500