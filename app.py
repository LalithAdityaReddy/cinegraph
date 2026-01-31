import streamlit as st
from db import (
    fetch_home_feed,
    fetch_movie_details,
    fetch_movie_reviews,
    fetch_users,
    fetch_user_diary,
    fetch_user_watchlist,
    fetch_followers_feed,
    insert_or_update_review,
    fetch_user_review_for_movie,
    has_liked_review,
    like_review,
    unlike_review,
    trending_among_friends,
    get_user_top_genres,
    fetch_user_ratings,       
    fetch_diary_activity,       
    fetch_user_activity_counts   
)
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd 
import numpy as np
import matplotlib.dates as mdates

sns.set_theme(style="darkgrid")
import time
from recommender import cinemamaya_recommendations

from db import fetch_tmdb_movie
from db import search_tmdb_movies

from db import (
    is_following,
    follow_user,
    unfollow_user,
    fetch_all_users_except
)
from db import is_in_diary, toggle_diary
from db import search_tmdb_suggestions


TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="CINEGRAPH",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown("""
<style>

/* ===============================
   GLOBAL THEME (222831 Palette)
   =============================== */

:root {
    --bg-main: #222831;
    --bg-sidebar: #1e2229;
    --bg-card: #31363F;
    --border-soft: #3b414d;

    --text-main: #EEEEEE;
    --text-muted: #BFC3C9;

    --accent: #76ABAE;
}

/* ===============================
   APP BACKGROUND
   =============================== */

.stApp {
    background-color: var(--bg-main);
}

/* ===============================
   SIDEBAR
   =============================== */

section[data-testid="stSidebar"] {
    background-color: var(--bg-sidebar);
    border-right: 1px solid var(--border-soft);
    min-width: 220px;
    max-width: 220px;
}

section[data-testid="stSidebar"] * {
    color: var(--text-main) !important;
    font-weight: 500;
}

section[data-testid="stSidebar"] > div {
    padding-top: 1rem;
}

/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
    background-color: var(--bg-card);
    border: 1px solid var(--border-soft);
    color: var(--text-main);
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 6px;
    width: 100%;
    text-align: left;
}

/* Hover */
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: var(--accent);
    color: #000000;
    border-color: var(--accent);
}

/* Remove icons / arrows */
section[data-testid="stSidebar"] .stButton > button::before,
section[data-testid="stSidebar"] .stButton > button::after,
section[data-testid="stSidebar"] .stButton svg {
    display: none !important;
}

/* ===============================
   MAIN CONTENT
   =============================== */

h1, h2, h3, h4 {
    color: var(--text-main) !important;
}

p, span, label, div {
    color: var(--text-main) !important;
}

small, .stCaption {
    color: var(--text-muted) !important;
}

/* ===============================
   BUTTONS
   =============================== */

.stButton > button {
    background-color: var(--bg-card);
    border: 1px solid var(--border-soft);
    color: var(--text-main);
    border-radius: 10px;
    font-weight: 600;
}

.stButton > button:hover {
    background-color: var(--accent);
    color: #000000;
    border-color: var(--accent);
}

/* ===============================
   INPUTS
   =============================== */

textarea, input {
    background-color: var(--bg-card) !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 10px !important;
}

textarea::placeholder,
input::placeholder {
    color: var(--text-muted) !important;
}

/* ===============================
   MOVIE CARDS
   =============================== */

.movie-card {
    background-color: var(--bg-card);
    border-radius: 14px;
    padding: 10px;
    border: 1px solid var(--border-soft);
    transition: transform 0.2s ease, border-color 0.2s ease;
}

.movie-card:hover {
    transform: translateY(-4px);
    border-color: var(--accent);
}

.movie-title {
    font-weight: 600;
    margin-top: 8px;
    text-align: center;
}

/* ===============================
   DIVIDERS
   =============================== */

hr {
    border-color: var(--border-soft);
}

/* ===============================
   REMOVE STREAMLIT HEADER GAP
   =============================== */

header, .stApp > header {
    height: 0px !important;
    background: transparent !important;
}

.block-container {
    padding-top: 1.5rem !important;
}

</style>
""", unsafe_allow_html=True)


# =============================
# SESSION STATE INITIALIZATION (MUST BE FIRST)
# =============================
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "cinemamaya_refresh" not in st.session_state:
    st.session_state.cinemamaya_refresh = 0

