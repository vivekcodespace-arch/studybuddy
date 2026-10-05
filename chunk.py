import re


def is_useful(chunk):
    text = chunk.strip()
    if len(text) < 200:
        return False
    words = text.split()
    if not words:
        return False
    alpha = sum(c.isalpha() for c in text)
    if alpha / max(len(text), 1) < 0.6:
        return False
    if len(re.findall(r"\b(19|20)\d{2}\b", text)) > 4:
        return False
    if sum(1 for w in words if w.endswith(".")) > len(words) * 0.3:
        return False
    return True


def chunk_text(text, size=1500):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if current and len(current) + len(p) > size:
            chunks.append(current)
            current = p
        else:
            current = f"{current}\n\n{p}" if current else p
    if current:
        chunks.append(current)
    return [c for c in chunks if is_useful(c)]