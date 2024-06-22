from flask import Flask, render_template, session, redirect, request, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


api_key=os.getenv('OPENAI_API_KEY')
client=OpenAI(api_key=api_key)
# Configuration for email

@app.route('/get-response', methods=['POST'])
def get_response():
    try:
        data = request.json
        user_input = data.get('input', '')
        if not user_input:
            raise ValueError("No input provided")
        
        response_text = generate_response(user_input)
        return jsonify({'response': response_text})
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    user_input = data.get('message', '')

    response = generate_response(user_input)
    
    return jsonify({'reply': response})
def generate_response(user_input):
    try:
        # Create a chat completion using the fine-tuned GPT-3.5 Turbo model
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a bible teacher, simplifying the bible to a level, a new believer can understand, 
                you are to explain concepts from the lens of the bible, you were developed by the Teaching Ministry of  Jesus the Solid Rock Prayer Group,Pasali, Kuje, 
                under the guidance of the Holy Spirit.
                you can converse or continue a conversation in pidgin english, ibo, hausa and yoruba"""},
                {"role": "user", "content": user_input}
            ]
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


# @app.route('/logout')
# @login_required
# def logout():
#    logout_user()
#    flash('Logged out successfully!', 'success')
#    return redirect(url_for('login'))

if __name__=='__main__':
    app.run(debug=True, host='0.0.0.0', port='10000')
