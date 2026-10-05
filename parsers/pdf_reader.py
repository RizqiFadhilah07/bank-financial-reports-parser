import re
import pdfplumber
from config import TWO_COLUMN_BANKS, SPLIT_X


def read_pages(pdf_path, bank_name):
    raw_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if bank_name in TWO_COLUMN_BANKS:
                left = page.crop((0, 0, SPLIT_X, page.height)).extract_text() or ""
                right = page.crop((SPLIT_X, 0, page.width, page.height)).extract_text() or ""
                raw_pages.append(left)
                raw_pages.append(right)
            else:
                raw_pages.append(page.extract_text() or "")
    return raw_pages


def fix_spaced_words(line):
    pattern = r"\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b"
    previous = None
    while previous != line:
        previous = line
        line = re.sub(pattern, lambda m: m.group(0).replace(" ", ""), line)
    return line


def clean_text(raw_pages):
    fixed_lines = []

    for page_text in raw_pages:
        for line in page_text.split("\n"):
            line = re.sub(r"^\d{2}[a-z]\s+", "", line)
            line = re.sub(r"(?<=\d)\s+(?=[\d.,])", "", line)
            line = re.sub(r"(?<=\d)\s+(?=,)", "", line)
            line = re.sub(r"(?<=,)\s+(?=\d)", "", line)
            line = re.sub(r"(?<=\()\s+(?=\d)", "", line)
            line = fix_spaced_words(line)
            fixed_lines.append(line)

    text = " ".join(fixed_lines)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("’", "'").replace("‘", "'")

    text = re.sub(
        r"\b([a-z])(?=(?:Keuntungan|Kerugian)\b)",
        r"\1 ",
        text,
        flags=re.IGNORECASE,
    )
    return text