import io
import json
import re
from datetime import datetime

import streamlit as st
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder

st.title("🎤 Test Audio Recording")

# Widget
audio_bytes = audio_recorder()

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")  # playback
    st.success("Audio recorded!")

    # Convert to text
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio, language="en-US")
            st.write("👉 Recognized:", text)
        except Exception as e:
            st.error(f"Could not recognize: {e}")


# -------------------------
# OPTIONAL NLP (spaCy) - fallback to regex if not available
# -------------------------
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")
except Exception:
    nlp = None

# -------------------------
# DATA
# -------------------------
CATEGORIES = {
    "milk": "dairy", "cheese": "dairy", "yogurt": "dairy",
    "apple": "fruits", "banana": "fruits", "orange": "fruits",
    "bread": "bakery", "rice": "grains", "water": "beverages"
}

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

MOCK_PRODUCTS = [
    {"name": "organic apples", "brand": "Farm Fresh", "price": 3.5, "unit": "kg"},
    {"name": "toothpaste", "brand": "Colgate", "price": 2.2, "unit": "tube"},
    {"name": "toothpaste", "brand": "Sensodyne", "price": 4.8, "unit": "tube"},
    {"name": "almond milk", "brand": "Alpro", "price": 3.9, "unit": "1L"},
]

# -------------------------
# STATE
# -------------------------
def init_state():
    if "shopping_list" not in st.session_state:
        st.session_state.shopping_list = []
    if "history" not in st.session_state:
        st.session_state.history = {"purchases": []}

def save_history():
    with open("history.json", "w") as f:
        json.dump(st.session_state.history, f)

# -------------------------
# NLP HELPERS
# -------------------------
def parse_quantity(text):
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    for w, v in NUMBER_WORDS.items():
        if w in text:
            return v
    return 1

def parse_command(command):
    c = command.lower()
    qty = parse_quantity(c)

    if "add" in c or "buy" in c or "need" in c:
        intent = "add"
    elif "remove" in c or "delete" in c:
        intent = "remove"
    elif "show" in c or "list" in c:
        intent = "show"
    elif "find" in c or "search" in c:
        intent = "find"
    elif "suggest" in c or "recommend" in c:
        intent = "suggest"
    else:
        intent = "unknown"

    # extract item
    item = None
    for known in CATEGORIES.keys():
        if known in c:
            item = known
            break
    if not item and nlp:
        doc = nlp(c)
        nouns = [t.text.lower() for t in doc if t.pos_ in ("NOUN", "PROPN")]
        if nouns:
            item = nouns[-1]

    # extract price filter
    price_filter = None
    m = re.search(r"(under|below|less than)\s*\$?\s*([\d\.]+)", c)
    if m:
        price_filter = float(m.group(2))

    return intent, item, qty, price_filter

# -------------------------
# COMMAND HANDLERS
# -------------------------
def add_item(item, qty):
    cat = CATEGORIES.get(item, "others")
    st.session_state.shopping_list.append({"item": item, "qty": qty, "category": cat})
    st.session_state.history["purchases"].append({"item": item, "date": str(datetime.now().date())})
    save_history()
    st.success(f"✅ Added {qty} × {item} ({cat})")

def remove_item(item):
    before = len(st.session_state.shopping_list)
    st.session_state.shopping_list = [i for i in st.session_state.shopping_list if i["item"] != item]
    if len(st.session_state.shopping_list) < before:
        st.warning(f"❌ Removed {item}")
    else:
        st.info(f"{item} not found in your list")

def show_list():
    if not st.session_state.shopping_list:
        st.info("🛒 Your list is empty.")
        return
    st.subheader("🛒 Shopping List")
    for i in st.session_state.shopping_list:
        st.write(f"- {i['qty']} × {i['item']} ({i['category']})")

def suggest_items():
    history = st.session_state.history.get("purchases", [])
    if not history:
        st.info("No history yet.")
        return
    last = [p["item"] for p in history[-3:]]
    st.info("💡 You may need: " + ", ".join(last))

def search_products(item, price_filter):
    results = [p for p in MOCK_PRODUCTS if item in p["name"]]
    if price_filter:
        results = [p for p in results if p["price"] <= price_filter]
    if results:
        st.subheader("🔎 Results")
        for p in results:
            st.write(f"- {p['name']} ({p['brand']}) - ${p['price']} / {p['unit']}")
    else:
        st.info("No matches found.")

def handle_command(cmd):
    intent, item, qty, price_filter = parse_command(cmd)
    if intent == "add" and item:
        add_item(item, qty)
    elif intent == "remove" and item:
        remove_item(item)
    elif intent == "show":
        show_list()
    elif intent == "suggest":
        suggest_items()
    elif intent == "find" and item:
        search_products(item, price_filter)
    else:
        st.warning("⚠️ Could not understand your command.")

# -------------------------
# STREAMLIT UI
# -------------------------
def main():
    init_state()
    st.title("🛍 Voice Command Shopping Assistant")

    st.write("Try commands like: **add milk**, **remove apples**, **show list**, **suggest items**, **find apples under 5**")

    # Voice input
    with st.expander("🎤 Record a command"):
        audio = audio_recorder("Click to record / stop")
        if audio:
            recognizer = sr.Recognizer()
            try:
                with sr.AudioFile(io.BytesIO(audio)) as source:
                    data = recognizer.record(source)
                text = recognizer.recognize_google(data, language="en-US")
                st.success(f"You said: {text}")
                handle_command(text)
            except:
                st.error("❌ Could not recognize speech. Try typing instead.")

    # Text input fallback
    cmd = st.text_input("Or type a command:")
    if st.button("Run"):
        if cmd:
            handle_command(cmd)

    st.divider()
    show_list()

if __name__ == "__main__":
    main()
