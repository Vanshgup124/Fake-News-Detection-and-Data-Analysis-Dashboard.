import streamlit as st
import pandas as pd
import plotly.express as px
import pickle
import re
import os
import numpy as np
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import nltk
from nltk.corpus import stopwords as nltk_stopwords

# Page Config
st.set_page_config(page_title="TruthLens Analyzer", page_icon="🛡️", layout="wide")

# Ensure stop words are downloaded quietly
try:
    nltk.download('stopwords', quiet=True)
except:
    pass

@st.cache_resource
def load_models():
    model_path = os.path.join("backend", "model.pkl")
    vectorizer_path = os.path.join("backend", "vectorizer.pkl")
    model = pickle.load(open(model_path, 'rb'))
    vectorizer = pickle.load(open(vectorizer_path, 'rb'))
    return model, vectorizer

@st.cache_data
def load_and_prep_data():
    data_path = os.path.join("data", "data.csv")
    df = pd.read_csv(data_path)
    
    stopwords = set(STOPWORDS)
    try:
        stopwords.update(nltk_stopwords.words('english'))
    except:
        pass
    stopwords.update(['said','say','says', 'will', 'one', 'new', 'year', 'see'])
    
    def clean_text(text):
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'[^a-zA-Z ]', '', text)
        words = text.split()
        words = [w for w in words if w not in stopwords and len(w) > 2]
        return " ".join(words)
        
    df['clean_title'] = df['title'].apply(clean_text)
    
    analyzer = SentimentIntensityAnalyzer()
    df['sentiment'] = df['title'].apply(lambda x: analyzer.polarity_scores(str(x))['compound'] if pd.notnull(x) else 0)
    
    fake_df = df[df['label'] == 0]
    domains = fake_df['source_domain'].dropna().astype(str).str.strip().str.lower()
    domains = domains[domains != 'na']
    fake_sources_count = Counter(domains).most_common(10)
    
    # Pre-compute vectorized dataset for Similar Articles
    model, vectorizer = load_models()
    vectorized_df = vectorizer.transform(df['clean_title'].fillna(''))
    
    return df, fake_sources_count, vectorized_df

model, vectorizer = load_models()
df, notorious_sources, vectorized_df = load_and_prep_data()

# Try obtaining feature names for explainability
try:
    feature_names = vectorizer.get_feature_names_out()
except:
    try:
        feature_names = vectorizer.get_feature_names()
    except:
        feature_names = None

def scrape_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        html = requests.get(url, timeout=5, headers=headers).text
        soup = BeautifulSoup(html, 'html.parser')
        paragraphs = soup.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs])
        if len(content.strip()) < 50:
            content = soup.title.string if soup.title else ""
        return content
    except Exception as e:
        return ""

def predict_text(text):
    original_text = text
    text = text.lower()
    text = re.sub(r'[^a-zA-Z ]', '', text)
    vec = vectorizer.transform([text])
    prediction = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0].max()
    is_real = (prediction == 1)
    
    # 1. Similarity
    sim = cosine_similarity(vec, vectorized_df)[0]
    top_indices = sim.argsort()[-3:][::-1]
    similar_records = df.iloc[top_indices]
    similar_articles = []
    for idx, row in similar_records.iterrows():
        if sim[idx] > 0.05:  # lowered threshold so something almost always shows
            similar_articles.append({
                'title': row['title'],
                'label': 'REAL' if row['label'] == 1 else 'FAKE',
                'score': sim[idx]
            })
            
    # 2. Explainability
    explanation_df = None
    if feature_names is not None and hasattr(model, 'coef_'):
        non_zero_idx = vec.nonzero()[1]
        words = []
        scores = []
        for idx in non_zero_idx:
            word = feature_names[idx]
            score = model.coef_[0][idx] * vec[0, idx]
            words.append(word)
            scores.append(score)
        
        if words:
            explanation_df = pd.DataFrame({'Word': words, 'Impact': scores})
            # Sort by absolute impact
            explanation_df['AbsImpact'] = explanation_df['Impact'].abs()
            explanation_df = explanation_df.sort_values(by='AbsImpact', ascending=False).head(10)
            
    # 3. Sentiment Breakdown
    analyzer = SentimentIntensityAnalyzer()
    sentiment_scores = analyzer.polarity_scores(original_text)
    comp = sentiment_scores['compound']
    if comp >= 0.05:
        sentiment_label = "Positive"
        sentiment_color = "green"
    elif comp <= -0.05:
        sentiment_label = "Negative"
        sentiment_color = "red"
    else:
        sentiment_label = "Neutral"
        sentiment_color = "gray"
            
    return {
        'prediction': 'REAL' if is_real else 'FAKE',
        'confidence': round(float(prob), 2),
        'similar_articles': similar_articles,
        'explanation_df': explanation_df,
        'sentiment_label': sentiment_label,
        'sentiment_score': comp,
        'sentiment_color': sentiment_color
    }

