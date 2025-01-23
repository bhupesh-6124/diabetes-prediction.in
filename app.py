from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_sqlalchemy import SQLAlchemy
import joblib
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import streamlit as st
import subprocess


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_key')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load the trained model
model= joblib.load('diabetes_model.pkl')

# Start Flask app in the background
flask_process = subprocess.Popen(["python", "app.py"])

# Streamlit interface
st.title("Diabetes Prediction App")
st.write("This is an embedded Flask app running in Streamlit.")

# Embed Flask app using iframe
st.components.v1.iframe("http://127.0.0.1:5001", height=800, scrolling=True)

# Gracefully terminate Flask when Streamlit stops
if st.button("Stop Flask App"):
    flask_process.terminate()
    st.warning("Flask app stopped!")


# Initialize the database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        contact TEXT,
        user_id TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()


# Home Page
@app.route('/')
def home():
    if 'user_id' in session:
        return f"""
        <!-- Welcome Text (top-right, smaller size) -->
        <div style="position: absolute; top: 2px; right: 20px; color: #b68d40; font-size: 10px;">
            <h1>Welcome, <strong>{session['user_id']}</strong>!</h1>
        </div>
        
        <!-- Button Box (on the left side) -->
        <div style="border: 2px solid #b68d40; border-radius: 10px; padding: 20px; text-align: center; position: absolute; top: 100px; left: 20px; width: 200px;">
            <a href='/predict'>
                <button style="background-color:#1f77b4; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">
                    Go to Prediction
                </button>
            </a>
        </div>
        """


    return render_template("index.html")


# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        contact = request.form.get('contact')
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # Check required fields
        if not all([name, email, user_id, password]):
            flash('All required fields must be filled!', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        hash_password = generate_password_hash(password)

        try:
            # Save user to database
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO users (name, email, contact, user_id, password)
                VALUES (?, ?, ?, ?, ?)''',
                (name, email, contact, user_id, hash_password)
            )
            conn.commit()
            conn.close()
            flash('Registration Successful! Please Login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('User ID or Email already exists!', 'danger')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')

    return render_template('register.html')


# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        # Retrieve user from database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()

        if user:
            if check_password_hash(user[5], password):  # Check password hash
                session['user_id'] = user_id
                flash('Login Successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid Password!', 'danger')
        else:
            flash('Invalid User ID!', 'danger')

    return render_template('login.html')


# Prediction Page
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if 'user_id' not in session:
        flash('Please login to access this page.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Collect input data
            data = [
                float(request.form['pregnancies']),
                float(request.form['glucose']),
                float(request.form['blood_pressure']),
                float(request.form['skin_thickness']),
                float(request.form['insulin']),
                float(request.form['bmi']),
                float(request.form['dpf']),
                float(request.form['age'])
            ]
            # Get prediction and probabilities
            prediction = model.predict([data])[0]
            probabilities = model.predict_proba([data])[0]

            # Extract probabilities for each class
            diabetic_probability = round(probabilities[1] * 100, 2)
            non_diabetic_probability = round(probabilities[0] * 100, 2)
            result = 'Diabetic' if prediction == 1 else 'Not Diabetic'

            # Store the data in the session for the result page
            session['result'] = result
            session['diabetic_probability'] = diabetic_probability
            session['non_diabetic_probability'] = non_diabetic_probability

            return redirect(url_for('result'))

        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
            return redirect(url_for('predict'))

    return render_template('predict.html')


# Result Page
@app.route('/result')
def result():
    if 'result' not in session:
        flash('No prediction found. Please make a prediction first.', 'warning')
        return redirect(url_for('predict'))

    return render_template(
        'result.html',
        result=session.get('result'),
        diabetic_probability=session.get('diabetic_probability'),
        non_diabetic_probability=session.get('non_diabetic_probability')
    )


# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('home'))



if __name__ == '__main__':
    init_db()
    app.run(debug=False, port=5001)
