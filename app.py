import os
import google.generativeai as genai
# We need to add render_template to show the HTML page
from flask import Flask, request, render_template

# Your secret key is now read from the hosting environment
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

model = genai.GenerativeModel('gemini-pro')
app = Flask(__name__)

# This is the NEW part that shows your website's front page
@app.route("/")
def home():
    # This tells Flask to find and show your index.html file
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json["message"]

    # You can simplify the prompt a bit
    chat_session = model.start_chat(history=[])
    prompt = f"""
    You are a friendly 'Skill Builder' coach. The user wants to learn a skill.
    The user just said: "{user_message}"
    Your job is to provide the very next, single, simple step for them.
    Keep your instructions small and encouraging. End by asking them to let you know when they have completed the step.
    """
    response = chat_session.send_message(prompt)

    return {"response": response.text}