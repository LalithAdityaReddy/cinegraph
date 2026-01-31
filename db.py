import psycopg2
import os
import requests
import json
from psycopg2.extras import RealDictCursor
import bcrypt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from requests.exceptions import RequestException


TMDB_API_KEY = os.getenv("TMDB_API_KEY") or "f69949784723a72b59309f686c6c6394"
TMDB_BASE = "https://api.themoviedb.org/3"


# =============================
# PASSWORD UTILITIES
# =============================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )



# =============================
# DB CONNECTION
# =============================
def get_conn():
    return psycopg2.connect(
        dbname="cinegraph",
        user="lalithadityareddy",
        host="localhost"
    )

def get_connection():
    return psycopg2.connect(
        dbname="cinegraph",
        user="lalithadityareddy",
        host="localhost"
    )

# =============================
# TMDB FETCH
# =============================
def fetch_tmdb_movie(tmdb_id):
    try:
        r = requests.get(
            f"{TMDB_BASE}/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY},
            timeout=6
        )
    except requests.exceptions.RequestException:
        return None   # ⛔ NEVER crash Streamlit

    if r.status_code != 200:
        return None

    try:
        return r.json()
    except Exception:
        return None


# =============================
# HOME FEED
# =============================
def fetch_home_feed(category="trending", limit=24, offset=0):
    conn = get_conn()
    cur = conn.cursor()

    if category == "trending":
        cur.execute("""
            SELECT
                m.tmdb_id,
                m.title,
                m.poster_path
            FROM movies m
            LEFT JOIN reviews r ON m.movie_id = r.movie_id
            GROUP BY m.movie_id
            ORDER BY COUNT(r.review_id) DESC, m.popularity DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
    else:
        cur.execute("""
            SELECT
                tmdb_id,
                title,
                poster_path
            FROM movies
            ORDER BY popularity DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "tmdb_id": r[0],
            "title": r[1],
            "poster_url": f"https://image.tmdb.org/t/p/w500{r[2]}" if r[2] else None
        }
        for r in rows
    ]