if "view" not in st.session_state:
    st.session_state.view = "login"

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

if "page" not in st.session_state:
    st.session_state.page = 0

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

if "search_page" not in st.session_state:
    st.session_state.search_page = 1


# =============================
# URL → SESSION SYNC (AFTER INIT)
# =============================
params = st.query_params

# if "view" in params and "view" not in st.session_state:
#     st.session_state.view = params.get("view", "home")


if "page" in params:
    st.session_state.page = int(params.get("page", st.session_state.page))

if "tmdb_id" in params:
    st.session_state.selected_tmdb_id = int(params["tmdb_id"])

# if "q" in params and st.session_state.view == "home":
#     st.session_state.search_query = params.get("q", "")


if "sp" in params:
    st.session_state.search_page = int(params.get("sp", 1))

def goto(view, tmdb_id=None, q=None, page=None, sp=None):
    st.session_state.view = view

    # reset search when switching views
    if view != "home":
        st.session_state.search_query = ""

    if tmdb_id is not None:
        st.session_state.selected_tmdb_id = tmdb_id

    if q is not None:
        st.session_state.search_query = q

    if page is not None:
        st.session_state.page = page

    if sp is not None:
        st.session_state.search_page = sp

    st.rerun()

# =============================
# AUTH GUARD
# =============================
# =============================
# AUTH GUARD
# =============================
if (
    st.session_state.current_user is None
    and st.session_state.view not in ["login", "signup", "auth"]
):
    goto("login")


# =============================
# AUTH UI
# =============================
if st.session_state.current_user is None:
    st.title("🔐 CINEGRAPH")

    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    # ---------- LOGIN ----------
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")

        if submit:
            if not username or not password:
                st.warning("Please enter username and password")
            else:
                from db import authenticate_user
                user = authenticate_user(username, password)

                if user:
                    st.session_state.current_user = user
                    goto("home", page=0)
                else:
                    st.error("Invalid username or password")

    # ---------- SIGN UP ----------
    with tab2:
        su_username = st.text_input("Username", key="su_user")
        su_email = st.text_input("Email", key="su_email")
        su_password = st.text_input("Password", type="password", key="su_pwd")
        su_confirm = st.text_input("Confirm Password", type="password", key="su_cpwd")

        if st.button("Create Account"):
            if not all([su_username, su_email, su_password]):
                st.warning("All fields are required")
            elif su_password != su_confirm:
                st.error("Passwords do not match")
            else:
                from db import create_user
                ok, msg = create_user(su_username, su_email, su_password)
                if ok:
                    st.success("Account created. Please login.")
                    goto("login")
                else:
                    st.error(msg)

    st.stop()


# =============================
# UI HELPERS
# =============================
def poster_grid(items, cols=6, show_reason=False):
    if items is None or len(items) == 0:
        st.info("No movies to show.")
        return

    rows = (len(items) + cols - 1) // cols
    idx = 0

    for _ in range(rows):
        colset = st.columns(cols)
        for c in colset:
            if idx >= len(items):
                break

            m = items[idx]
            idx += 1

            with c:
                st.markdown('<div class="movie-card">', unsafe_allow_html=True)

                if m.get("poster_url"):
                    st.image(m["poster_url"], use_column_width=True)
                else:
                    st.write("🖼️ No poster")

                if st.button("Open", key=f"open_{m['tmdb_id']}"):
                    goto("details", m["tmdb_id"])

                st.markdown(
                    f"<div class='movie-title'>{m['title']}</div>",
                    unsafe_allow_html=True
                )

                if show_reason and m.get("reason"):
                    st.caption(f"✨ {m['reason']}")

                st.markdown("</div>", unsafe_allow_html=True)

# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("## 🎬 CINEGRAPH")

    st.markdown(f"👤 **{st.session_state.current_user['username']}**")

    if st.button("Home"):
        goto("home")

    if st.button("My Diary"):
        goto("diary")

    if st.button("My Watchlist"):
        goto("watchlist")

    if st.button("Friends Feed"):
        goto("feed")

    if st.button("Insights"):
        goto("insights")

    if st.button("🌌 CINEMAMAYA"):
        goto("cinemamaya")

    st.markdown("---")

    if st.button("🚪 Logout"):
        st.session_state.current_user = None
        st.rerun()

# =============================
# HEADER
# =============================
st.title("🎬 CINEGRAPH")

