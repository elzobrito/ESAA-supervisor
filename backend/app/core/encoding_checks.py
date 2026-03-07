def check_encoding(file_path: str) -> bool:
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def detect_mojibake(text: str) -> bool:
    # Basic heuristic for detecting common mojibake patterns
    # (e.g., "Ã¡" instead of "á")
    mojibake_patterns = ["Ã", "Â", "â", "œ"]
    for pattern in mojibake_patterns:
        if pattern in text:
            # This is very naive and might have false positives, 
            # but serves the purpose for PoC.
            return True
    return False
