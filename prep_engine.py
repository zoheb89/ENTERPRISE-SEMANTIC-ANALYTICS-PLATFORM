
"""
Capgemini DataPrepAI — deterministic raw-data preparation and quality profiling.

Design goals:
- Treat source data as untrusted/raw until profiled.
- Detect explainable, column-level quality issues.
- Separate safe deterministic preparation from business/semantic decisions.
- Never invent business values or silently delete non-duplicate business records.
- Referential-integrity findings belong to semantic validation, not cleansing.
"""
from __future__ import annotations
from dataclasses import dataclass
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
    category: str = "Data Quality"

def _is_date_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return any(k in n for k in ("date","datetime","timestamp","time","dob","birthdate","servicedate"))

def _is_year_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return "year" in n or n in {"yr","modelyear","manufactureyear"}

def _is_bool_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return n in {"active","enabled","isactive","isvalid","flag","statusflag"} or n.endswith("flag")

def _is_pii_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return any(k in n for k in (
        "email","emailaddress","phone","phonenumber","mobile","mobilephone",
        "customername","fullname","firstname","lastname","address","ssn",
        "passport","nationalid","aadhaar","aadhar","dob","dateofbirth"
    ))

def _is_money_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return any(k in n for k in ("cost","price","amount","revenue","salary","fee","value","total"))

def _date_parse_ratio(s: pd.Series) -> float:
    x = s.dropna().astype(str).str.strip()
    x = x[x.ne("")]
    if x.empty:
        return 0.0
    try:
        parsed = pd.to_datetime(x, errors="coerce", format="mixed")
    except TypeError:
        parsed = pd.to_datetime(x, errors="coerce")
    return float(parsed.notna().mean())

def _numeric_parse_ratio(s: pd.Series) -> float:
    x = s.dropna().astype(str).str.strip()
    x = x[x.ne("")]
    if x.empty:
        return 0.0
    x = x.str.replace(r"[$₹€£]", "", regex=True).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    parsed = pd.to_numeric(x, errors="coerce")
    return float(parsed.notna().mean())

def _numeric_bad_rows(s: pd.Series) -> int:
    x = s.dropna().astype(str).str.strip()
    x = x[x.ne("")]
    if x.empty:
        return 0
    clean = x.str.replace(r"[$₹€£]", "", regex=True).str.replace(",", "", regex=False).str.replace("%", "", regex=False)
    return int(pd.to_numeric(clean, errors="coerce").isna().sum())

def _currency_rows(s: pd.Series) -> int:
    x = s.astype("string")
    return int(x.str.contains(r"[$₹€£]", regex=True, na=False).sum())

def _whitespace_rows(s: pd.Series) -> int:
    if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
        return 0
    x=s.astype("string")
    return int((x.notna() & x.ne(x.str.strip())).sum())

def _blank_rows(s: pd.Series) -> int:
    if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
        return 0
    return int(s.astype("string").str.strip().eq("").sum())

def _case_variant_rows(s: pd.Series) -> int:
    if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
        return 0
    x=s.dropna().astype(str).str.strip()
    if x.empty:
        return 0
    groups={}
    for v in x:
        groups.setdefault(v.casefold(), set()).add(v)
    variants={k for k,v in groups.items() if len(v)>1}
    return int(x.str.casefold().isin(variants).sum())

def _bool_inconsistency(s: pd.Series) -> tuple[int,list[str]]:
    x=s.dropna().astype(str).str.strip().str.casefold()
    if x.empty: return 0,[]
    canonical={"true","false","yes","no","y","n","1","0","t","f"}
    vals=sorted(set(x))
    if not set(vals).issubset(canonical):
        return 0, vals
    true_forms={"true","t","yes","y","1"}
    false_forms={"false","f","no","n","0"}
    true_seen=sorted(set(vals) & true_forms)
    false_seen=sorted(set(vals) & false_forms)
    # Multiple textual representations of the same boolean are a quality issue.
    if len(true_seen)>1 or len(false_seen)>1:
        return int(len(x)), vals
    return 0, vals

def _year_bad_rows(s: pd.Series) -> int:
    x=s.dropna().astype(str).str.strip()
    if x.empty: return 0
    # Accept four-digit years in a reasonable operational range.
    return int((~x.str.fullmatch(r"(19|20)\d{2}")).sum())

