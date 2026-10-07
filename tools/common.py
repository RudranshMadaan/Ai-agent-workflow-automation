from pathlib import Path
import pandas as pd
from rapidfuzz.fuzz import ratio


def read_table(path: str) -> pd.DataFrame:
    p = Path(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(p)
    return pd.read_csv(p)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


def similarity(a, b) -> float:
    return ratio(str(a).lower().strip(), str(b).lower().strip()) / 100.0


def pct_difference(a, b) -> float:
    if float(a) == 0:
        return float("inf")
    return abs(float(a) - float(b)) / abs(float(a)) * 100.0
