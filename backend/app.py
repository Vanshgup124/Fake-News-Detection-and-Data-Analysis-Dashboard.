from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import re
import csv
import os
from collections import Counter

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

@app.route('/fake_sources', methods=['GET'])
def get_fake_sources():
    try:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'data.csv')
        fake_sources = Counter()
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # '0' represents fake news based on the data schema
                if row.get('label') == '0':
                    domain = row.get('source_domain', '').strip()
                    if domain and domain.lower() != 'na':
                        fake_sources[domain] += 1
                        
        top_10 = fake_sources.most_common(10)
        return jsonify({
            'success': True,
            'top_sources': [{'domain': domain, 'count': count} for domain, count in top_10]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)