def normalize_numeric(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
