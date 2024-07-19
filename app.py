from flask import Flask, render_template, session, redirect, request, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
import os
from itsdangerous import URLSafeTimedSerializer
from flask_migrate import Migrate
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

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

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')
