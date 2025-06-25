import os
import google.generativeai as genai
from flask import Flask, request, render_template

app = Flask(__name__)

# The SECRET_KEY is still good practice for security, so we leave it.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Configure the Gemini API key
try:
    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
except (AttributeError, ValueError):
    print("Google API Key not configured or is invalid. Please set the GOOGLE_API_KEY environment variable.")
    model = None

# <<< --- THIS IS THE BIG CHANGE --- >>>
# We are giving the bot a new personality and a new set of instructions.
SYSTEM_INSTRUCTION = """
You are a helpful and clear 'How-To' assistant.
When a user asks how to do something (e.g., "how to make an omelette"), your goal is to provide a complete, well-structured, and easy-to-follow set of instructions in a single response.
Format the instructions clearly. Start with a list of necessary "Ingredients" or "Tools," followed by a "Steps" section with a numbered list.
Your tone should be helpful and straightforward. Assume the user wants all the information at once.
"""

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    if model is None:
        return {"response": "Error: The application is not configured correctly. Missing API Key."}, 500

    user_message = request.json["message"]

    # For this new personality, we don't need complex history.
    # We combine the system instruction with the user's question every time.
    # This ensures it always gives a full answer.
    prompt = f"{SYSTEM_INSTRUCTION}\n\nUser Question: {user_message}"

    try:
        # Send the combined prompt to Gemini
        response = model.generate_content(prompt)
        
        return {"response": response.text}
    
    except Exception as e:
        # If there's an error, print it to the logs and inform the user
        print(f"An error occurred: {e}")
        return {"response": "Sorry, I encountered an error while trying to think. Please try again."}, 500