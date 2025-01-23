import flask
import streamlit as st
import subprocess

# Start Flask app in the background
flask_process = subprocess.Popen(["python", "app.py"])

# Streamlit interface
st.title("Diabetes Prediction App")
st.write("This is an interactive interface embedding a Flask backend.")

# Embed Flask app using iframe
st.components.v1.iframe("http://127.0.0.1:5001", height=800, scrolling=True)

# Gracefully terminate Flask when Streamlit stops
if st.button("Stop Flask App"):
    flask_process.terminate()
    st.warning("Flask app stopped!")
