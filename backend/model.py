import pandas as pd
import re
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Load data
df = pd.read_csv('../data/data.csv')

# Fix column name if needed
df.rename(columns={'lable': 'label'}, inplace=True)

# Drop missing values
df = df.dropna(subset=['title'])

# Clean text
def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z ]', '', text)
    return text

df['clean_title'] = df['title'].apply(clean_text)

# Features & labels
X = df['clean_title']
y = df['label']

# Convert text → numbers
vectorizer = TfidfVectorizer(stop_words='english')
X_vec = vectorizer.fit_transform(X)

# Split data (VERY IMPORTANT)
X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, random_state=42
)

# Train model
model = LogisticRegression()
model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))

# Test sample
sample = ["Breaking: celebrity shocking news revealed"]
sample_clean = clean_text(sample[0])
sample_vec = vectorizer.transform([sample_clean])

print("Prediction:", "REAL" if model.predict(sample_vec)[0] == 1 else "FAKE")

# Save model
pickle.dump(model, open('model.pkl', 'wb'))
pickle.dump(vectorizer, open('vectorizer.pkl', 'wb'))