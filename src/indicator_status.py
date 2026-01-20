import pandas as pd

def indicator_status(values):
    numeric = pd.to_numeric(values, errors="coerce")

    total = len(numeric)
    reported = numeric.notna().sum()

    if reported == 0:
        return "Not Reported", 0

    coverage = round((reported / total) * 100)

    if reported < total:
        return "Partial", coverage

    return "Reported", 100