if st.session_state.current_user:
    st.success(f"Logged in as {st.session_state.current_user['username']}")
else:
    st.warning("Please select a user")

st.divider()
from db import authenticate_user, create_user

# =============================
# HOME VIEW
# =============================
if st.session_state.view == "home":

    st.subheader("🏠 Home Feed")

    # ---------- SEARCH INPUT (CONTROLLED) ----------
    with st.form("search_form"):
        query = st.text_input(
            "🔍 Search movies (TMDB – real time)",
            value=st.session_state.search_query,
            placeholder="Type at least 3 characters and press Enter"
        )
        search_submit = st.form_submit_button("Search")

    if search_submit:
        st.session_state.search_query = query.strip()
        st.session_state.page = 0
        st.rerun()

    # =============================
    # SEARCH MODE
    # =============================
    if st.session_state.search_query:

        q = st.session_state.search_query

        # ---------- AUTOCOMPLETE ----------
        suggestions = []
        if len(q) >= 3:
            suggestions = search_tmdb_suggestions(q)

        if suggestions:
            st.markdown("#### 🎯 Suggestions")
            for s in suggestions:
                if st.button(
                    f"{s['title']} ({s['year']})",
                    key=f"suggest_{s['tmdb_id']}"
                ):
                    st.session_state.selected_tmdb_id = s["tmdb_id"]
                    st.session_state.view = "details"
                    st.rerun()

        # ---------- SEARCH RESULTS ----------
        results = search_tmdb_movies(q, page=1)

        st.subheader(f"🔎 Results for: {q}")
        poster_grid(results)

        st.divider()

        if st.button("🏠 Back to Home"):
            st.session_state.search_query = ""
            goto("home")

    # =============================
    # NORMAL HOME FEED
    # =============================
    else:
        PAGE_SIZE = 24
        offset = st.session_state.page * PAGE_SIZE

        movies = fetch_home_feed("trending", PAGE_SIZE, offset)
        poster_grid(movies)

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.session_state.page > 0:
                if st.button("⬅ Previous"):
                    goto("home", page=st.session_state.page - 1)

        with col3:
            if st.button("Next ➡"):
                goto("home", page=st.session_state.page + 1)


# =============================
# DIARY
# =============================
elif st.session_state.view == "diary":
    if not st.session_state.current_user:
        st.warning("Select a user first")
        st.stop()

    st.subheader("📓 My Diary")
    diary = fetch_user_diary(st.session_state.current_user["user_id"])

    if not diary:
        st.info("No diary entries yet.")
    else:
        for d in diary:
            cols = st.columns([1, 4])
            with cols[0]:
                if d["poster_url"]:
                    st.image(d["poster_url"], use_column_width=True)
            with cols[1]:
                st.markdown(f"### {d['title']}")
                st.write(f"⭐ Rating: {d['rating']}")
                st.caption(f"Watched on {d['watched_date']}")

# =============================
# WATCHLIST
# =============================
elif st.session_state.view == "watchlist":
    if not st.session_state.current_user:
        st.warning("Select a user first")
        st.stop()

    st.subheader("📌 My Watchlist")
    watchlist = fetch_user_watchlist(st.session_state.current_user["user_id"])

    if not watchlist:
        st.info("Watchlist is empty.")
    else:
        for w in watchlist:
            cols = st.columns([1, 4])
            with cols[0]:
                if w["poster_url"]:
                    st.image(w["poster_url"], use_column_width=True)
            with cols[1]:
                st.markdown(f"### {w['title']}")
                st.caption(f"Priority: {w['priority']}")

