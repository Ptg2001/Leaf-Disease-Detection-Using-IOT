import time
import numpy as np
from picamera2 import Picamera2, Preview
from PIL import Image
import tensorflow as tf
from pymongo import MongoClient
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, jsonify, request

app = Flask(__name__)

# Connect to MongoDB Atlas
client = MongoClient(
    'your mongodb connection string')
db = client.get_database('leaf_disease_detection')
results_collection = db.results
users_collection = db.users

# Load the trained model
model_path_h5 = "model.hdf5"
model = tf.keras.models.load_model(model_path_h5)

class_labels = ['Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
                'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy',
                'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_',
                'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy', 'Grape___Black_rot',
                'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy',
                'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy',
                'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy', 'Potato___Early_blight',
                'Potato___Late_blight', 'Potato___healthy', 'Raspberry___healthy', 'Soybean___healthy',
                'Squash___Powdery_mildew', 'Strawberry___Leaf_scorch', 'Strawberry___healthy',
                'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold',
                'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite', 'Tomato___Target_Spot',
                'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 'Tomato___healthy']


# Function to capture an image using PiCamera
def capture_image():
    try:
        picam2 = Picamera2()
        camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)}, lores={"size": (640, 480)},
                                                          display="lores")
        picam2.configure(camera_config)
        picam2.start_preview(Preview.QTGL)
        picam2.start()
        time.sleep(2)
        image_path = 'captured_image.jpg'  # Path to store the captured image
        picam2.capture_file(image_path)
        return image_path
    except Exception as e:
        print("Error capturing image:", e)
        return None


# Function to preprocess the captured image
def preprocess_image(image_path):
    try:
        img = Image.open(image_path)
        img = img.resize((224, 224))  # Resize image to match input size of the model
        img_array = np.array(img, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array
    except Exception as e:
        print("Error preprocessing image:", e)
        return None


# Function to fetch user's email from database
def fetch_user_email(username):
    user = users_collection.find_one({'username': username})
    if user:
        return user['email']
    else:
        return None


# Function to send email notification
def send_email_notification(predicted_class, confidence):
    sender_email = "your email address"
    receiver_email = "user's email address"
    password = "gmail account app password"

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = receiver_email
    message['Subject'] = "Alert!!! Leaf Disease Detected!"  # Subject modified here

    body = f"Leaf disease detected: {predicted_class}\nConfidence: {confidence}"
    message.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = message.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print("Email notification sent successfully.")
    except Exception as e:
        print("Error sending email notification:", e)


# Function to send classification result to MongoDB Atlas
def send_classification_result(predicted_class, confidence, username):
    result_data = {
        'predicted_class': predicted_class,
        'confidence': confidence,
        'username': username
    }
    try:
        results_collection.insert_one(result_data)
        print("Classification result stored successfully.")
    except Exception as e:
        print("Error storing classification result:", e)


@app.route('/start_detection', methods=['GET'])
def continuous_detection():
    # Get the username from the request query parameters
    username = request.args.get('username')

    iteration = 0  # Initialize iteration counter

    while True:
        # Capture image using PiCamera
        image_path = capture_image()
        if image_path is None:
            print('Failed to capture image')
            continue

        # Preprocess the captured image
        img_array = preprocess_image(image_path)
        if img_array is None:
            print('Failed to preprocess image')
            continue

        # Classify the image using the loaded model
        predictions = model.predict(img_array)
        predicted_class_index = np.argmax(predictions)
        predicted_class = class_labels[predicted_class_index]
        confidence = float(predictions[0][predicted_class_index])

        # Send classification result to MongoDB Atlas and email notification to the user
        send_classification_result(predicted_class, confidence, username)
        send_email_notification(predicted_class, confidence)

        # Wait for 5 seconds before capturing the next image
        time.sleep(5)  # Adjust this value as needed


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

