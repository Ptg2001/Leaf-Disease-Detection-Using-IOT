from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from pymongo import MongoClient
import bcrypt
import requests


app = Flask(__name__)
app.secret_key = 'your auto generated key'

# Connect to MongoDB Atlas
client = MongoClient(
    'mongo db connection string')
db = client.get_database('leaf_disease_detection')
users_collection = db.users
results_collection = db.results


# Homepage
@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))


# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Check if username already exists
        existing_user = users_collection.find_one({'username': request.form['username']})
        if existing_user:
            return 'That username already exists!'

        # Hash the password
        hashed_password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())

        # Store username, email, and hashed password in the database
        users_collection.insert_one({
            'username': request.form['username'],
            'email': request.form['email'],  # Add email field
            'password': hashed_password
        })

        # Set session username
        session['username'] = request.form['username']

        # Redirect to index page after successful registration
        return redirect(url_for('index'))

    return render_template('register.html')


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        existing_user = users_collection.find_one({'username': request.form['username']})

        if existing_user:
            if bcrypt.checkpw(request.form['password'].encode('utf-8'), existing_user['password']):
                session['username'] = request.form['username']
                return redirect(url_for('index'))

            return 'Invalid username/password combination'

        return 'User not found'

    return render_template('login.html')


# Logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# Route to trigger plant disease detection on Raspberry Pi
# Route to trigger plant disease detection on Raspberry Pi
@app.route('/detect_disease', methods=['POST'])
def detect_disease():
    # Ensure the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get the username from the session
    username = session['username']

    # Send request to Raspberry Pi with the username as a query parameter
    pi_url = f'http://IP address of raspberry pi:5000/start_detection?username={username}'
    response = requests.get(pi_url)

    # Handle response from Raspberry Pi
    if response.status_code == 200:
        return redirect(url_for('result'))
    else:
        return 'Failed to trigger plant disease detection.'



@app.route('/result')
def result():
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch all results from the database sorted by timestamp in descending order
    username = session['username']
    user_results = list(results_collection.find({'username': username}).sort('timestamp', -1))  # Convert cursor to list

    # Pass the results to the template for rendering
    return render_template('result.html', username=username, user_results=user_results)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