@st.cache_data(ttl=600)
def fetch_live_news():
    try:
        rss_url = "https://news.google.com/rss?gl=US&hl=en-US&ceid=US:en"
        response = requests.get(rss_url, timeout=5)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        news_list = []
        for item in items[:10]:
            title = item.find('title').text
            link = item.find('link').text
            news_list.append({"title": title, "link": link})
        return news_list
    except:
        return []

# Title
st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🛡️ TruthLens</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>AI-Powered Fake News Detection & Analysis Ecosystem</p>", unsafe_allow_html=True)
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["🔍 Detection Tool", "📊 Interactive Dashboard", "📡 Live News Radar"])

with tab1:
    st.header("Analyze Article Content")
    
    input_method = st.radio("Choose Input Method:", ("Paste Text", "Paste URL"), horizontal=True)
    
    user_input = ""
    if input_method == "Paste Text":
        user_input = st.text_area("Paste the news article or text you want to verify:", height=150)
    else:
        url_input = st.text_input("Enter Article URL:")
        if url_input:
            with st.spinner("Scraping Article..."):
                user_input = scrape_url(url_input)
                if not user_input:
                    st.error("Could not extract content from the URL. Ensure the link is publicly accessible.")
                else:
                    st.success("Successfully extracted article content!")
                    with st.expander("View Scraped Content"):
                        st.write(user_input[:1000] + "..." if len(user_input) > 1000 else user_input)
    
    if st.button("Verify Authenticity", type="primary", use_container_width=True):
        if user_input.strip() == "":
            st.warning("Please enter some text or a valid URL to analyze.")
        else:
            with st.spinner("Analyzing Truth Metrics..."):
                results = predict_text(user_input)
                
            pred = results['prediction']
            conf = results['confidence']
            
            # Prediction Results
            if pred == "FAKE":
                st.error(f"### 🛑 FAKE NEWS DETECTED\n**Confidence Score: {conf*100}%**")
            else:
                st.success(f"### ✅ REAL NEWS DETECTED\n**Confidence Score: {conf*100}%**")

            st.divider()
            colA, colB = st.columns(2)
            
            # Explainability
            with colA:
                st.subheader("Model Thinking (Explainability)")
                if results['explanation_df'] is not None and not results['explanation_df'].empty:
                    exp_df = results['explanation_df']
                    # Color map: Negative Impact -> Fake (Red), Positive Impact -> Real (Green)
                    exp_df['Classification Target'] = exp_df['Impact'].apply(lambda x: 'Pushes towards Real' if x > 0 else 'Pushes towards Fake')
                    fig_exp = px.bar(exp_df, x='Impact', y='Word', orientation='h', color='Classification Target',
                                     color_discrete_map={'Pushes towards Fake': '#ef4444', 'Pushes towards Real': '#10b981'},
                                     title="Most Influential Words")
                    fig_exp.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_exp, use_container_width=True)
                else:
                    st.info("No specific vocabulary significantly influenced the model.")
                    
            # Sentiment & Similar Articles
            with colB:
                st.subheader("Input Profile")
                st.markdown(f"**Text Sentiment:** :{results['sentiment_color']}[{results['sentiment_label']}] (Score: {round(results['sentiment_score'], 2)})")
                
                st.subheader("Similar Database Articles")
                if results['similar_articles']:
                    for art in results['similar_articles']:
                        label_color = "red" if art['label'] == 'FAKE' else "green"
                        st.markdown(f"*{art['title']}* - :{label_color}[**{art['label']}**]")
                else:
                    st.write("No significantly similar articles found in our factual database.")

    st.divider()
    st.subheader("⚠️ Notorious Fake News Sources")
    st.write("Based on our dataset analysis, these sources are the most frequent publishers of fake news.")
    cols = st.columns(5)
    for i, (source, count) in enumerate(notorious_sources):
        with cols[i % 5]:
            st.metric(label=source, value=f"{count} flags", delta="-Unreliable", delta_color="inverse")

