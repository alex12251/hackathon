from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import base64
import requests
import os
import json
from werkzeug.utils import secure_filename
from openai import OpenAI

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# A4F API configuration
a4f_api_key = "ddc-a4f-0a91e899b40844f1968ad93283b89a1e"
a4f_base_url = "https://api.a4f.co/v1"

client = OpenAI(
    api_key=a4f_api_key,
    base_url=a4f_base_url,
)

# Directory for uploaded images
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Indian cattle and buffalo breeds database
BREEDS_DATABASE = {
    "sahiwal": {
        "name": "Sahiwal",
        "type": "Cattle",
        "origin": "Punjab region (India/Pakistan)",
        "characteristics": "Reddish dun to brown color, loose skin, hump in males, high milk yield",
        "milk_production": "2000-3000 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Heat tolerant, resistant to ticks and diseases"
    },
    "gir": {
        "name": "Gir",
        "type": "Cattle",
        "origin": "Gujarat, India",
        "characteristics": "Distinctive curved horns, red and white spotted skin, prominent hump",
        "milk_production": "1500-2000 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Well adapted to harsh climates"
    },
    "red_sindhi": {
        "name": "Red Sindhi",
        "type": "Cattle",
        "origin": "Sindh region (Pakistan)",
        "characteristics": "Deep red color, drooping ears, moderate hump",
        "milk_production": "1800-2600 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Heat tolerant, good resistance to diseases"
    },
    "tharparkar": {
        "name": "Tharparkar",
        "type": "Cattle",
        "origin": "Tharparkar district (Pakistan)",
        "characteristics": "White or light gray coat, medium size, lyre-shaped horns",
        "milk_production": "1800-2600 kg per lactation",
        "purpose": "Dual purpose (dairy and draught)",
        "adaptation": "Well suited to arid conditions"
    },
    "jangli_bhains": {
        "name": "Jangli Bhains (Wild Buffalo)",
        "type": "Buffalo",
        "origin": "Assam and other Northeastern states, India",
        "characteristics": "Massive body, large curved horns, dark gray to black skin",
        "milk_production": "Not typically milked",
        "purpose": "Conservation, sometimes used for draught",
        "adaptation": "Well adapted to swampy areas"
    },
    "murrah": {
        "name": "Murrah",
        "type": "Buffalo",
        "origin": "Haryana and Punjab, India",
        "characteristics": "Jet black color, short and tightly curved horns, muscular body",
        "milk_production": "1500-2500 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Adapts well to various climatic conditions"
    },
    "jaffrabadi": {
        "name": "Jaffrabadi",
        "type": "Buffalo",
        "origin": "Gujarat, India",
        "characteristics": "Heavy build, broad forehead, curved horns",
        "milk_production": "2000-3000 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Suitable for hot and humid climates"
    },
    "nili_ravi": {
        "name": "Nili-Ravi",
        "type": "Buffalo",
        "origin": "Punjab region (India/Pakistan)",
        "characteristics": "Black body with white markings on face and legs, wall eyes",
        "milk_production": "1800-2500 kg per lactation",
        "purpose": "Dairy",
        "adaptation": "Good adaptability to different environments"
    }
}

def analyze_image_with_a4f(image_data):
    """Analyze image using A4F API to detect breed and health indicators"""
    try:
        # Convert image to base64 if it's a file path
        if isinstance(image_data, str) and os.path.exists(image_data):
            with open(image_data, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Call A4F API
        completion = client.chat.completions.create(
            model="provider-3/gemini-2.5-flash-image-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this image of Indian cattle or buffalo. Identify the breed if possible from these options: Sahiwal, Gir, Red Sindhi, Tharparkar, Jangli Bhains, Murrah, Jaffrabadi, Nili-Ravi. Also assess the animal's health by looking for signs of illness, injury, or malnutrition. Provide your response in JSON format with these keys: breed (string), confidence (float), health_score (0-100), health_issues (array of strings), and recommendations (array of strings)."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        # Parse the response
        response_text = completion.choices[0].message.content
        # Extract JSON from response (the model might return text with JSON)
        try:
            # Try to parse the entire response as JSON
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the text
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
            else:
                # Fallback if no JSON found
                result = {
                    "breed": "Unknown",
                    "confidence": 0.0,
                    "health_score": 50,
                    "health_issues": ["Could not analyze health"],
                    "recommendations": ["Please consult a veterinarian for accurate assessment"]
                }
        
        return result
        
    except Exception as e:
        print(f"Error analyzing image with A4F: {str(e)}")
        return {
            "breed": "Unknown",
            "confidence": 0.0,
            "health_score": 50,
            "health_issues": ["Analysis error"],
            "recommendations": ["Please try again or consult a veterinarian"]
        }

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    """Endpoint to analyze uploaded cattle/buffalo image"""
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Analyze the image
        analysis_result = analyze_image_with_a4f(filepath)
        
        # Get additional breed information from our database
        breed_key = analysis_result.get('breed', '').lower().replace(' ', '_')
        breed_info = BREEDS_DATABASE.get(breed_key, {})
        
        # Prepare response
        response_data = {
            "breed": analysis_result.get('breed', 'Unknown'),
            "confidence": analysis_result.get('confidence', 0.0),
            "health_score": analysis_result.get('health_score', 50),
            "health_issues": analysis_result.get('health_issues', []),
            "recommendations": analysis_result.get('recommendations', []),
            "breed_info": breed_info
        }
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in analyze_image: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/check-symptoms', methods=['POST'])
def check_symptoms():
    """Endpoint to provide recommendations based on symptoms"""
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', [])
        
        # This is a simplified example - in a real application, you would use
        # a more sophisticated symptom-checking algorithm or database
        
        recommendations = []
        
        if 'lethargy' in symptoms:
            recommendations.append({
                "symptom": "Lethargy/Dullness",
                "condition": "Possible anemia or malnutrition",
                "medicine": "Vitamin B complex supplements and iron tonic"
            })
        
        if 'swelling' in symptoms:
            recommendations.append({
                "symptom": "Swelling in Body Parts",
                "condition": "Inflammation or edema",
                "medicine": "Non-steroidal anti-inflammatory drugs like Meloxicam"
            })
            
        if 'diarrhea' in symptoms:
            recommendations.append({
                "symptom": "Diarrhea/Loose Motion",
                "condition": "Possible parasitic or bacterial infection",
                "medicine": "Oral Rehydration Solution (ORS) and antibiotics if prescribed"
            })
            
        # Add more symptom checks as needed...
        
        return jsonify({"recommendations": recommendations})
        
    except Exception as e:
        print(f"Error in check_symptoms: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/breeds', methods=['GET'])
def get_breeds():
    """Endpoint to get information about all breeds"""
    return jsonify(BREEDS_DATABASE)

if __name__ == '__main__':
    app.run(debug=True, port=5000)