# =============================
# MOVIE DETAILS (AUTO INSERT)
# =============================
# =============================
# MOVIE DETAILS (AUTO INSERT SAFE)
# =============================
def fetch_movie_details(tmdb_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1️⃣ Check if movie already exists
    cur.execute(
        "SELECT * FROM movies WHERE tmdb_id = %s",
        (tmdb_id,)
    )
    movie = cur.fetchone()

    if movie:
        cur.close()
        conn.close()
        return movie

    # 2️⃣ Fetch from TMDB
    # 2️⃣ Fetch from TMDB (SAFE)
    try:
        tmdb = fetch_tmdb_movie(tmdb_id)
    except Exception:
        tmdb = None

    if not tmdb:
        cur.close()
        conn.close()
        return None


    # ✅ SAFE release_date handling
    release_date = tmdb.get("release_date")
    if not release_date:
        release_date = None   # <-- CRITICAL FIX

    # 3️⃣ Insert safely
    cur.execute("""
        INSERT INTO movies (
            tmdb_id,
            title,
            overview,
            genres,
            poster_path,
            release_date,
            popularity,
            vote_average,
            vote_count
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (tmdb_id) DO NOTHING
    """, (
        tmdb["id"],
        tmdb.get("title"),
        tmdb.get("overview"),
        json.dumps(tmdb.get("genres", [])),
        tmdb.get("poster_path"),
        release_date,                 # ✅ safe
        tmdb.get("popularity", 0),
        tmdb.get("vote_average", 0),
        tmdb.get("vote_count", 0)
    ))

    conn.commit()

    # 4️⃣ Fetch again
    cur.execute(
        "SELECT * FROM movies WHERE tmdb_id = %s",
        (tmdb_id,)
    )
    movie = cur.fetchone()

    cur.close()
    conn.close()
    return movie


# =============================
# USERS
# =============================
def fetch_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT user_id, username, role FROM users ORDER BY username")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users

# =============================
# REVIEWS
# =============================
def fetch_movie_reviews(tmdb_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    r.review_id,
                    u.username,
                    r.review_text,
                    r.rating,
                    r.like_count,
                    r.created_at
                FROM reviews r
                JOIN movies m ON m.movie_id = r.movie_id
                JOIN users u ON u.user_id = r.user_id
                WHERE m.tmdb_id = %s
                ORDER BY r.created_at DESC
            """, (tmdb_id,))
            rows = cur.fetchall()

    return [
        {
            "review_id": r[0],
            "username": r[1],
            "review_text": r[2],
            "rating": r[3],
            "like_count": r[4],
            "created_at": r[5]
        }
        for r in rows
    ]


def insert_or_update_review(user_id: int, tmdb_id: int, rating: float, review_text: str):
    """
    Inserts a review if not exists, otherwise updates the existing one.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO reviews (user_id, movie_id, rating, review_text)
        SELECT %s, movie_id, %s, %s
        FROM movies
        WHERE tmdb_id = %s
        ON CONFLICT (user_id, movie_id)
        DO UPDATE SET
            rating = EXCLUDED.rating,
            review_text = EXCLUDED.review_text,
            created_at = NOW()
    """, (user_id, rating, review_text, tmdb_id))

    conn.commit()
    cur.close()
    conn.close()
def fetch_user_review_for_movie(user_id: int, tmdb_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT r.review_id, r.rating, r.review_text
        FROM reviews r
        JOIN movies m ON m.movie_id = r.movie_id
        WHERE r.user_id = %s AND m.tmdb_id = %s
    """, (user_id, tmdb_id))

    review = cur.fetchone()
    cur.close()
    conn.close()
    return review


# =============================
# LIKES
# =============================
def has_liked_review(user_id, review_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1 FROM review_likes
        WHERE user_id=%s AND review_id=%s
    """, (user_id, review_id))
    liked = cur.fetchone() is not None
    cur.close()
    conn.close()
    return liked

def like_review(user_id, review_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO review_likes (user_id, review_id)
        VALUES (%s,%s)
        ON CONFLICT DO NOTHING
    """, (user_id, review_id))
    conn.commit()
    cur.close()
    conn.close()

def unlike_review(user_id, review_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM review_likes
        WHERE user_id=%s AND review_id=%s
    """, (user_id, review_id))
    conn.commit()
    cur.close()
    conn.close()
def fetch_user_diary(user_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    m.tmdb_id,
                    m.title,
                    m.poster_path,
                    d.rating,
                    d.watched_date
                FROM diary d
                JOIN movies m ON m.movie_id = d.movie_id
                WHERE d.user_id = %s
                ORDER BY d.watched_date DESC
            """, (user_id,))
            rows = cur.fetchall()

    return [
        {
            "tmdb_id": r[0],
            "title": r[1],
            "poster_url": f"https://image.tmdb.org/t/p/w500{r[2]}" if r[2] else None,
            "rating": r[3],
            "watched_date": r[4]
        }
        for r in rows
    ]

def fetch_user_watchlist(user_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    m.tmdb_id,
                    m.title,
                    m.poster_path,
                    w.priority
                FROM watchlist w
                JOIN movies m ON m.movie_id = w.movie_id
                WHERE w.user_id = %s
                ORDER BY w.priority ASC
            """, (user_id,))
            rows = cur.fetchall()

    return [
        {
            "tmdb_id": r[0],
            "title": r[1],
            "poster_url": f"https://image.tmdb.org/t/p/w500{r[2]}" if r[2] else None,
            "priority": r[3]
        }
        for r in rows
    ]


def fetch_followers_feed(user_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.username,
                    m.tmdb_id,
                    m.title,
                    m.poster_path,
                    r.rating,
                    r.review_text,
                    r.created_at
                FROM followers f
                JOIN reviews r ON r.user_id = f.following_id
                JOIN users u ON u.user_id = r.user_id
                JOIN movies m ON m.movie_id = r.movie_id
                WHERE f.follower_id = %s
                ORDER BY r.created_at DESC
                LIMIT 50
            """, (user_id,))
            rows = cur.fetchall()

    return [
        {
            "username": r[0],
            "tmdb_id": r[1],
            "title": r[2],
            "poster_url": f"https://image.tmdb.org/t/p/w500{r[3]}" if r[3] else None,
            "rating": r[4],
            "review": r[5],
            "created_at": r[6]
        }
        for r in rows
    ]

def trending_among_friends(user_id: int, limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT m.title, COUNT(*) AS watch_count
        FROM followers f
        JOIN diary d ON f.following_id = d.user_id
        JOIN movies m ON d.movie_id = m.movie_id
        WHERE f.follower_id = %s
        GROUP BY m.title
        ORDER BY watch_count DESC
        LIMIT %s
    """, (user_id, limit))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_user_top_genres(user_id: int):
    """
    Returns top genres watched by a user based on diary entries
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            g->>'name' AS genre,
            COUNT(*) AS freq
        FROM diary d
        JOIN movies m ON d.movie_id = m.movie_id
        JOIN LATERAL jsonb_array_elements(m.genres) g ON TRUE
        WHERE d.user_id = %s
        GROUP BY genre
        ORDER BY freq DESC
        LIMIT 5
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# =============================
# FOLLOW / UNFOLLOW
# =============================

def is_following(follower_id: int, following_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1
        FROM followers
        WHERE follower_id = %s AND following_id = %s
    """, (follower_id, following_id))
    res = cur.fetchone()
    cur.close()
    conn.close()
    return res is not None


def follow_user(follower_id: int, following_id: int):
    if follower_id == following_id:
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO followers (follower_id, following_id)
        VALUES (%s, %s)
        ON CONFLICT DO NOTHING
    """, (follower_id, following_id))
    conn.commit()
    cur.close()
    conn.close()


def unfollow_user(follower_id: int, following_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM followers
        WHERE follower_id = %s AND following_id = %s
    """, (follower_id, following_id))
    conn.commit()
    cur.close()
    conn.close()


def fetch_all_users_except(user_id: int):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT user_id, username
        FROM users
        WHERE user_id != %s
        ORDER BY username
    """, (user_id,))
    users = cur.fetchall()
    cur.close()
    conn.close()
    return users


def is_in_watchlist(user_id: int, tmdb_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM watchlist w
                JOIN movies m ON m.movie_id = w.movie_id
                WHERE w.user_id = %s AND m.tmdb_id = %s
            """, (user_id, tmdb_id))
            return cur.fetchone() is not None


def toggle_watchlist(user_id: int, tmdb_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT movie_id FROM movies WHERE tmdb_id = %s
            """, (tmdb_id,))
            row = cur.fetchone()
            if not row:
                return
            movie_id = row[0]

            cur.execute("""
                DELETE FROM watchlist
                WHERE user_id = %s AND movie_id = %s
            """, (user_id, movie_id))

            if cur.rowcount == 0:
                cur.execute("""
                    INSERT INTO watchlist (user_id, movie_id, priority)
                    VALUES (%s, %s, 3)
                """, (user_id, movie_id))

        conn.commit()
import bcrypt

# =============================
# AUTH HELPERS
def create_user(username: str, email: str, password: str):
    conn = get_connection()
    cur = conn.cursor()

    hashed = hash_password(password)

    try:
        cur.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, 'user')
        """, (username, email, hashed))

        conn.commit()
        return True, "Account created successfully"

    except Exception as e:
        conn.rollback()

        if "users_username_key" in str(e):
            return False, "Username already exists"
        if "users_email_key" in str(e):
            return False, "Email already exists"

        return False, "Something went wrong"

    finally:
        cur.close()
        conn.close()


def authenticate_user(username: str, password: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT user_id, username, password_hash, role
        FROM users
        WHERE username = %s
    """, (username,))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return None

    if verify_password(password, user["password_hash"]):
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"]
        }

    return None
