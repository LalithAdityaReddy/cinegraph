import psycopg2
import pandas as pd
import json

# 1. Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="cinegraph",
    user="lalithadityareddy",
    host="localhost"
)
cur = conn.cursor()

# 2. Load CSV (limit to first 5000 rows)
df = pd.read_csv("movies_metadata.csv", low_memory=False)
df = df.head(5000)

# 3. Helper function to safely parse JSON-like columns
def safe_json(val):
    try:
        if pd.isna(val):
            return None
        return json.loads(val.replace("'", '"'))
    except Exception:
        return None

# 4. Iterate and insert
insert_query = """
INSERT INTO movies (
    movie_id, title, original_title, overview, tagline,
    adult, video, release_date, runtime,
    popularity, vote_average, vote_count,
    original_language, poster_path, homepage,
    budget, revenue,
    genres, production_companies, production_countries, spoken_languages
)
VALUES (%s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s,
        %s, %s, %s, %s)
ON CONFLICT (movie_id) DO NOTHING;
"""

for _, row in df.iterrows():
    try:
        cur.execute(insert_query, (
            int(row["id"]) if pd.notna(row["id"]) else None,
            row["title"],
            row["original_title"],
            row["overview"],
            row["tagline"],
            bool(row["adult"]) if pd.notna(row["adult"]) else False,
            bool(row["video"]) if pd.notna(row["video"]) else False,
            row["release_date"] if pd.notna(row["release_date"]) else None,
            int(row["runtime"]) if pd.notna(row["runtime"]) else None,
            float(row["popularity"]) if pd.notna(row["popularity"]) else None,
            float(row["vote_average"]) if pd.notna(row["vote_average"]) else None,
            int(row["vote_count"]) if pd.notna(row["vote_count"]) else None,
            row["original_language"],
            row["poster_path"],
            row["homepage"],
            int(row["budget"]) if pd.notna(row["budget"]) else None,
            int(row["revenue"]) if pd.notna(row["revenue"]) else None,
            json.dumps(safe_json(row["genres"])),
            json.dumps(safe_json(row["production_companies"])),
            json.dumps(safe_json(row["production_countries"])),
            json.dumps(safe_json(row["spoken_languages"]))
        ))
    except Exception as e:
        print("Skipped row due to error:", e)

# 5. Commit and close
conn.commit()
cur.close()
conn.close()

print("✅ Inserted first 5000 movies successfully")
