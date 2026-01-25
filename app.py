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
    get_user_top_genres
)
from recommender import cinemamaya_recommendations

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
    layout="wide"
)
st.markdown("""
<style>

/* ===============================
   CORE COLORS (Letterboxd Style)
   =============================== */
:root {
    --bg-main: #0e0f11;
    --bg-panel: #16181d;
    --bg-card: #1b1e24;
    --border-soft: #2a2e36;

    --text-main: #e6e6e6;
    --text-muted: #a0a4ad;

    --accent-green: #00c030;
    --accent-blue: #40bcf4;
}

/* ===============================
   APP BACKGROUND
   =============================== */
[data-testid="stAppViewContainer"] {
    background-color: var(--bg-main);
    color: var(--text-main);
}

/* ===============================
   SIDEBAR
   =============================== */
[data-testid="stSidebar"] {
    background-color: #0b0c0f;
    border-right: 1px solid var(--border-soft);
}

[data-testid="stSidebar"] * {
    color: var(--text-main) !important;
}

/* Sidebar buttons */
[data-testid="stSidebar"] .stButton > button {
    background: var(--bg-panel);
    border: 1px solid var(--border-soft);
    color: var(--text-main);
    border-radius: 10px;
    padding: 10px 14px;
    width: 100%;
    text-align: left;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: #22262d;
    border-color: var(--accent-green);
}

/* ===============================
   HEADINGS & TEXT
   =============================== */
h1, h2, h3, h4 {
    color: #ffffff;
}

p, span, label {
    color: var(--text-main) !important;
}

/* Muted captions */
small, .stCaption {
    color: var(--text-muted) !important;
}

/* ===============================
   MOVIE CARD
   =============================== */
.movie-card {
    background: var(--bg-card);
    border-radius: 14px;
    padding: 10px;
    border: 1px solid var(--border-soft);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.movie-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.6);
}

.movie-title {
    font-weight: 600;
    margin-top: 8px;
    text-align: center;
}

/* ===============================
   BUTTONS (NO YELLOW)
   =============================== */
.stButton > button {
    background: #20232a;
    color: var(--text-main);
    border: 1px solid var(--border-soft);
    border-radius: 10px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #262a33;
    border-color: var(--accent-blue);
}

/* ===============================
   TEXT INPUTS / REVIEW BOX
   =============================== */
textarea, input {
    background-color: #0f1115 !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
}

textarea::placeholder {
    color: var(--text-muted);
}

/* ===============================
   STAR RATING
   =============================== */
.star {
    font-size: 30px;
    cursor: pointer;
}

.star-active {
    color: var(--accent-green);
}

.star-inactive {
    color: #444;
}

/* ===============================
   CINEMAMAYA PANEL
   =============================== */
.cinemamaya {
    background: linear-gradient(180deg, #15171c, #0f1115);
    border-radius: 18px;
    padding: 20px;
    border: 1px solid var(--border-soft);
}

</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>

/* ===============================
   FORCE TEXT VISIBILITY FIX
   =============================== */

/* All buttons */
button, .stButton button {
    color: #ffffff !important;
    background-color: #1f222a !important;
    border: 1px solid #3a3f4b !important;
}

/* Button hover */
button:hover {
    background-color: #2a2f3a !important;
}

/* Submit buttons inside forms */
button[kind="primary"] {
    background-color: #00c030 !important;
    color: #000000 !important;
    font-weight: 700 !important;
}

/* Text inside inputs & textareas */
textarea, input {
    color: #ffffff !important;
}

/* Placeholder text */
textarea::placeholder, input::placeholder {
    color: #9aa0aa !important;
}

/* ===============================
   STAR RATING VISIBILITY
   =============================== */
.star-btn {
    font-size: 32px;
    background: transparent !important;
    border: none !important;
    color: #444 !important;
}

.star-btn.active {
    color: #00c030 !important;
}

/* Fix emoji rendering */
span, p {
    color: #ffffff !important;
}

</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* REMOVE STREAMLIT DEFAULT HEADER GAP */
header, .stApp > header {
    background: transparent !important;
    height: 0px !important;
}

/* Remove top padding */
.block-container {
    padding-top: 1rem !important;
}

/* Force app background */
.stApp {
    background: radial-gradient(circle at top, #0f1115, #000000);
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

if "view" in params:
    st.session_state.view = params.get("view", st.session_state.view)

if "page" in params:
    st.session_state.page = int(params.get("page", st.session_state.page))

if "tmdb_id" in params:
    st.session_state.selected_tmdb_id = int(params["tmdb_id"])

if "q" in params:
    st.session_state.search_query = params.get("q", "")

if "sp" in params:
    st.session_state.search_page = int(params.get("sp", 1))

def goto(view, tmdb_id=None, q=None, page=None, sp=None):
    st.session_state.view = view

    st.query_params.clear()
    st.query_params["view"] = view

    if tmdb_id is not None:
        st.session_state.selected_tmdb_id = tmdb_id
        st.query_params["tmdb_id"] = str(tmdb_id)

    if q is not None:
        st.session_state.search_query = q
        st.query_params["q"] = q

    if page is not None:
        st.session_state.page = page
        st.query_params["page"] = str(page)

    if sp is not None:
        st.session_state.search_page = sp
        st.query_params["sp"] = str(sp)

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
# ROUTING
# =============================

if st.session_state.current_user is None:
    st.title("🔐 Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        from db import authenticate_user
        user = authenticate_user(username, password)

        if user:
            st.session_state.current_user = user
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

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
                    st.image(m["poster_url"], use_container_width=True)
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
    st.markdown(f"### 👤 {st.session_state.current_user['username']}")

    if st.button("🚪 Logout"):
        st.session_state.current_user = None
        st.rerun()

    st.markdown("---")

    if st.button("🏠 Home"):
        goto("home")
    if st.button("📓 My Diary"):
        goto("diary")
    if st.button("📌 My Watchlist"):
        goto("watchlist")
    if st.button("👥 Friends Feed"):
        goto("feed")
    if st.button("📊 Insights"):
        goto("insights")
    if st.button("🌌 CINEMAMAYA"):
        goto("cinemamaya")



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
# HOME
# =============================
# =============================
# HOME VIEW
# =============================
if st.session_state.view == "home":

    st.subheader("🏠 Home Feed")

    query = st.text_input(
        "🔍 Search movies (TMDB – real time)",
        value=st.session_state.search_query,
        placeholder="Type a movie name..."
    )

    # =============================
    # SEARCH MODE
    # =============================
    if query.strip():

        # 🔁 Reset page when query changes
        if query != st.session_state.search_query:
            st.session_state.search_query = query
            st.session_state.search_page = 1

        # ---------- AUTOCOMPLETE ----------
        suggestions = search_tmdb_suggestions(query)

        if suggestions:
            st.markdown("#### 🎯 Suggestions")
            for s in suggestions[:5]:
                if st.button(
                    f"{s['title']} ({s['year']})",
                    key=f"suggest_{s['tmdb_id']}"
                ):
                    goto("details", s["tmdb_id"])

        # ---------- SEARCH RESULTS ----------
        results = search_tmdb_movies(
            st.session_state.search_query,
            page=st.session_state.search_page
        )

        st.subheader(f"🔎 Results for: {st.session_state.search_query}")
        poster_grid(results)

        # ---------- SEARCH PAGINATION ----------
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.session_state.search_page > 1:
                if st.button("⬅ Previous", key="search_prev"):
                    goto(
                        "home",
                        q=st.session_state.search_query,
                        sp=st.session_state.search_page - 1
                    )

        with col3:
            if st.button("Next ➡", key="search_next"):
                goto(
                    "home",
                    q=st.session_state.search_query,
                    sp=st.session_state.search_page + 1
                )

        # ---------- BACK TO HOME ----------
        st.divider()
        if st.button("🏠 Back to Home"):
            st.session_state.search_query = ""
            st.session_state.search_page = 1
            goto("home", page=0)

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
                    st.image(d["poster_url"], use_container_width=True)
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
                    st.image(w["poster_url"], use_container_width=True)
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
                    st.rerun()
            else:
                if st.button("Follow", key=f"follow_{p['user_id']}"):
                    follow_user(user["user_id"], p["user_id"])
                    st.rerun()

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
                    st.image(f["poster_url"], use_container_width=True)

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
        from db import fetch_tmdb_movie
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
                use_container_width=True
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
                "Submit Review",
                use_container_width=True
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
                st.rerun()
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
                st.caption(f"⭐ {r['rating']} · ❤️ {r['like_count']}")

# =============================
# INSIGHTS
# =============================
elif st.session_state.view == "insights":
    if not st.session_state.current_user:
        st.warning("Select a user first")
        st.stop()

    st.subheader("📊 Insights")

    st.markdown("### 🎭 Top Genres")
    genres = get_user_top_genres(st.session_state.current_user["user_id"])
    if genres:
        for g, c in genres:
            st.write(f"{g} → {c}")
    else:
        st.info("No genre data yet.")

    st.markdown("### 🔥 Trending Among Friends")
    trends = trending_among_friends(st.session_state.current_user["user_id"])
    if trends:
        for t, c in trends:
            st.write(f"{t} → {c}")
    else:
        st.info("No trends yet.")
elif st.session_state.view == "cinemamaya":

    st.markdown('<div class="cinemamaya">', unsafe_allow_html=True)

    st.subheader("🌌 CINEMAMAYA – Personalized for You")
    st.caption("Curated from your taste, reviews & watch history")

    if st.button("🔄 Refresh Recommendations"):
        st.session_state.cinemamaya_refresh += 1
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
