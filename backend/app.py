from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import re

app = Flask(__name__)
CORS(app)  #allows frontend to connect

# Load model and vectorizer
model = pickle.load(open('model.pkl', 'rb'))
vectorizer = pickle.load(open('vectorizer.pkl', 'rb'))

# Clean text (same as training)
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z ]', '', text)
    return text

@app.route('/')
def home():
    return "Fake News Detection API is running 🚀"

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()

        # safer check
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400

        text = data['text']

        # Clean text
        cleaned = clean_text(text)

        # Convert to vector
        vec = vectorizer.transform([cleaned])

        # Predict
        prediction = model.predict(vec)[0]

        # Confidence
        prob = model.predict_proba(vec)[0].max()

        return jsonify({
            'prediction': 'REAL' if prediction == 1 else 'FAKE',
            'confidence': round(float(prob), 2)
        })

    except Exception as e:
        # catch unexpected errors
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)