with tab2:
    st.header("Interactive Analysis Dashboard")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Overall Distribution")
        pie_data = df['label'].value_counts().reset_index()
        pie_data.columns = ['Classification', 'Count']
        pie_data['Classification'] = pie_data['Classification'].map({0: 'Fake', 1: 'Real'})
        fig_pie = px.pie(pie_data, values='Count', names='Classification', color='Classification', 
                         color_discrete_map={'Fake':'#ef4444', 'Real':'#10b981'}, hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        st.subheader("Top 10 News Sources (Overall)")
        top_sources = df['source_domain'].value_counts().head(10).reset_index()
        top_sources.columns = ['Source Domain', 'Article Count']
        fig_bar = px.bar(top_sources, x='Source Domain', y='Article Count', text='Article Count', color='Article Count', color_continuous_scale='Blues')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.divider()
    st.subheader("Top Words Comparison")
    col3, col4 = st.columns(2)
    fake_text = " ".join(df[df['label'] == 0]['clean_title'].astype(str))
    real_text = " ".join(df[df['label'] == 1]['clean_title'].astype(str))
    
    fake_words_top = pd.DataFrame(Counter(fake_text.split()).most_common(10), columns=['Word', 'Count'])
    real_words_top = pd.DataFrame(Counter(real_text.split()).most_common(10), columns=['Word', 'Count'])
    
    with col3:
        fig_fake_words = px.bar(fake_words_top, x='Word', y='Count', title="Top Words (Fake News)", color_discrete_sequence=['#ef4444'])
        st.plotly_chart(fig_fake_words, use_container_width=True)
    with col4:
        fig_real_words = px.bar(real_words_top, x='Word', y='Count', title="Top Words (Real News)", color_discrete_sequence=['#10b981'])
        st.plotly_chart(fig_real_words, use_container_width=True)
        
    st.divider()
    st.subheader("Sentiment Distribution")
    fig_hist = px.histogram(df, x="sentiment", color="label", nbins=50, 
                            color_discrete_map={0: '#ef4444', 1: '#10b981'},
                            barmode='overlay', opacity=0.7)
    fig_hist.for_each_trace(lambda t: t.update(name = 'Fake' if t.name == '0' else 'Real'))
    st.plotly_chart(fig_hist, use_container_width=True)

with tab3:
    st.header("📡 Live World News Radar")
    st.write("This tab fetches live trending headlines off the web and runs them through your fake news model in real-time.")
    
    if st.button("Refresh Headlines"):
        st.cache_data.clear()
        
    with st.spinner("Fetching global headlines..."):
        news_items = fetch_live_news()
        
    if news_items:
        for item in news_items:
            with st.container():
                st.markdown(f"#### [{item['title']}]({item['link']})")
                res = predict_text(item['title'])
                pred = res['prediction']
                conf = res['confidence']
                
                if pred == "FAKE":
                    st.error(f"🚨 **Classifier Flagged as FAKE** (Confidence: {conf})")
                else:
                    st.success(f"✅ **Classifier Flagged as REAL** (Confidence: {conf})")
                st.divider()
