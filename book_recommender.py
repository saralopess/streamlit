import streamlit as st
import requests
import random

# =========================
#  Config
# =========================

OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
COVERS_BASE_URL = "https://covers.openlibrary.org/b/id/"

# =========================
#  Mappings
# =========================

GENRE_TO_SUBJECT = {
    "Classics 🏛️": "classics",
    "Fantasy 🐉": "fantasy",
    "Science Fiction 🚀": "science_fiction",
    "Romance ❤️": "romance",
    "Mystery / Crime 🕵️‍♂️": "mystery",
    "Thriller 😱": "thriller",
    "Horror 👻": "horror",
    "Historical 📜": "historical_fiction",
    "Non-fiction 📚": "nonfiction",
    "Young Adult ✨": "young_adult",
    "Children 👧🧒": "children",
    "Poetry ✒️": "poetry",
    "Comics / Manga 💥": "comics",
}

YEAR_RANGES = {
    " Before 1950": (None, 1949),
    " 1950–1980": (1950, 1980),
    " 1980–2000": (1980, 2000),
    " 2000–2010": (2000, 2010),
    " 2010–2020": (2010, 2020),
    " After 2020": (2021, None),
    "🎲 No preference": (None, None),
}

LENGTH_RANGES = {
    " Snack-size (< 200 pages)": (0, 199),
    " A normal meal (200–400 pages)": (200, 400),
    " A full feast (400+ pages)": (401, None),
    " 🎲 Surprise me (any length)": (None, None),
}

MOOD_EXTRA_SUBJECTS = {
    "Cozy & comfy ☕️": ["cozy", "friendship"],
    "Dark & twisty 🌑": ["dark", "psychological"],
    "Funny 😂": ["humor"],
    "Soft & romantic 💌": ["love_stories"],
    "Adventure 🗺️": ["adventure"],
    "Scary 👀": ["horror"],
    "Thought-provoking 🤔": ["philosophy"],
}

# =========================
#  Fetch summary + ratings
# =========================

def fetch_work_details(key: str):
    base = "https://openlibrary.org"

    description = None
    rating_avg = None
    rating_count = None

    # Summary
    r = requests.get(f"{base}{key}.json")
    if r.ok:
        data = r.json()
        d = data.get("description")
        if isinstance(d, dict):
            description = d.get("value")
        elif isinstance(d, str):
            description = d

    # Ratings
    r2 = requests.get(f"{base}{key}/ratings.json")
    if r2.ok:
        summary = r2.json().get("summary", {})
        rating_avg = summary.get("average")
        rating_count = summary.get("count")

    return description, rating_avg, rating_count

# =========================
#  Core Logic
# =========================

def build_tags(prefs):
    return {
        "subjects": [GENRE_TO_SUBJECT[g] for g in prefs["genres"]],
        "extra": sum((MOOD_EXTRA_SUBJECTS[m] for m in prefs["mood"]), []),
        "year": YEAR_RANGES[prefs["year_range"]],
        "length": LENGTH_RANGES[prefs["length"]],
        "kids": prefs["kids"],
    }

def fetch_books(tags):
    docs = {}

    def query(subject):
        q_parts = []

        # Subject or generic fallback
        if subject:
            q_parts.append(f"subject:{subject}")
        else:
            q_parts.append("books")

        # If for kids, bias toward children-related subjects
        if tags["kids"] == "Yes":
            q_parts.append("subject:children OR subject:juvenile")

        q = " ".join(q_parts)

        params = {
            "q": q,
            "limit": 50,
        }

        r = requests.get(OPENLIBRARY_SEARCH_URL, params=params)
        if r.ok:
            for d in r.json().get("docs", []):
                if d.get("key"):
                    docs[d["key"]] = d

    # Main genres
    for s in tags["subjects"]:
        query(s)

    # Broad search
    query(None)

    # Extra mood-based subjects
    for s in tags["extra"]:
        query(s)

    return list(docs.values())

def passes_range(v, a, b):
    if v is None:
        return True
    if a is not None and v < a:
        return False
    if b is not None and v > b:
        return False
    return True

def is_kids_book(doc):
    title = (doc.get("title") or "").lower()
    subjects = " ".join(doc.get("subject", [])).lower() if doc.get("subject") else ""

    kids_keywords = [
        "children", "childrens", "kid", "kids",
        "juvenile", "coloring book", "colouring book",
        "notebook", "activity book", "for kids",
    ]

    return any(k in title for k in kids_keywords) or any(
        k in subjects for k in kids_keywords
    )

def filter_books(docs, tags):
    ya, yb = tags["year"]
    pa, pb = tags["length"]

    filtered = [
        d for d in docs
        if passes_range(d.get("first_publish_year"), ya, yb)
        and passes_range(d.get("number_of_pages_median"), pa, pb)
    ]

    # If it's NOT for kids, remove kids-style books
    if tags["kids"] == "No":
        filtered = [d for d in filtered if not is_kids_book(d)]

    return filtered