def is_in_diary(user_id: int, tmdb_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM diary d
                JOIN movies m ON m.movie_id = d.movie_id
                WHERE d.user_id = %s AND m.tmdb_id = %s
            """, (user_id, tmdb_id))
            return cur.fetchone() is not None
def toggle_diary(user_id: int, tmdb_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:

            # check existing
            cur.execute("""
                SELECT d.diary_id
                FROM diary d
                JOIN movies m ON m.movie_id = d.movie_id
                WHERE d.user_id = %s AND m.tmdb_id = %s
            """, (user_id, tmdb_id))

            row = cur.fetchone()

            if row:
                # REMOVE
                cur.execute(
                    "DELETE FROM diary WHERE diary_id = %s",
                    (row[0],)
                )
            else:
                # ADD
                cur.execute("""
                    INSERT INTO diary (user_id, movie_id, watched_date)
                    SELECT %s, movie_id, CURRENT_DATE
                    FROM movies
                    WHERE tmdb_id = %s
                """, (user_id, tmdb_id))
def search_tmdb_movies(query: str, page: int = 1, limit: int = 20):
    if not query or len(query.strip()) < 3:
        return []

    try:
        r = requests.get(
            f"{TMDB_BASE}/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": query,
                "page": page
            },
            timeout=6
        )
    except RequestException:
        return []

    if r.status_code != 200:
        return []

    try:
        data = r.json().get("results", [])
    except Exception:
        return []

    movies = []
    for m in data[:limit]:
        movies.append({
            "tmdb_id": m.get("id"),
            "title": m.get("title", ""),
            "poster_url": (
                f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                if m.get("poster_path") else None
            )
        })

    return movies



def search_tmdb_suggestions(query: str, limit: int = 6):
    if not query or len(query.strip()) < 3:
        return []

    try:
        r = requests.get(
            f"{TMDB_BASE}/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": query,
                "page": 1
            },
            timeout=6   # ⬅ reduce timeout
        )
    except RequestException as e:
        # 🔇 silent fail (do NOT crash Streamlit)
        return []

    if r.status_code != 200:
        return []

    try:
        results = r.json().get("results", [])[:limit]
    except Exception:
        return []

    return [
        {
            "tmdb_id": m.get("id"),
            "title": m.get("title", ""),
            "year": (m.get("release_date") or "")[:4]
        }
        for m in results
    ]
def fetch_user_ratings(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT rating
        FROM reviews
        WHERE user_id = %s
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]
def fetch_diary_activity(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT watched_date, COUNT(*)
        FROM diary
        WHERE user_id = %s
        GROUP BY watched_date
        ORDER BY watched_date
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
def fetch_user_activity_counts(user_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM reviews WHERE user_id=%s", (user_id,))
    reviews = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM diary WHERE user_id=%s", (user_id,))
    diary = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM watchlist WHERE user_id=%s", (user_id,))
    watchlist = cur.fetchone()[0]

    cur.close()
    conn.close()
    return reviews, diary, watchlist







