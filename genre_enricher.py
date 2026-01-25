import os
import psycopg2
import requests
import json
import time
from psycopg2.extras import RealDictCursor

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

SLEEP_SECONDS = 0.25   # safe rate-limit (≈4 req/sec)

# =============================
# DB CONNECTION
# =============================
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# =============================
# TMDB FETCH
# =============================
def fetch_tmdb_details(tmdb_id):
    r = requests.get(
        f"{TMDB_BASE}/movie/{tmdb_id}",
        params={"api_key": TMDB_API_KEY},
        timeout=10
    )
    if r.status_code != 200:
        return None
    return r.json()

# =============================
# MAIN ENRICHER
# =============================
def enrich_genres():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1️⃣ Fetch movies with empty genres
    cur.execute("""
        SELECT movie_id, tmdb_id
        FROM movies
        WHERE genres = '[]'::jsonb OR genres IS NULL
        ORDER BY popularity DESC
    """)
    movies = cur.fetchall()

    print(f"🎬 Movies to enrich: {len(movies)}")

    updated = 0

    for m in movies:
        tmdb_id = m["tmdb_id"]

        details = fetch_tmdb_details(tmdb_id)
        if not details:
            continue

        genres = details.get("genres", [])
        if not genres:
            continue

        cur.execute("""
            UPDATE movies
            SET genres = %s
            WHERE movie_id = %s
        """, (json.dumps(genres), m["movie_id"]))

        conn.commit()
        updated += 1

        if updated % 25 == 0:
            print(f"✅ Enriched {updated} movies")

        time.sleep(SLEEP_SECONDS)

    cur.close()
    conn.close()

    print(f"\n🎉 Genre enrichment complete: {updated} movies updated.")

# =============================
# RUN
# =============================
if __name__ == "__main__":
    enrich_genres()
