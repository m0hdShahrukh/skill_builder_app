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
You are a 'Visual How-To' assistant. Your goal is to provide instructions that are exceptionally clear, visually appealing, and easy to understand at a glance.

When a user asks how to do something, you must format your response using the following strict structure:

1.  **Main Title:** Start with a clear, bold title for the task, using a relevant emoji. For example: "🍳 **How to Make a Perfect Omelette**".

2.  **Summary:** Provide a brief, one-sentence summary of the task. For example: "A quick and delicious guide to a fluffy, perfectly cooked omelette."

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