# =============================
# FRIENDS FEED
# =============================
elif st.session_state.view == "feed":
    st.subheader("👥 Friends Feed")

    user = st.session_state.current_user

    # -----------------------------
    # FOLLOW / UNFOLLOW USERS
    # -----------------------------
    st.markdown("### 🤝 Discover People")

    people = fetch_all_users_except(user["user_id"])

    for p in people:
        cols = st.columns([3, 1])

        with cols[0]:
            st.write(f"👤 **{p['username']}**")

        with cols[1]:
            following = is_following(user["user_id"], p["user_id"])

            if following:
                if st.button("Unfollow", key=f"unfollow_{p['user_id']}"):
                    unfollow_user(user["user_id"], p["user_id"])
                    goto("feed")
            else:
                if st.button("Follow", key=f"follow_{p['user_id']}"):
                    follow_user(user["user_id"], p["user_id"])
                    goto("feed")

    st.divider()

    # -----------------------------
    # FRIENDS ACTIVITY
    # -----------------------------
    st.markdown("### 📰 Friends Activity")

    feed = fetch_followers_feed(user["user_id"])

    if not feed:
        st.info("Follow users to see their activity.")
    else:
        for f in feed:
            cols = st.columns([1, 4])

            with cols[0]:
                if f["poster_url"]:
                    st.image(f["poster_url"], use_column_width=True)

            with cols[1]:
                st.markdown(
                    f"**{f['username']}** reviewed **{f['title']}**"
                )
                st.write(f"⭐ {f['rating']}")
                st.write(f["review"])
                st.caption(f["created_at"])

elif st.session_state.view == "search":
    st.subheader(f"🔍 Results for: {st.session_state.search_query}")

    results = search_tmdb_movies(st.session_state.search_query)

    poster_grid(results)

# =============================
# MOVIE DETAILS
# =============================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id

    if not tmdb_id:
        st.error("Invalid movie selection.")
        st.stop()

    # -----------------------------
    # MOVIE FETCH (DB → TMDB FALLBACK)
    # -----------------------------
    movie = fetch_movie_details(tmdb_id)

    if not movie:
        tmdb_movie = fetch_tmdb_movie(tmdb_id)

        if not tmdb_movie:
            st.error("Unable to load movie details.")
            st.stop()

        movie = {
            "tmdb_id": tmdb_movie["id"],
            "title": tmdb_movie["title"],
            "overview": tmdb_movie.get("overview", ""),
            "poster_path": tmdb_movie.get("poster_path"),
            "genres": tmdb_movie.get("genres", []),
            "release_date": tmdb_movie.get("release_date"),
        }

    # -----------------------------
    # MOVIE HEADER
    # -----------------------------
    col1, col2 = st.columns([1, 2])

    with col1:
        if movie.get("poster_path"):
            st.image(
                f"{TMDB_IMG}{movie['poster_path']}",
                use_column_width=True
            )

    with col2:
        st.markdown(f"## {movie['title']}")
        st.write(movie.get("overview", "No overview available."))

    # -----------------------------
    # DIARY BUTTON
    # -----------------------------
    if st.session_state.current_user:
        in_diary = is_in_diary(
            st.session_state.current_user["user_id"],
            tmdb_id
        )

        if in_diary:
            if st.button("📕 Remove from Diary"):
                toggle_diary(
                    st.session_state.current_user["user_id"],
                    tmdb_id
                )
                st.success("Removed from diary")
                st.rerun()
        else:
            if st.button("📘 Add to Diary"):
                toggle_diary(
                    st.session_state.current_user["user_id"],
                    tmdb_id
                )
                st.success("Added to diary")
                st.rerun()

    # -----------------------------
    # WATCHLIST BUTTON
    # -----------------------------
    if st.session_state.current_user:
        from db import is_in_watchlist, toggle_watchlist

        in_watchlist = is_in_watchlist(
            st.session_state.current_user["user_id"],
            tmdb_id
        )

        if in_watchlist:
            if st.button("❌ Remove from Watchlist"):
                toggle_watchlist(
                    st.session_state.current_user["user_id"],
                    tmdb_id
                )
                st.rerun()
        else:
            if st.button("📌 Add to Watchlist"):
                toggle_watchlist(
                    st.session_state.current_user["user_id"],
                    tmdb_id
                )
                st.rerun()

    # =============================
    # WRITE / UPDATE REVIEW
    # =============================
    st.divider()
    st.subheader("✍️ Your Review")

    if st.session_state.current_user:
        user_id = st.session_state.current_user["user_id"]
        existing = fetch_user_review_for_movie(user_id, tmdb_id)

        # ---------- STAR RATING ----------
        st.markdown("### ⭐ Your Rating")

        if "star_rating" not in st.session_state:
            st.session_state.star_rating = (
                float(existing["rating"]) if existing else 0
            )

        star_cols = st.columns(5)
        for i in range(5):
            val = i + 1
            icon = "⭐" if val <= st.session_state.star_rating else "☆"

            if star_cols[i].button(icon, key=f"rate_{val}"):
                st.session_state.star_rating = val

        # ---------- REVIEW FORM ----------
        with st.form("review_form"):
            review_text = st.text_area(
                "Your review",
                value=existing["review_text"] if existing else "",
                height=120
            )

            submit = st.form_submit_button(
                "Submit Review"
            )

        # ---------- SUBMIT HANDLER ----------
        if submit:
            if st.session_state.star_rating == 0:
                st.warning("Please select a rating.")
            elif not review_text.strip():
                st.warning("Review text cannot be empty.")
            else:
                insert_or_update_review(
                    user_id=user_id,
                    tmdb_id=tmdb_id,
                    rating=st.session_state.star_rating,
                    review_text=review_text.strip()
                )

                st.success(
                    "Review updated successfully!"
                    if existing else
                    "Review added successfully!"
                )

                st.session_state.star_rating = 0 
                goto("details", tmdb_id)

    else:
        st.info("Login to write a review.")

    # =============================
    # ALL REVIEWS
    # =============================
    st.divider()
    st.subheader("📝 Reviews")

    reviews = fetch_movie_reviews(tmdb_id)

    if not reviews:
        st.info("No reviews yet.")
    else:
        for r in reviews:
            st.markdown(f"**{r['username']}**")
            st.write(r["review_text"])

            c1, c2 = st.columns([1, 6])

            with c1:
                if st.session_state.current_user:
                    liked = has_liked_review(
                        st.session_state.current_user["user_id"],
                        r["review_id"]
                    )

                    if liked:
                        if st.button("💔 Unlike", key=f"unlike_{r['review_id']}"):
                            unlike_review(
                                st.session_state.current_user["user_id"],
                                r["review_id"]
                            )
                            st.rerun()
                    else:
                        if st.button("❤️ Like", key=f"like_{r['review_id']}"):
                            like_review(
                                st.session_state.current_user["user_id"],
                                r["review_id"]
                            )
                            st.rerun()

            with c2:
                st.caption(f"⭐ {r['rating']}")

