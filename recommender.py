import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from db import get_conn

def build_movie_dataframe(conn):
    query = """
        SELECT movie_id, title, overview, genres
        FROM movies
        WHERE overview IS NOT NULL
    """
    df = pd.read_sql(query, conn)

    df["genres_text"] = df["genres"].apply(
        lambda g: " ".join([x["name"] for x in g]) if g else ""
    )

    df["text"] = df["overview"] + " " + df["genres_text"]
    return df
def build_tfidf_matrix(df):
    tfidf = TfidfVectorizer(
        stop_words="english",
        max_features=5000
    )
    matrix = tfidf.fit_transform(df["text"])
    return tfidf, matrix
def build_user_profile(user_id, df, tfidf_matrix, conn):
    query = """
        SELECT m.movie_id, r.rating
        FROM reviews r
        JOIN movies m ON r.movie_id = m.movie_id
        WHERE r.user_id = %s
    """
    user_movies = pd.read_sql(query, conn, params=(user_id,))

    if user_movies.empty:
        return None

    indices = df.index[df["movie_id"].isin(user_movies["movie_id"])]

    weights = user_movies.set_index("movie_id")["rating"]
    weighted_vectors = []

    for idx in indices:
        movie_id = df.iloc[idx]["movie_id"]
        weight = weights.get(movie_id, 3)
        weighted_vectors.append(tfidf_matrix[idx] * weight)

    user_vector = sum(weighted_vectors) / len(weighted_vectors)
    return user_vector
def recommend_for_user(user_id, conn, top_n=10):
    df = build_movie_dataframe(conn)
    tfidf, matrix = build_tfidf_matrix(df)
    user_vec = build_user_profile(user_id, df, matrix, conn)

    if user_vec is None:
        return []

    similarities = cosine_similarity(user_vec, matrix).flatten()
    df["score"] = similarities

    # Remove already watched
    watched = pd.read_sql(
        "SELECT movie_id FROM diary WHERE user_id=%s",
        conn, params=(user_id,)
    )

    recs = (
        df[~df["movie_id"].isin(watched["movie_id"])]
        .sort_values("score", ascending=False)
        .head(top_n)
    )

    return recs[["movie_id", "title", "score"]]
# recommender.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from db import get_connection


def cinemamaya_recommendations(user_id: int, top_n: int = 12):
    """
    🌌 CINEMAMAYA – Explainable Personalized Movie Recommendations
    """

    conn = get_connection()

    # 1️⃣ User taste profile (diary + watchlist + reviews)
    user_df = pd.read_sql("""
        SELECT DISTINCT m.movie_id, m.title, m.genres, m.overview
        FROM diary d
        JOIN movies m ON m.movie_id = d.movie_id
        WHERE d.user_id = %s

        UNION

        SELECT DISTINCT m.movie_id, m.title, m.genres, m.overview
        FROM watchlist w
        JOIN movies m ON m.movie_id = w.movie_id
        WHERE w.user_id = %s

        UNION

        SELECT DISTINCT m.movie_id, m.title, m.genres, m.overview
        FROM reviews r
        JOIN movies m ON m.movie_id = r.movie_id
        WHERE r.user_id = %s
    """, conn, params=(user_id, user_id, user_id))

    if user_df.empty:
        conn.close()
        return pd.DataFrame()

    # 2️⃣ All movies (include poster_path)
    movies_df = pd.read_sql("""
        SELECT movie_id, tmdb_id, title, genres, overview, poster_path
        FROM movies
    """, conn)

    conn.close()

    # 3️⃣ Feature engineering
    movies_df["text"] = (
        movies_df["overview"].fillna("") + " " +
        movies_df["genres"].fillna("").astype(str)
    )

    user_text = (
        user_df["overview"].fillna("") + " " +
        user_df["genres"].fillna("").astype(str)
    ).str.cat(sep=" ")

    # 4️⃣ TF-IDF similarity
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=5000
    )

    tfidf_movies = vectorizer.fit_transform(movies_df["text"])
    tfidf_user = vectorizer.transform([user_text])

    similarity = cosine_similarity(tfidf_user, tfidf_movies)[0]
    movies_df["score"] = similarity

    # 5️⃣ Remove already seen movies
    seen_ids = set(user_df["movie_id"])
    movies_df = movies_df[~movies_df["movie_id"].isin(seen_ids)]

    if movies_df.empty:
        return pd.DataFrame()

    # 6️⃣ Rank top-N
    top_df = movies_df.sort_values(
        "score", ascending=False
    ).head(top_n).copy()

    # 7️⃣ Explainability (safe + deterministic)
    def explain(row):
        row_genres = str(row["genres"])
        for _, seen in user_df.iterrows():
            seen_genres = str(seen["genres"])
            if any(
                g.strip().lower() in row_genres.lower()
                for g in seen_genres.split(",")
            ):
                return f"Because you liked **{seen['title']}**"
        return "Based on your watch history & preferences"

    top_df["reason"] = top_df.apply(explain, axis=1)

    # 8️⃣ Confidence score (real, not random)
    max_score = top_df["score"].max() or 1.0
    history_strength = min(len(user_df) / 10, 1.0)

    top_df["confidence"] = (
        (top_df["score"] / max_score) * history_strength * 100
    ).round(1)

    # 9️⃣ Correct poster URL
    top_df["poster_url"] = top_df["poster_path"].apply(
        lambda p: f"https://image.tmdb.org/t/p/w500{p}" if p else None
    )

    return top_df[
        [
            "movie_id",
            "tmdb_id",
            "title",
            "poster_url",
            "score",
            "confidence",
            "reason"
        ]
    ]


