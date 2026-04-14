import streamlit as st
import pandas as pd
import plotly.express as px
import pickle
import re
import os
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
    
    # Text cleaning for word frequency
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
    
    # Calculate sentiment
    analyzer = SentimentIntensityAnalyzer()
    df['sentiment'] = df['title'].apply(lambda x: analyzer.polarity_scores(str(x))['compound'] if pd.notnull(x) else 0)
    
    # Calculate top notorious sources
    # Assuming label 0 is fake based on app.py
    fake_df = df[df['label'] == 0]
    domains = fake_df['source_domain'].dropna().astype(str).str.strip().str.lower()
    domains = domains[domains != 'na']
    fake_sources_count = Counter(domains).most_common(10)
    
    return df, fake_sources_count

model, vectorizer = load_models()
df, notorious_sources = load_and_prep_data()

def predict_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z ]', '', text)
    vec = vectorizer.transform([text])
    prediction = model.predict(vec)[0]
    prob = model.predict_proba(vec)[0].max()
    return ('REAL' if prediction == 1 else 'FAKE', round(float(prob), 2))

# Title
st.markdown("<h1 style='text-align: center; color: #3b82f6;'>🛡️ TruthLens</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>AI-Powered Fake News Detection & Analysis Ecosystem</p>", unsafe_allow_html=True)
st.divider()

# Tabs
tab1, tab2 = st.tabs(["🔍 Detection Tool", "📊 Interactive Dashboard"])

with tab1:
    st.header("Analyze Article Content")
    user_input = st.text_area("Paste the news article or text you want to verify:", height=150)
    
    if st.button("Verify Authenticity", type="primary"):
        if user_input.strip() == "":
            st.warning("Please enter some text to analyze.")
        else:
            with st.spinner("Analyzing..."):
                pred, conf = predict_text(user_input)
                
            if pred == "FAKE":
                st.error(f"**Fake News Detected**\n\nConfidence Score: {conf}")
            else:
                st.success(f"**Real News Detected**\n\nConfidence Score: {conf}")

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
        # Pie Chart
        st.subheader("Overall Distribution")
        pie_data = df['label'].value_counts().reset_index()
        pie_data.columns = ['Classification', 'Count']
        pie_data['Classification'] = pie_data['Classification'].map({0: 'Fake', 1: 'Real'})
        fig_pie = px.pie(pie_data, values='Count', names='Classification', color='Classification', 
                         color_discrete_map={'Fake':'#ef4444', 'Real':'#10b981'}, hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        # Top News Sources Bar Chart
        st.subheader("Top 10 News Sources (Overall)")
        top_sources = df['source_domain'].value_counts().head(10).reset_index()
        top_sources.columns = ['Source Domain', 'Article Count']
        fig_bar = px.bar(top_sources, x='Source Domain', y='Article Count', text='Article Count', color='Article Count', color_continuous_scale='Blues')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.divider()
    
    # Top Words
    st.subheader("Top Words Comparison")
    col3, col4 = st.columns(2)
    
    fake_text = " ".join(df[df['label'] == 0]['clean_title'])
    real_text = " ".join(df[df['label'] == 1]['clean_title'])
    
    fake_words_top = pd.DataFrame(Counter(fake_text.split()).most_common(10), columns=['Word', 'Count'])
    real_words_top = pd.DataFrame(Counter(real_text.split()).most_common(10), columns=['Word', 'Count'])
    
    with col3:
        fig_fake_words = px.bar(fake_words_top, x='Word', y='Count', title="Top Words (Fake News)", color_discrete_sequence=['#ef4444'])
        st.plotly_chart(fig_fake_words, use_container_width=True)
        
    with col4:
        fig_real_words = px.bar(real_words_top, x='Word', y='Count', title="Top Words (Real News)", color_discrete_sequence=['#10b981'])
        st.plotly_chart(fig_real_words, use_container_width=True)
        
    st.divider()
    
    # Sentiment Distribution
    st.subheader("Sentiment Distribution")
    fig_hist = px.histogram(df, x="sentiment", color="label", nbins=50, 
                            color_discrete_map={0: '#ef4444', 1: '#10b981'},
                            barmode='overlay', opacity=0.7)
    # Update legend labels safely
    fig_hist.for_each_trace(lambda t: t.update(name = 'Fake' if t.name == '0' else 'Real'))
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.divider()
    
    # WordClouds
    st.subheader("Word Clouds")
    col5, col6 = st.columns(2)
    
    with col5:
        st.write("**Fake News Word Cloud**")
        wc_fake = WordCloud(width=600, height=300, background_color='rgba(255, 255, 255, 0)', mode="RGBA", colormap="Reds").generate(fake_text)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.imshow(wc_fake, interpolation='bilinear')
        ax.axis("off")
        fig.patch.set_alpha(0.0)
        st.pyplot(fig)
        
    with col6:
        st.write("**Real News Word Cloud**")
        wc_real = WordCloud(width=600, height=300, background_color='rgba(255, 255, 255, 0)', mode="RGBA", colormap="Greens").generate(real_text)
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.imshow(wc_real, interpolation='bilinear')
        ax2.axis("off")
        fig2.patch.set_alpha(0.0)
        st.pyplot(fig2)
