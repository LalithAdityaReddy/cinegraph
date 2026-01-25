import os
import psycopg2
import requests
import json
from psycopg2.extras import execute_batch

# =============================
# CONFIG
# =============================
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or "f69949784723a72b59309f686c6c6394"
TMDB_BASE = "https://api.themoviedb.org/3"

DB_CONFIG = {
    "dbname": "cinegraph",
    "user": "lalithadityareddy",
    "host": "localhost"
}

TOTAL_MOVIES = 1000
MOVIES_PER_PAGE = 20
TOTAL_PAGES = TOTAL_MOVIES // MOVIES_PER_PAGE  # 50 pages

# =============================
# DB CONNECTION
# =============================
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# =============================
# TMDB FETCH
# =============================
def fetch_popular_movies(page):
    r = requests.get(
        f"{TMDB_BASE}/movie/popular",
        params={
            "api_key": TMDB_API_KEY,
            "page": page
        },
        timeout=15
    )
    if r.status_code != 200:
        raise RuntimeError(f"TMDB error on page {page}")
    return r.json()["results"]

# =============================
# MAIN SEEDER
# =============================
def seed_movies():
    conn = get_connection()
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO movies (
            tmdb_id, title, original_title, overview,
            genres, poster_path, release_date,
            popularity, vote_average, vote_count
        )
        VALUES (
            %(tmdb_id)s, %(title)s, %(original_title)s, %(overview)s,
            %(genres)s, %(poster_path)s, %(release_date)s,
            %(popularity)s, %(vote_average)s, %(vote_count)s
        )
        ON CONFLICT (tmdb_id) DO NOTHING
    """

    total_inserted = 0

    for page in range(1, TOTAL_PAGES + 1):
        print(f"📥 Fetching page {page}/{TOTAL_PAGES}...")
        movies = fetch_popular_movies(page)

        batch = []
        for m in movies:
            batch.append({
    "tmdb_id": m["id"],
    "title": m["title"],
    "original_title": m.get("original_title"),
    "overview": m.get("overview"),
    "genres": json.dumps([]),  # fill later
    "poster_path": m.get("poster_path"),
    "release_date": m["release_date"] if m.get("release_date") else None,
    "popularity": m.get("popularity"),
    "vote_average": m.get("vote_average"),
    "vote_count": m.get("vote_count")
})


        execute_batch(cur, insert_sql, batch)
        conn.commit()
        total_inserted += len(batch)

    cur.close()
    conn.close()

    print(f"\n✅ Seeding complete: {total_inserted} movies processed.")

# =============================
# RUN
# =============================
if __name__ == "__main__":
    seed_movies()
