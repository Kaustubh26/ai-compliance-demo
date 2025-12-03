import os

def load_text_from_file(filepath):
    """
    Load text from a given file path.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print("❌ Failed parsing file:", filepath, e)
        return ""