# =========================
# TRUE RANDOM SELECTOR
# =========================

def pick_random(docs, prev_key=None):
    if not docs:
        return None
    pool = [d for d in docs if d.get("key") != prev_key] or docs
    return random.choice(pool)

def format_book(d):
    return {
        "title": d.get("title", "Unknown Title"),
        "authors": ", ".join(d.get("author_name", []) or []),
        "year": d.get("first_publish_year", "Unknown Year"),
        "pages": d.get("number_of_pages_median"),
        "cover": f"{COVERS_BASE_URL}{d.get('cover_i')}-L.jpg" if d.get("cover_i") else None,
        "key": d.get("key"),
        "url": "https://openlibrary.org" + d.get("key"),
    }

# =========================
#  UI
# =========================

st.title("📚 Bookify – Swipe Your Next Read!")

# INTRO
st.write("""
👋 **Welcome to Bookify — where every reader finds their perfect match!**  
Take our fun, short quiz and let us pair you with a book that feels *just right*.  
Ready to meet your next story? 
""")

# State
if "results" not in st.session_state:
    st.session_state.results = []

if "book" not in st.session_state:
    st.session_state.book = None

if "likes" not in st.session_state:
    st.session_state.likes = []

# Sidebar
st.sidebar.header("❤️ Your Liked Books")
for b in st.session_state.likes:
    st.sidebar.markdown(
        f"**{b['title']}**<br>"
        f"{b['authors']}<br>"
        f"<a href='{b['url']}' target='_blank'>Open Library</a>",
        unsafe_allow_html=True,
    )
    st.sidebar.write("---")

if not st.session_state.likes:
    st.sidebar.write("No liked books yet.")

# =========================
#  QUIZ
# =========================

with st.form("quiz"):
    st.subheader("1. What kind of genre are you in the mood for? 🏷️")
    genres = st.multiselect(
        "Choose 1–3 genres you enjoy:",
        list(GENRE_TO_SUBJECT.keys()),
        default=["Classics 🏛️"],
    )

    st.subheader("2. What mood should your next book have? 🎭")
    mood = st.multiselect(
        "Pick the vibe you're looking for:",
        list(MOOD_EXTRA_SUBJECTS.keys()),
    )

    st.subheader("3. What kind of reading “meal” are you craving? 🍽️")
    length = st.radio("Choose your preferred ‘portion’:", list(LENGTH_RANGES.keys()))
    year = st.selectbox("Which era should it come from?", list(YEAR_RANGES.keys()))

    st.subheader("4. Who is this book for? 👥")
    audience = st.selectbox("Who's reading?", ["Just me", "Me & kids"])
    kids = "Yes" if audience == "Me & kids" else "No"

    go = st.form_submit_button("Find Books")

# =========================
#  LOAD RESULTS
# =========================

if go:
    prefs = {
        "genres": genres,
        "mood": mood,
        "length": length,
        "year_range": year,
        "kids": kids,
    }

    tags = build_tags(prefs)

    with st.spinner("🔎 Searching for books…"):
        docs = fetch_books(tags)
        docs = filter_books(docs, tags)

    if docs:
        st.session_state.results = docs
        st.session_state.book = format_book(pick_random(docs))
    else:
        st.error("No books match your filters — try adjusting them!")

# =========================
#  SHOW BOOK + SWIPE
# =========================

book = st.session_state.book

if book:
    st.subheader("📖 Your Match")

    col1, col2 = st.columns([1, 2])

    with col1:
        if book["cover"]:
            st.image(book["cover"], caption="", use_column_width=True)
        else:
            st.write("No cover available.")

    with col2:
        st.markdown(f"### {book['title']} 📘")
        if book["authors"]:
            st.write(f"**Author:** {book['authors']}")
        st.write(f"**Published:** {book['year']}")
        st.write(f"[🔗 View on Open Library]({book['url']})")

    desc, avg, count = fetch_work_details(book["key"])

    st.subheader("📝 Summary")
    st.write(desc or "No summary available.")

    st.subheader("⭐ Ratings")
    if avg is not None:
        st.write(f"**{avg:.1f} ⭐** ({count} reviews)")
    else:
        st.write("No ratings available.")

    st.write("---")
    st.markdown("### ❤️ Swipe")

    left, right = st.columns(2)

    if left.button("❤️ Like"):
        st.session_state.likes.append(book)
        st.session_state.book = format_book(
            pick_random(st.session_state.results, book["key"])
        )
        st.rerun()

    if right.button("❌ Skip"):
        st.session_state.book = format_book(
            pick_random(st.session_state.results, book["key"])
        )
        st.rerun()

elif go:
    st.info("Try adjusting your filters for more results.")