def profile_raw(files: dict[str, pd.DataFrame]) -> list[PrepFinding]:
    findings=[]
    for name, df in files.items():
        nrows=max(len(df),1)

        # Exact duplicates on the raw source.
        dup=int(df.duplicated(keep="first").sum())
        if dup:
            findings.append(PrepFinding(
                name,"Exact duplicate rows","warning",dup,
                "Remove exact duplicate records while preserving the first occurrence.",
                "drop_exact_duplicates",True,"Duplicates"))
        else:
            # Also identify records that become identical after only safe,
            # deterministic normalization (for example whitespace trimming).
            normalized=_normalize_columns(df)
            for c in normalized.columns:
                if pd.api.types.is_object_dtype(normalized[c]) or pd.api.types.is_string_dtype(normalized[c]):
                    normalized[c]=normalized[c].astype("string").str.strip().replace({"":pd.NA})
            normalized_dup=int(normalized.duplicated(keep="first").sum())
            if normalized_dup:
                findings.append(PrepFinding(
                    name,"Duplicate rows after safe normalization","warning",normalized_dup,
                    "Review records that become identical after deterministic normalization; only exact duplicates are eligible for automatic removal.",
                    "drop_exact_duplicates",True,"Duplicates"))

        for col in df.columns:
            colname=str(col)
            s=df[col]

            # Structural whitespace in values.
            ws=_whitespace_rows(s)
            if ws:
                findings.append(PrepFinding(
                    name,f"Leading/trailing whitespace: {colname}","info",ws,
                    "Trim surrounding whitespace before semantic analysis.",
                    "trim_whitespace",True,"Standardization"))

            # Blank strings.
            blanks=_blank_rows(s)
            if blanks:
                findings.append(PrepFinding(
                    name,f"Blank string values: {colname}","warning",blanks,
                    "Convert whitespace-only values to null and expose missingness for review.",
                    "blank_to_null",True,"Missingness"))

            nulls=int(s.isna().sum())
            if nulls and nulls/nrows >= .30:
                findings.append(PrepFinding(
                    name,f"Null-heavy column: {colname}","warning",nulls,
                    "Review whether the column is sufficiently populated for the semantic model.",
                    "review_missingness",False,"Missingness"))

            # Inconsistent categorical casing.
            cv=_case_variant_rows(s)
            if cv:
                findings.append(PrepFinding(
                    name,f"Inconsistent text casing: {colname}","warning",cv,
                    "Normalize casing only where a deterministic canonical form is known; otherwise review.",
                    "normalize_text_case",True,"Standardization"))

            # PII indicator — security review, never auto-mask here.
            if _is_pii_like(colname):
                nonnull=int(s.notna().sum())
                if nonnull:
                    findings.append(PrepFinding(
                        name,f"Potential PII/PHI column: {colname}","warning",nonnull,
                        "Route to Security Center for masking/access review. Do not auto-mask without approval.",
                        "security_review",False,"Security"))

            # Dates: report invalid values separately from missingness.
            if _is_date_like(colname) and not pd.api.types.is_datetime64_any_dtype(s):
                ratio=_date_parse_ratio(s)
                if ratio < 1.0 and int(s.dropna().shape[0]) > 0:
                    bad=_numeric_bad_rows(s) if False else int(s.dropna().shape[0] * (1-ratio))
                    # Use exact invalid count from parser.
                    x=s.dropna().astype(str).str.strip()
                    try:
                        parsed=pd.to_datetime(x,errors="coerce",format="mixed")
                    except TypeError:
                        parsed=pd.to_datetime(x,errors="coerce")
                    bad=int(parsed.isna().sum())
                    if bad:
                        findings.append(PrepFinding(
                            name,f"Invalid date/time values: {colname}","warning",bad,
                            "Standardize parseable dates; keep invalid values visible for review rather than inventing a date.",
                            "coerce_date",True,"Dates"))

            # Year fields: identify malformed year tokens.
            if _is_year_like(colname):
                bad=_year_bad_rows(s)
                if bad:
                    findings.append(PrepFinding(
                        name,f"Invalid year values: {colname}","warning",bad,
                        "Keep only valid four-digit years; review malformed values before publishing.",
                        "review_year",False,"Dates"))

            # Numeric/money fields. Detect currency and comma formatting even
            # when there are fewer than ten rows.
            if (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)) and not _is_year_like(colname):
                currency=_currency_rows(s)
                if currency and _is_money_like(colname):
                    findings.append(PrepFinding(
                        name,f"Currency-formatted numeric values: {colname}","info",currency,
                        "Normalize currency symbols and thousands separators into a numeric representation.",
                        "coerce_numeric",True,"Numeric"))

                nonblank=int(s.dropna().shape[0])
                if nonblank:
                    ratio=_numeric_parse_ratio(s)
                    bad=_numeric_bad_rows(s)
                    if bad and (ratio >= .50 or _is_money_like(colname)):
                        findings.append(PrepFinding(
                            name,f"Non-numeric values in numeric candidate: {colname}","warning",bad,
                            "Convert safely parseable numeric text; review values that cannot be parsed.",
                            "coerce_numeric",True,"Numeric"))

            # Boolean/status flag consistency.
            if _is_bool_like(colname):
                count, vals=_bool_inconsistency(s)
                if count:
                    findings.append(PrepFinding(
                        name,f"Inconsistent boolean representations: {colname}","warning",count,
                        "Map equivalent values such as Yes/Y/TRUE and No/N/FALSE to a canonical boolean after review.",
                        "normalize_boolean",True,"Standardization"))

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

