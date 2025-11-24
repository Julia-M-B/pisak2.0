import re
import unicodedata

CLEAN_REGEX = re.compile(r"[^a-ząćęłńóśźż0-9\s]")
MULTIPLE_WHITESPACE = re.compile(r"[ \t]+")

def clean(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFC", text)
    text = CLEAN_REGEX.sub("", text)
    text = MULTIPLE_WHITESPACE.sub(" ", text)
    return text

def get_words_set(file_path) -> set[str]:
    with open(file_path, "r") as f:
        text = f.read()

    text = clean(text)
    words = text.split(" ")
    words = set(words)
    return words

