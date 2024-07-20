from flask import Flask, render_template, session, redirect, request, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
import os
from itsdangerous import URLSafeTimedSerializer
from flask_migrate import Migrate
from dotenv import load_dotenv
from openai import OpenAI
import requests
load_dotenv()
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)
VERIFY_TOKEN = 'c07240d75087dfa3a4e856c1eeefcd5a'
# Configuration for email
# Secret key for generating reset tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/get-response', methods=['POST'])
def get_response():
    try:
        data = request.json
        user_input = data.get('input', '')
        if not user_input:
            raise ValueError("No input provided")

        # Retrieve conversation history from session
        conversation_history = session.get('conversation_history', [])

        # Append the new user input to the conversation history
        conversation_history.append({"role": "user", "content": user_input})

        response_text = generate_response(conversation_history)

        # Append the bot response to the conversation history
        conversation_history.append({"role": "assistant", "content": response_text})

        # Save the updated conversation history in session
        session['conversation_history'] = conversation_history

        return jsonify({'response': response_text})
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    user_input = data.get('message', '')

    # Retrieve conversation history from session
    conversation_history = session.get('conversation_history', [])

    # Append the new user input to the conversation history
    conversation_history.append({"role": "user", "content": user_input})

    response = generate_response(conversation_history)

    # Append the bot response to the conversation history
    conversation_history.append({"role": "assistant", "content": response})

    # Save the updated conversation history in session
    session['conversation_history'] = conversation_history

    return jsonify({'reply': response})

def generate_response(conversation_history):
    try:
        # Create a chat completion using the fine-tuned GPT-3.5 Turbo model
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a bible teacher, simplifying the bible to a level, a new believer can understand, 
                you are to explain concepts from the lens of the bible, after initial greetings by the user, you are to ask the user for their name so that you can relate more personally with them,you were developed by bro.Igata John from Teaching Ministry of  Jesus the Solid Rock Prayer Group,Pasali, Kuje, 
                under the guidance of the Holy Spirit.
                """}
            ] + conversation_history
        )

        # Extract the model's response content
        model_response = completion.choices[0].message.content.strip()

        return model_response
    except Exception as e:
        return str(e)

@app.route('/')
def chat():
    return render_template('chat.html')

@app.errorhandler(401)
def unauthorized(error):
    return render_template('unauthorize.html'), 401
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if verify_token == VERIFY_TOKEN:
            return str(challenge)
        return 'Verification token mismatch', 403

    if request.method == 'POST':
        data = request.json
        handle_message(data)
        return jsonify({'status': 'success'})
def handle_message(data):
    try:
        if 'messages' in data['entry'][0]['changes'][0]['value']:
            messages = data['entry'][0]['changes'][0]['value']['messages']
            for message in messages:
                if message['type'] == 'text':
                    user_input = message['text']['body']
                    phone_number = message['from']

                    response_text = generate_response(user_input)
                    send_whatsapp_message(phone_number, response_text)
    except Exception as e:
        print(f"Error handling message: {str(e)}")
    except Exception as e:
        print(f"Error handling message: {str(e)}")
def send_whatsapp_message(phone_number, message_text):
    url = 'https://graph.facebook.com/v19.0/364928576706283/messages'
    headers = {
        'Authorization': f'Bearer {os.getenv("WHATSAPP_API_TOKEN")}',
        'Content-Type': 'application/json'
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': phone_number,
        'type': 'text',
        'text': {
            'body': message_text
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")
if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')
