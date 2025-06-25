import google.generativeai as genai
from flask import Flask, request

# Put your magic key here
import os
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# This is the robot's brain model
model = genai.GenerativeModel('gemini-pro')

# This creates the robot's body (the Flask app)
app = Flask(__name__)

# This tells the robot what to do when it gets a message
@app.route("/chat", methods=["POST"])
def chat():
    # Get the message from the user
    user_message = request.json["message"]

    # The robot's personality and instructions
    # We start a new chat each time for this simple version
    chat_session = model.start_chat(history=[])
    prompt = f"""
    You are a friendly and encouraging 'Skill Builder' coach.
    Your goal is to help a user learn a new skill.
    The user said: "{user_message}"
    Based on their message, ask what they want to learn or give them the very first, simple step.
    Keep your instructions small and easy.
    """
    response = chat_session.send_message(prompt)

    # Send the robot's answer back
    return {"response": response.text}