def _canonical_bool(s: pd.Series) -> pd.Series:
    mapping={"true":True,"t":True,"yes":True,"y":True,"1":True,
             "false":False,"f":False,"no":False,"n":False,"0":False}
    x=s.astype("string").str.strip().str.casefold()
    return x.map(mapping).astype("boolean")

def prepare_raw_files(files: dict[str,pd.DataFrame], findings: list[PrepFinding]|None=None) -> tuple[dict[str,pd.DataFrame], list[dict[str,Any]]]:
    findings=findings or profile_raw(files)
    cleaned={}
    applied=[]
    for name, original in files.items():
        df=_normalize_columns(original)

        for col in list(df.columns):
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                before=_whitespace_rows(df[col])
                if before:
                    df[col]=df[col].astype("string").str.strip()
                    applied.append({"table":name,"action":f"Trimmed whitespace: {col}","rows":before,"category":"Standardization"})
                df[col]=df[col].replace({"":pd.NA,"nan":pd.NA,"None":pd.NA})

        for col in list(df.columns):
            if _is_bool_like(str(col)) and (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])):
                vals=df[col].dropna().astype(str).str.strip().str.casefold()
                if not vals.empty and set(vals).issubset({"true","false","t","f","yes","no","y","n","1","0"}):
                    df[col]=_canonical_bool(df[col])
                    applied.append({"table":name,"action":f"Standardized boolean values: {col}","rows":int(df[col].notna().sum()),"category":"Standardization"})

            elif _is_date_like(str(col)) and not pd.api.types.is_datetime64_any_dtype(df[col]):
                ratio=_date_parse_ratio(df[col])
                if ratio >= .50:
                    try: parsed=pd.to_datetime(df[col],errors="coerce",format="mixed")
                    except TypeError: parsed=pd.to_datetime(df[col],errors="coerce")
                    if parsed.notna().sum() > 0:
                        df[col]=parsed
                        applied.append({"table":name,"action":f"Standardized datetime: {col}","rows":int(parsed.notna().sum()),"category":"Dates"})

            elif (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])):
                ratio=_numeric_parse_ratio(df[col])
                nonblank=int(df[col].dropna().shape[0])
                if nonblank and (ratio >= .80 or _is_money_like(str(col))):
                    x=df[col].astype("string").str.replace(r"[$₹€£]", "", regex=True).str.replace(",","",regex=False).str.replace("%","",regex=False).str.strip()
                    parsed=pd.to_numeric(x,errors="coerce")
                    if parsed.notna().sum() > 0 and parsed.notna().mean() >= .50:
                        df[col]=parsed
                        applied.append({"table":name,"action":f"Standardized numeric values: {col}","rows":int(parsed.notna().sum()),"category":"Numeric"})

        # Exact duplicates are evaluated after deterministic normalization.
        dup=int(df.duplicated(keep="first").sum())
        if dup:
            df=df.drop_duplicates(keep="first").reset_index(drop=True)
            applied.append({"table":name,"action":"Removed exact duplicates","rows":dup,"category":"Duplicates"})

        cleaned[name]=df
    return cleaned, applied

def summary(files: dict[str,pd.DataFrame], findings: list[PrepFinding]) -> dict[str,Any]:
    return {
        "tables":len(files),
        "rows":sum(len(df) for df in files.values()),
        "columns":sum(len(df.columns) for df in files.values()),
        "findings":len(findings),
        "critical":sum(1 for f in findings if f.severity=="critical"),
        "warnings":sum(1 for f in findings if f.severity=="warning"),
        "info":sum(1 for f in findings if f.severity=="info"),
        "auto_safe":sum(1 for f in findings if f.auto_safe),
        "review_required":sum(1 for f in findings if not f.auto_safe),
    }
