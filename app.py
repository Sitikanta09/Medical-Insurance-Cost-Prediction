from flask import Flask, render_template, request, redirect, url_for, session
import pickle
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='tempplates')
import os

app.secret_key = os.environ.get("SECRET_KEY", "medicalinsurance123")  # For session management

# In-memory user store (replace with DB in production)
users = {}

# Load the trained model (make sure it's a .pkl file)
with open("model.pkl", "rb") as file:
    model = pickle.load(file)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        users[username] = {'password': password, 'profile': {}}
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    user = users.get(username)
    if user and check_password_hash(user['password'], password):
        session['username'] = username
        return redirect(url_for('profile'))
    return 'Invalid credentials'

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('home'))
    username = session['username']
    if request.method == 'POST':
        profile_data = {
            'age': request.form['age'],
            'bmi': request.form['bmi'],
            'children': request.form['children']
        }
        users[username]['profile'] = profile_data
    return render_template('profile.html', profile=users[username]['profile'])

@app.route('/predict-form')
def predict_form():
    if 'username' not in session:
        return redirect(url_for('home'))
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        age = float(request.form['age'])
        sex = 0 if request.form['sex'] == 'male' else 1
        bmi = float(request.form['bmi'])
        children = int(request.form['children'])
        smoker = 1 if request.form['smoker'] == 'yes' else 0
        region = ['southeast', 'southwest', 'northeast', 'northwest'].index(request.form['region'])

        features = np.array([[age, sex, bmi, children, smoker, region]])
        prediction = model.predict(features)[0]

        return render_template('result.html', prediction_text=f"Estimated Insurance Cost: Rs.{prediction:,.2f}")
    except Exception:
    return render_template(
        "result.html",
        prediction_text="Invalid input. Please enter valid values."
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)