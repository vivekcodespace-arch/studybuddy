import streamlit as st
from extract import extract_pages, pages_to_text
from chunk import chunk_text
from generate import generate_cards, client, MODEL, OLLAMA_HOST
from export import export_to_anki, to_csv


st.title("Flashcard Generator")
st.caption("Runs locally on Gemma. Your notes never leave your machine.")

try:
    available = [m["model"] for m in client.list()["models"]]
    if MODEL not in available:
        st.error(f"Model {MODEL} not found. Run: docker exec -it ollama ollama pull {MODEL}")
        st.stop()
except Exception:
    st.error(f"Cannot reach Ollama at {OLLAMA_HOST}. Is the container running?")
    st.stop()

st.session_state.setdefault("cards", [])
st.session_state.setdefault("done_upto", 0)
st.session_state.setdefault("running", False)

uploaded = st.file_uploader("Upload a PDF", type="pdf")
pasted = st.text_area("Or paste your notes")
deck_name = st.text_input("Deck name", "My Study Deck")
batch_size = st.slider("Pages per batch", 2, 20, 5)
target = st.number_input("Stop after N cards (0 = all pages)", 0, 500, 0, step=10)

pages = []
if uploaded:
    pages = extract_pages(uploaded)
elif pasted.strip():
    pages = [pasted]

if pages:
    start = st.session_state.done_upto
    total = len(pages)
    st.info(f"{total} pages found. Done so far: {start}")

    if start >= total:
        st.session_state.running = False
        st.success("All pages processed.")
    elif target and len(st.session_state.cards) >= target:
        st.session_state.running = False
        st.success(f"Reached {len(st.session_state.cards)} cards. Stopped at page {start}.")
    elif st.session_state.running:
        end = min(start + batch_size, total)

        if st.button("Pause", type="secondary"):
            st.session_state.running = False
            st.rerun()

        st.progress(start / total, text=f"Pages {start + 1}-{end} of {total} · {len(st.session_state.cards)} cards")

        chunks = chunk_text(pages_to_text(pages[start:end]))
        if not chunks:
            st.warning(f"No usable text in pages {start + 1}-{end}. Skipping.")
        else:
            status = st.empty()
            for i, chunk in enumerate(chunks):
                st.session_state.cards.extend(generate_cards(chunk))
                status.caption(f"Chunk {i + 1} of {len(chunks)} · {len(st.session_state.cards)} cards")

        st.session_state.done_upto = end
        st.rerun()
    else:
        label = "Start" if start == 0 else f"Resume from page {start + 1}"
        if st.button(label, type="primary"):
            st.session_state.running = True
            st.rerun()

cards = st.session_state.cards
if cards:
    st.divider()
    review_tab, study_tab = st.tabs([f"Review ({len(cards)})", "Study"])

    with review_tab:
        kept = []
        for i, card in enumerate(cards):
            with st.expander(card["q"][:70]):
                q = st.text_input("Question", card["q"], key=f"q{i}")
                a = st.text_area("Answer", card["a"], key=f"a{i}", height=80)
                if q != card["q"] or a != card["a"]:
                    st.session_state.running = False
                if st.checkbox("Include", value=True, key=f"k{i}"):
                    kept.append({"q": q, "a": a})

        st.caption(f"{len(kept)} of {len(cards)} selected")

        col1, col2 = st.columns(2)

        with col1:
            if kept and st.button("Prepare Anki deck"):
                export_to_anki(kept, deck_name, "output.apkg")
                st.session_state.deck_ready = True

            if st.session_state.get("deck_ready"):
                with open("output.apkg", "rb") as f:
                    st.download_button("Download .apkg", f, f"{deck_name}.apkg")
                st.caption("Don't unzip. Install Anki from apps.ankiweb.net, then File → Import.")

        with col2:
            if kept:
                st.download_button("Download CSV", to_csv(kept), f"{deck_name}.csv", "text/csv")
                st.caption("For Quizlet, Sheets, or reading on a phone.")

        if st.button("Start over"):
            for key in ("cards", "done_upto", "running", "deck_ready", "idx", "revealed", "known"):
                st.session_state.pop(key, None)
            st.rerun()

    with study_tab:
        st.session_state.setdefault("idx", 0)
        st.session_state.setdefault("revealed", False)
        st.session_state.setdefault("known", set())

        idx = min(st.session_state.idx, len(cards) - 1)
        card = cards[idx]

        st.caption(f"Card {idx + 1} of {len(cards)} · {len(st.session_state.known)} marked known")
        st.progress((idx + 1) / len(cards))

        st.markdown(f"### {card['q']}")

        if st.session_state.revealed:
            st.success(card["a"])
            c1, c2, c3 = st.columns(3)
            if c1.button("Got it", use_container_width=True):
                st.session_state.known.add(idx)
                st.session_state.idx = (idx + 1) % len(cards)
                st.session_state.revealed = False
                st.rerun()
            if c2.button("Need practice", use_container_width=True):
                st.session_state.known.discard(idx)
                st.session_state.idx = (idx + 1) % len(cards)
                st.session_state.revealed = False
                st.rerun()
            if c3.button("Back", use_container_width=True):
                st.session_state.idx = (idx - 1) % len(cards)
                st.session_state.revealed = False
                st.rerun()
        else:
            if st.button("Show answer", type="primary", use_container_width=True):
                st.session_state.revealed = True
                st.rerun()