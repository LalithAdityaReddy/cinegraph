# 🎬 CINEGRAPH

CINEGRAPH is a social movie discovery platform that allows users to explore movies, write reviews, follow friends, and receive AI-powered personalized recommendations.

## Features
- Real-time movie search (TMDB API)
- Ratings & reviews
- Personal diary
- Watchlist
- Follow users & view friends’ activity
- "CINEMAMAYA" recommendation engine
- Secure authentication

## Tech Stack
- Frontend: Streamlit
- Backend: Python
- Database: PostgreSQL
- ML: Scikit-learn
- API: TMDB

## Recommendation Engine
CINEMAMAYA uses:
- Genre affinity
- User ratings
- Viewing history
- Friends’ preferences
- TF-IDF + cosine similarity

## Installation
```bash
pip install -r requirements.txt
streamlit run app.py
