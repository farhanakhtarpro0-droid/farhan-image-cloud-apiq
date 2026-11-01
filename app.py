from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import random
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

app = Flask(__name__)
CORS(app)

# Render के Environment Variables से Firebase JSON रीड करना
firebase_cert = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
if firebase_cert:
    cert_dict = json.loads(firebase_cert)
    cred = credentials.Certificate(cert_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("WARNING: Firebase Service Account not found!")

# आपकी 3 ImgBB API Keys
IMGBB_API_KEYS = [
    "7d974ca9c76123718ec713f80f339023",
    "2ef39e0982bbdea406538c9922028b9f",
    "3b71855b5a8274e884c959cdfced67e5"
]

@app.route('/')
def home():
    return "Farhan Image Cloud API is Running!"

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
        
    image_file = request.files['image']
    custom_api_key = request.form.get('api_key')
    user_id = None

    # अगर यूजर ने API key दी है, तो फायरबेस से चेक करें
    if custom_api_key:
        users_ref = db.collection('users').where('api_key', '==', custom_api_key).stream()
        user_doc = None
        for doc in users_ref:
            user_doc = doc
            break
            
        if not user_doc:
            return jsonify({"error": "Invalid API Key"}), 401
        user_id = user_doc.id

    # रैंडम ImgBB API Key चुनें
    active_imgbb_key = random.choice(IMGBB_API_KEYS)
    
    try:
        # ImgBB पर फोटो अपलोड करना
        url = f"https://api.imgbb.com/1/upload?key={active_imgbb_key}"
        files = {'image': (image_file.filename, image_file.read(), image_file.mimetype)}
        response = requests.post(url, files=files)
        result = response.json()
        
        if result.get('success'):
            image_url = result['data']['url']
            
            # अगर यूजर लॉगिन है, तो फायरबेस में रिकॉर्ड सेव करें
            if user_id:
                db.collection('users').document(user_id).collection('uploads').add({
                    'url': image_url,
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
                
            return jsonify({"success": True, "url": image_url})
        else:
            return jsonify({"error": "ImgBB upload failed"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
      
