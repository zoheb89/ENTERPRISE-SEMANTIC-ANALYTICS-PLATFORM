
"""
Capgemini DataPrepAI — deterministic raw-data preparation engine.

Safe-by-default transformations:
- normalize column names
- trim string whitespace
- convert blank strings to null
- remove exact duplicate rows
- detect null-heavy columns
- detect inconsistent date / numeric candidates
- produce explainable recommendations
- apply only deterministic, reversible preparation actions

The engine does not invent business values and does not silently delete
non-duplicate business records.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import re
import numpy as np
import pandas as pd

@dataclass
class PrepFinding:
    table: str
    issue: str
    severity: str
    affected_rows: int
    recommendation: str
    action: str
    auto_safe: bool = True

def _is_date_like(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("date","time","timestamp","dob","birth"))

def _date_parse_ratio(s: pd.Series) -> float:
    x = s.dropna().astype(str).str.strip()
    if x.empty: return 0.0
    try:
        parsed = pd.to_datetime(x, errors="coerce", format="mixed")
    except TypeError:
        parsed = pd.to_datetime(x, errors="coerce")
    return float(parsed.notna().mean())

def _numeric_parse_ratio(s: pd.Series) -> float:
    x = s.dropna().astype(str).str.replace(",","",regex=False).str.replace("$","",regex=False).str.strip()
    if x.empty: return 0.0
    parsed = pd.to_numeric(x, errors="coerce")
    return float(parsed.notna().mean())

def profile_raw(files: dict[str, pd.DataFrame]) -> list[PrepFinding]:
    findings=[]
    for name, df in files.items():
        dup=int(df.duplicated(keep="first").sum())
        if dup:
            findings.append(PrepFinding(name,"Exact duplicate rows","warning",dup,
                "Remove exact duplicate records while preserving the first occurrence.",
                "drop_exact_duplicates",True))
        for col in df.columns:
            s=df[col]
            nulls=int(s.isna().sum())
            blanks=0
            if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
                blanks=int(s.astype("string").str.strip().eq("").sum())
            affected=nulls+blanks
            if affected and affected/len(df) >= .30:
                findings.append(PrepFinding(name,f"Null/blank-heavy column: {col}","warning",affected,
                    "Convert blanks to null and review whether the column should be retained in the semantic model.",
                    "blank_to_null",True))
            elif blanks:
                findings.append(PrepFinding(name,f"Blank string values: {col}","info",blanks,
                    "Convert whitespace-only values to null.",
                    "blank_to_null",True))
            if _is_date_like(str(col)) and not pd.api.types.is_datetime64_any_dtype(s):
                ratio=_date_parse_ratio(s)
                if ratio >= .90 and ratio < 1:
                    bad=int(s.notna().sum()*(1-ratio))
                    findings.append(PrepFinding(name,f"Inconsistent date/time values: {col}","warning",bad,
                        "Parse consistently as a datetime while preserving unparseable values as null for review.",
                        "coerce_date",True))
            if (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)) and not _is_date_like(str(col)):
                ratio=_numeric_parse_ratio(s)
                nonblank=int(s.dropna().shape[0])
                if nonblank >= 10 and ratio >= .95 and ratio < 1:
                    bad=int(nonblank*(1-ratio))
                    findings.append(PrepFinding(name,f"Mixed numeric text: {col}","info",bad,
                        "Normalize numeric text (commas/currency symbols) where safely parseable.",
                        "coerce_numeric",True))
    return findings

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out=df.copy()
    seen=set(); cols=[]
    for raw in out.columns:
        n=str(raw).strip().replace("\n"," ").replace("\r"," ")
        n="_".join(n.split())
        if not n: n="unnamed_column"
        base=n; i=2
        while n.lower() in seen:
            n=f"{base}_{i}"; i+=1
        seen.add(n.lower()); cols.append(n)
    out.columns=cols
    return out

def prepare_raw_files(files: dict[str,pd.DataFrame], findings: list[PrepFinding]|None=None) -> tuple[dict[str,pd.DataFrame], list[dict[str,Any]]]:
    findings=findings or profile_raw(files)
    cleaned={}
    applied=[]
    for name, original in files.items():
        df=_normalize_columns(original)
        # trim strings and blank -> null
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                df[col]=df[col].astype("string").str.strip()
                df[col]=df[col].replace({"":pd.NA,"nan":pd.NA,"None":pd.NA})
        # Safe type normalization only for high-confidence columns.
        for col in list(df.columns):
            if _is_date_like(str(col)) and not pd.api.types.is_datetime64_any_dtype(df[col]):
                ratio=_date_parse_ratio(df[col])
                if ratio >= .90:
                    try:
                        df[col]=pd.to_datetime(df[col],errors="coerce",format="mixed")
                    except TypeError:
                        df[col]=pd.to_datetime(df[col],errors="coerce")
                    applied.append({"table":name,"action":f"Standardized datetime: {col}","rows":int(df[col].notna().sum())})
            elif (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])):
                ratio=_numeric_parse_ratio(df[col])
                nonblank=int(df[col].dropna().shape[0])
                if nonblank >= 10 and ratio >= .95:
                    x=df[col].astype("string").str.replace(",","",regex=False).str.replace("$","",regex=False)
                    parsed=pd.to_numeric(x,errors="coerce")
                    if parsed.notna().mean() >= .95:
                        df[col]=parsed
                        applied.append({"table":name,"action":f"Standardized numeric values: {col}","rows":int(parsed.notna().sum())})
        # Remove exact duplicates after normalization/type coercion so that
        # visually identical raw records become true duplicates.
        dup=int(df.duplicated(keep="first").sum())
        if dup:
            df=df.drop_duplicates(keep="first").reset_index(drop=True)
            applied.append({"table":name,"action":"Removed exact duplicates","rows":dup})
        cleaned[name]=df
    return cleaned, applied

def summary(files: dict[str,pd.DataFrame], findings: list[PrepFinding]) -> dict[str,Any]:
    return {
        "tables":len(files),
        "rows":sum(len(df) for df in files.values()),
        "columns":sum(len(df.columns) for df in files.values()),
        "findings":len(findings),
        "high_risk":sum(1 for f in findings if f.severity=="critical"),
        "warnings":sum(1 for f in findings if f.severity=="warning"),
    }
