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
    🌌 CINEMAMAYA – v3 (Final)
    Precise, intriguing, explainable recommendations
    """

    import pandas as pd
    import time
    from collections import Counter
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    conn = get_connection()

    # ======================================================
    # 1️⃣ USER SIGNALS (REVIEWS + DIARY)
    # ======================================================
    user_movies = pd.read_sql("""
        SELECT m.movie_id, m.title, m.genres, m.overview, r.rating
        FROM movies m
        JOIN reviews r ON r.movie_id = m.movie_id
        WHERE r.user_id = %s

        UNION

        SELECT m.movie_id, m.title, m.genres, m.overview, 3 AS rating
        FROM diary d
        JOIN movies m ON m.movie_id = d.movie_id
        WHERE d.user_id = %s
    """, conn, params=(user_id, user_id))

    if len(user_movies) < 2:
        conn.close()
        return pd.DataFrame()

    # ======================================================
    # 2️⃣ FRIENDS SIGNAL
    # ======================================================
    friends_movies = pd.read_sql("""
        SELECT DISTINCT m.movie_id
        FROM followers f
        JOIN reviews r ON r.user_id = f.following_id
        JOIN movies m ON m.movie_id = r.movie_id
        WHERE f.follower_id = %s AND r.rating >= 4
    """, conn, params=(user_id,))

    friend_ids = set(friends_movies["movie_id"])

    # ======================================================
    # 3️⃣ ALL MOVIES
    # ======================================================
    movies_df = pd.read_sql("""
        SELECT movie_id, tmdb_id, title, genres, overview, poster_path
        FROM movies
    """, conn)

    conn.close()

    # ======================================================
    # 4️⃣ SAFE GENRE EXTRACTION (FIXED)
    # ======================================================
    def extract_genres(genres):
        if not genres:
            return []

        # JSON-like list of dicts
        if isinstance(genres, list):
            return [
                g.get("name", "").lower()
                for g in genres
                if isinstance(g, dict) and "name" in g
            ]

        text = str(genres).lower()
        bad = {"id", "name", "genre", "genres", "null", "none"}

        tokens = []
        for part in text.replace("{", "").replace("}", "").replace("[", "").replace("]", "").split(","):
            part = part.strip()
            if not part or part.isdigit() or part in bad or len(part) <= 2:
                continue
            tokens.append(part)

        return tokens

    # ======================================================
    # 5️⃣ GENRE AFFINITY (STRONG SIGNAL)
    # ======================================================
    genre_counter = Counter()

    for _, row in user_movies.iterrows():
        weight = row["rating"] if not pd.isna(row["rating"]) else 3
        for g in extract_genres(row["genres"]):
            genre_counter[g] += weight

    if not genre_counter:
        return pd.DataFrame()

    top_genres = dict(genre_counter.most_common(6))

    def genre_score(genres):
        return sum(top_genres.get(g, 0) for g in extract_genres(genres))

    movies_df["genre_score"] = movies_df["genres"].apply(genre_score)

    # ======================================================
    # 6️⃣ CONTENT SIMILARITY (SECONDARY)
    # ======================================================
    movies_df["text"] = (
        movies_df["overview"].fillna("") + " " +
        movies_df["genres"].fillna("").astype(str)
    )

    user_text = " ".join(
        user_movies["overview"].fillna("").astype(str).tolist()
    )

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=4000
    )

    tfidf_movies = vectorizer.fit_transform(movies_df["text"])
    tfidf_user = vectorizer.transform([user_text])

    movies_df["content_score"] = cosine_similarity(
        tfidf_user, tfidf_movies
    )[0]

    # ======================================================
    # 7️⃣ FRIEND BOOST
    # ======================================================
    movies_df["friend_boost"] = movies_df["movie_id"].apply(
        lambda x: 1.25 if x in friend_ids else 1.0
    )

    # ======================================================
    # 8️⃣ FINAL SCORE
    # ======================================================
    movies_df["final_score"] = (
        movies_df["genre_score"] * 2.5 +
        movies_df["content_score"] * 1.2
    ) * movies_df["friend_boost"]

    # Remove already seen
    seen_ids = set(user_movies["movie_id"])
    movies_df = movies_df[~movies_df["movie_id"].isin(seen_ids)]

    if movies_df.empty:
        return pd.DataFrame()

    # ======================================================
    # 9️⃣ REFRESH JITTER (REAL-TIME FEEL)
    # ======================================================
    refresh_seed = int(time.time() // 45)
    movies_df["final_score"] *= (1 + (refresh_seed % 3) * 0.05)

    # ======================================================
    # 🔟 TOP N
    # ======================================================
    top_df = movies_df.sort_values(
        "final_score", ascending=False
    ).head(top_n).copy()

    # ======================================================
    # 1️⃣1️⃣ SMART, NON-REPEATING EXPLANATIONS
    # ======================================================
    used_reasons = set()

    def explain(row):
        for g in extract_genres(row["genres"]):
            if g in top_genres and g not in used_reasons:
                used_reasons.add(g)
                return f"Because you often enjoy **{g.title()}** films"

        if row["movie_id"] in friend_ids and "friends" not in used_reasons:
            used_reasons.add("friends")
            return "Popular among people you follow"

        return " Matches your overall taste profile"

    top_df["reason"] = top_df.apply(explain, axis=1)

    # ======================================================
    # 1️⃣2️⃣ CONFIDENCE SCORE
    # ======================================================
    max_score = top_df["final_score"].max() or 1
    top_df["confidence"] = (
        (top_df["final_score"] / max_score) * 100
    ).round(1)

    # ======================================================
    # 1️⃣3️⃣ POSTER URL
    # ======================================================
    top_df["poster_url"] = top_df["poster_path"].apply(
        lambda p: f"https://image.tmdb.org/t/p/w500{p}" if p else None
    )

    return top_df[
        [
            "movie_id",
            "tmdb_id",
            "title",
            "poster_url",
            "confidence",
            "reason"
        ]
    ]