# =============================
# INSIGHTS
# =============================
elif st.session_state.view == "insights":
    if not st.session_state.current_user:
        st.warning("Select a user first")
        st.stop()

    user_id = st.session_state.current_user["user_id"]

    st.title("Insights Dashboard")
    st.caption("Visual analysis of user taste, behavior, and personalization strength")

    st.divider()

    # ==================================================
    # 1. GENRE AFFINITY (INTENSITY FIXED)
    # ==================================================
    col_chart, col_text = st.columns([2, 1])
    genres = get_user_top_genres(user_id)

    with col_chart:
        st.subheader("Genre Affinity")

        if genres:
            genre_df = pd.DataFrame(genres, columns=["Genre", "Count"])
            genre_df = genre_df.sort_values("Count", ascending=True)

            palette = sns.color_palette("Blues", len(genre_df))

            fig, ax = plt.subplots(figsize=(7, 4))
            sns.barplot(
                data=genre_df,
                x="Count",
                y="Genre",
                palette=palette,
                ax=ax
            )

            ax.set_title("Most Watched Genres")
            ax.set_xlabel("Movies Watched")
            ax.set_ylabel("")
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No genre data available yet.")

    with col_text:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Explanation")
        st.write(
            "Genres with darker bars represent stronger preferences. "
            "This genre affinity forms the primary basis of personalized recommendations."
        )

    st.divider()

    # ==================================================
    # 2. RATING BEHAVIOR
    # ==================================================
    col_chart, col_text = st.columns([2, 1])
    ratings = fetch_user_ratings(user_id)

    with col_chart:
        st.subheader("Rating Behavior")

        if ratings:
            fig, ax = plt.subplots(figsize=(7, 4))
            sns.histplot(
                ratings,
                bins=5,
                kde=True,
                color="#7C3AED",
                ax=ax
            )

            ax.set_title("Rating Distribution")
            ax.set_xlabel("Rating (1–5)")
            ax.set_ylabel("Frequency")
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No ratings available yet.")

    with col_text:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Explanation")
        st.write(
            "This distribution shows how strictly or generously you rate movies. "
            "It influences how selective recommendations become."
        )

    st.divider()

    # ==================================================
    # 3. FRIENDS INFLUENCE (INTENSITY FIXED)
    # ==================================================
    col_chart, col_text = st.columns([2, 1])
    trends = trending_among_friends(user_id)

    with col_chart:
        st.subheader("Friends Influence")

        if trends:
            trends_df = pd.DataFrame(trends, columns=["Movie", "Count"])
            trends_df = trends_df.sort_values("Count", ascending=True)

            palette = sns.color_palette("Reds", len(trends_df))

            fig, ax = plt.subplots(figsize=(7, 4))
            sns.barplot(
                data=trends_df,
                x="Count",
                y="Movie",
                palette=palette,
                ax=ax
            )

            ax.set_title("Trending Among Friends")
            ax.set_xlabel("Frequency")
            ax.set_ylabel("")
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No friends activity available yet.")

    with col_text:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Explanation")
        st.write(
            "Movies with darker bars are more popular among your friends. "
            "These social signals subtly influence recommendations."
        )

    st.divider()

    # ==================================================
    # 4. WATCHING CONSISTENCY (DATE FIXED)
    # ==================================================
    col_chart, col_text = st.columns([2, 1])
    activity = fetch_diary_activity(user_id)

    with col_chart:
        st.subheader("Watching Consistency")

        if activity:
            activity_df = pd.DataFrame(activity, columns=["Date", "Movies"])

            fig, ax = plt.subplots(figsize=(8, 3.5))
            sns.lineplot(
                data=activity_df,
                x="Date",
                y="Movies",
                linewidth=2.5,
                color="#16A34A",
                ax=ax
            )

            ax.scatter(
                activity_df["Date"],
                activity_df["Movies"],
                c=activity_df["Movies"],
                cmap="Greens",
                s=60,
                label="Movies Watched"
            )

            ax.xaxis.set_major_locator(
                mdates.AutoDateLocator(minticks=4, maxticks=7)
            )
            ax.xaxis.set_major_formatter(
                mdates.DateFormatter("%d %b")
            )

            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

            ax.set_title("Viewing Activity Over Time")
            ax.set_xlabel("Date")
            ax.set_ylabel("Movies Watched")
            ax.legend()
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No diary activity available yet.")

    with col_text:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Explanation")
        st.write(
            "Darker points indicate higher activity days. "
            "This timeline reveals whether watching behavior is consistent or sporadic."
        )

    st.divider()

    # ==================================================
    # 5. TASTE DIVERSITY
    # ==================================================
    col_chart, col_text = st.columns([2, 1])

    with col_chart:
        st.subheader("Taste Diversity")

        if genres:
            colors = sns.color_palette("Blues", len(genre_df))

            fig, ax = plt.subplots(figsize=(6, 6))
            ax.pie(
                genre_df["Count"],
                labels=genre_df["Genre"],
                autopct="%1.1f%%",
                startangle=140,
                colors=colors
            )

            ax.set_title("Genre Distribution")
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No diversity data available.")

    with col_text:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### Explanation")
        st.write(
            "This chart shows how evenly preferences are spread across genres. "
            "A balanced chart indicates exploration, while dominance indicates specialization."
        )

    st.divider()

    # ==================================================
    # 6. RECOMMENDATION READINESS
    # ==================================================
    st.subheader("Recommendation Readiness")
    st.caption("Current strength of personalization")

    reviews, diary, watchlist = fetch_user_activity_counts(user_id)
    readiness_score = min((reviews * 2 + diary + watchlist) * 10, 100)

    col1, col2, col3 = st.columns(3)
    col1.metric("Reviews", reviews)
    col2.metric("Diary Entries", diary)
    col3.metric("Watchlist", watchlist)

    st.progress(readiness_score / 100)
    st.caption(f"Personalization Strength: {readiness_score}%")

elif st.session_state.view == "cinemamaya":

    st.markdown('<div class="cinemamaya">', unsafe_allow_html=True)

    st.subheader("🌌 CINEMAMAYA – Personalized for You")
    st.caption("Curated from your taste, reviews & watch history")

    if st.button("🔄 Refresh Recommendations"):
        st.session_state.cinemamaya_refresh = time.time()
        st.rerun()

    recs = cinemamaya_recommendations(
        st.session_state.current_user["user_id"]
    )

    if recs is None or recs.empty:
        st.info("Watch & rate movies to unlock CINEMAMAYA ✨")
    else:
        poster_grid(
            recs.to_dict("records"),
            cols=6,
            show_reason=True
        )

    st.markdown("</div>", unsafe_allow_html=True)
