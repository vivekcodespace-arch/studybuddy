from pypdf import PdfReader


def extract_pages(pdf_file):
    reader = PdfReader(pdf_file)
    return [page.extract_text() or "" for page in reader.pages]


def pages_to_text(pages):
    return "\n\n".join(p for p in pages if p.strip())