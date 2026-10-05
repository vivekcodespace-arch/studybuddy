import os
import json
from ollama import Client

MODEL = os.getenv("OLLAMA_MODEL", "gemma2:2b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

client = Client(host=OLLAMA_HOST)

# PROMPT = """You are making flashcards from study text.

# Rules:
# - Make one flashcard for EVERY distinct fact in the text.
# - If the text contains 4 facts, return 4 flashcards.
# - Return at least 2 flashcards. Never return just one.
# - Each question must stand alone and test ONE fact.
# - Never invent facts that are not in the text.
# - Keep answers to one short sentence.

# Return a JSON object with a single key "flashcards" holding an array.

# Example text:
# Binary search repeatedly divides a sorted array in half. It runs in O(log n) time. It requires random access to elements.

# Example response:
# {{"flashcards": [{{"q": "What is the time complexity of binary search?", "a": "O(log n)"}}, {{"q": "What must be true of an array before binary search can be used?", "a": "It must be sorted."}}, {{"q": "What access pattern does binary search require?", "a": "Random access to elements."}}]}}

# Now do the same for this text:
# {text}
# """


def validate_card(card):
    if not isinstance(card, dict):
        return None
    q = card.get("q") or card.get("question")
    a = card.get("a") or card.get("answer")
    if not isinstance(q, str) or not isinstance(a, str):
        return None
    q, a = q.strip(), a.strip()
    if len(q) < 8 or len(a) < 1:
        return None
    if "according to the text" in q.lower():
        return None
    return {"q": q, "a": a}


def unwrap(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("flashcards", "cards", "questions", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        if "q" in data or "question" in data:
            return [data]
    return []


# PROMPT = """You are making flashcards from study text.

# Rules:
# - Make one flashcard for EVERY distinct fact in the text.
# - If the text contains 4 facts, return 4 flashcards.
# - Return at least 2 flashcards. Never return just one.
# - Each question must stand alone and test ONE fact.
# - Never invent facts that are not in the text.
# - Keep answers to one short sentence.

# Return a JSON object with a single key "flashcards" holding an array.

# Example text:
# Binary search repeatedly divides a sorted array in half. It runs in O(log n) time. It requires random access to elements.

# Example response:
# {{"flashcards": [{{"q": "What is the time complexity of binary search?", "a": "O(log n)"}}, {{"q": "What must be true of an array before binary search can be used?", "a": "It must be sorted."}}, {{"q": "What access pattern does binary search require?", "a": "Random access to elements."}}]}}

# Now do the same for this text:
# {text}
# """
PROMPT = """Make flashcards from the text. One card per distinct fact. At least 2 cards. Questions must stand alone. Never invent facts. Short answers.

Return JSON: {{"flashcards": [{{"q": "...", "a": "..."}}]}}

Example text: Binary search divides a sorted array in half. It runs in O(log n) time.
Example response: {{"flashcards": [{{"q": "What is the time complexity of binary search?", "a": "O(log n)"}}, {{"q": "What must be true of an array for binary search?", "a": "It must be sorted."}}]}}

Text:
{text}
"""

def generate_cards(chunk, _depth=0):
    try:
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": PROMPT.format(text=chunk)}],
            format="json",
            options={
                "temperature": 0.3,
                "num_ctx": 2048,
                "num_predict": 600,
            },
            keep_alive="30m",
        )
    except Exception as exc:
        print(f"Generation failed: {exc}")
        return []

    content = response["message"]["content"].strip()
    content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []

    cards = [c for c in (validate_card(x) for x in unwrap(data)) if c]

    # Small models sometimes collapse a dense chunk into one card.
    # Split once and retry each half rather than losing the content.
    if len(cards) < 2 and _depth == 0 and len(chunk) > 400:
        mid = chunk.rfind(". ", 0, len(chunk) // 2 + 100)
        if mid > 100:
            left = generate_cards(chunk[: mid + 1], _depth=1)
            right = generate_cards(chunk[mid + 1 :], _depth=1)
            merged = left + right
            if len(merged) > len(cards):
                return dedupe(merged)

    return dedupe(cards)


def dedupe(cards):
    seen, out = set(), []
    for c in cards:
        key = c["q"].lower().rstrip("?. ")
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out