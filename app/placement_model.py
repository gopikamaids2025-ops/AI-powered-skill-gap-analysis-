"""Placement Readiness: the EXISTING trained ML model and scaler (never retrained or changed here).

Pipeline:  student values -> DataFrame (exact training feature order) -> scaler -> trained model -> label + confidence.

Two kinds of numeric limits are used and they are kept apart on purpose:
  VALID range     what a real value can be (for example Attendance 0-100). Streamlit input boxes use this, so a real
                  student value is never changed and the form can never crash.
  TRAINING range  the min/max found in the training dataset. A value outside it is still accepted, but the app shows a
                  clear warning because the model has never seen such values and its output is less reliable.
"""
from __future__ import annotations

import joblib
import pandas as pd
import streamlit as st

from utils.helpers import find_file

# Order used when the model was trained (verified against scaler.feature_names_in_ and the dataset at start-up).
FEATURES = ["CGPA", "Attendance", "Aptitude_Score", "Coding_Score", "DSA_Score", "SQL_Score", "Python_Score", "Communication",
            "Soft_Skills", "Projects", "Internships", "Certifications", "Resume_Score", "Mock_Interview", "Hackathon",
            "GitHub_Score", "LeetCode_Solved"]
NON_FEATURES = ("Student_ID", "Placement_Ready")

# key: (label, valid_min, valid_max, step, python type)
FEATURE_SPECS = {
    "CGPA": ("CGPA (out of 10)", 0.0, 10.0, 0.01, float), "Attendance": ("Attendance (%)", 0, 100, 1, int),
    "Aptitude_Score": ("Aptitude score", 0, 100, 1, int), "Coding_Score": ("Coding score", 0, 100, 1, int),
    "DSA_Score": ("DSA score", 0, 100, 1, int), "SQL_Score": ("SQL score", 0, 100, 1, int),
    "Python_Score": ("Python score", 0, 100, 1, int), "GitHub_Score": ("GitHub score", 0, 100, 1, int),
    "LeetCode_Solved": ("LeetCode problems solved", 0, 10000, 1, int), "Communication": ("Communication", 0, 100, 1, int),
    "Soft_Skills": ("Soft skills", 0, 100, 1, int), "Projects": ("Projects", 0, 50, 1, int),
    "Internships": ("Internships", 0, 20, 1, int), "Certifications": ("Certifications", 0, 50, 1, int),
    "Resume_Score": ("Resume score", 0, 100, 1, int), "Mock_Interview": ("Mock interview score", 0, 100, 1, int),
}
LABELS = {k: v[0] for k, v in FEATURE_SPECS.items()} | {"Hackathon": "Hackathon participation"}
SECTIONS = {"Academic": ["CGPA", "Attendance", "Aptitude_Score"],
            "Technical": ["Coding_Score", "DSA_Score", "SQL_Score", "Python_Score", "GitHub_Score", "LeetCode_Solved"],
            "Soft skills": ["Communication", "Soft_Skills"],
            "Career": ["Projects", "Internships", "Certifications", "Resume_Score", "Mock_Interview"]}
# Used ONLY if the training dataset file is missing (values measured from the 1,000-row training dataset).
TRAINING_FALLBACK = {"CGPA": (6.01, 9.8), "Attendance": (70, 100), "Aptitude_Score": (40, 100), "Coding_Score": (35, 100),
                     "DSA_Score": (30, 100), "SQL_Score": (30, 100), "Python_Score": (35, 100), "Communication": (40, 100),
                     "Soft_Skills": (40, 100), "Projects": (0, 6), "Internships": (0, 2), "Certifications": (0, 6),
                     "Resume_Score": (40, 100), "Mock_Interview": (35, 100), "GitHub_Score": (0, 100), "LeetCode_Solved": (0, 500)}


@st.cache_resource(show_spinner=False)
def load_artifacts():
    """Load model + scaler unchanged and verify they agree with the training dataset. Returns (model, scaler, info)."""
    info = {"ok": False, "error": None, "notes": []}
    model_path, scaler_path = find_file("placement_model.pkl"), find_file("scaler.pkl")
    if model_path is None or scaler_path is None:
        info["error"] = "placement_model.pkl and/or scaler.pkl were not found in the models/ folder."
        return None, None, info
    try:
        model, scaler = joblib.load(model_path), joblib.load(scaler_path)
        order = list(getattr(scaler, "feature_names_in_", FEATURES))
        if sorted(order) != sorted(FEATURES):
            raise ValueError(f"The scaler expects these features: {order}. They do not match this application's feature list.")
        if getattr(model, "n_features_in_", len(order)) != len(order):
            raise ValueError("The model and scaler expect a different number of features.")
        info.update(ok=True, model_path=str(model_path), scaler_path=str(scaler_path), feature_order=order,
                    has_proba=hasattr(model, "predict_proba"), hackathon_yes=1)
        df, _ = load_dataset()
        if df is not None:
            cols = [c for c in df.columns if c not in NON_FEATURES]
            info["order_check"] = "Feature order matches the training dataset" if cols == order else "WARNING: dataset column order differs from the scaler"
            if cols != order:
                info["notes"].append("The scaler's stored order is used, which is the order the model was trained with.")
            if hasattr(scaler, "mean_") and "Hackathon" in order:
                yes_share = float((df["Hackathon"] == 1).mean())
                mean = float(scaler.mean_[order.index("Hackathon")])
                if abs(mean - yes_share) > 0.1 and abs(mean - (1 - yes_share)) < 0.1:
                    info["hackathon_yes"] = 0  # training used the opposite encoding
                info["hackathon_check"] = f"Hackathon: Yes = {info['hackathon_yes']} (scaler mean {mean:.3f}, dataset Yes share {yes_share:.3f})"
        else:
            info["order_check"] = "Training dataset not found - using the order stored inside the scaler"
        return model, scaler, info
    except Exception as exc:  # noqa: BLE001 - shown to the user in plain text
        info["error"] = f"{type(exc).__name__}: {exc}"
        return None, None, info


@st.cache_data(show_spinner=False)
def load_dataset():
    path = find_file("placement_dataset.csv", "AI_Powered_Skill_Gap_Placement_Dataset_1000.xlsx")
    if path is None:
        return None, None
    try:
        df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_excel(path)
        if df["Hackathon"].dtype == object or str(df["Hackathon"].dtype).startswith("str"):
            df["Hackathon"] = df["Hackathon"].map({"Yes": 1, "No": 0})
        return df, str(path)
    except Exception:  # noqa: BLE001 - a missing dataset is not fatal
        return None, str(path)


def training_ranges() -> tuple[dict, str]:
    df, _ = load_dataset()
    if df is not None and all(f in df.columns for f in FEATURES):
        return {f: (float(df[f].min()), float(df[f].max())) for f in FEATURES if f != "Hackathon"}, "training dataset"
    return dict(TRAINING_FALLBACK), "built-in copy of the training ranges (dataset file not found)"


def missing_values(ml: dict) -> list[str]:
    return [f for f in FEATURES if ml.get(f) is None]


def check_value(key: str, value) -> tuple[object | None, str | None]:
    """Validate ONE value against its VALID range. Returns (clean value, problem). Never clamps or edits the value."""
    if value is None or key == "Hackathon":
        return value, None
    _, lo, hi, _, typ = FEATURE_SPECS[key]
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None, f"{LABELS[key]}: '{value}' is not a number."
    if not lo <= v <= hi:
        return None, f"{LABELS[key]}: {v:g} is outside the allowed range {lo:g}-{hi:g}."
    if typ is int and v != int(v):
        return None, f"{LABELS[key]}: {v:g} must be a whole number."
    return typ(v), None


def range_warnings(ml: dict) -> list[dict]:
    """Values that are valid but outside what the model saw in training."""
    ranges, _ = training_ranges()
    out = []
    for f, (lo, hi) in ranges.items():
        v = ml.get(f)
        if v is not None and not lo <= v <= hi:
            out.append({"field": LABELS[f], "value": v, "lo": lo, "hi": hi})
    return out


def predict(ml: dict) -> dict | None:
    """Student values -> DataFrame (exact training order) -> scaler -> model. None if inputs or model are not usable."""
    model, scaler, info = load_artifacts()
    if not info["ok"] or missing_values(ml):
        return None
    try:
        row = {f: float(ml[f]) for f in FEATURES}
        yes = info.get("hackathon_yes", 1)
        row["Hackathon"] = float(yes if ml["Hackathon"] else 1 - yes)
        X = scaler.transform(pd.DataFrame([row], columns=info["feature_order"]))
        label = int(model.predict(X)[0])
        p_ready = None
        if info["has_proba"]:
            p_ready = float(model.predict_proba(X)[0][list(model.classes_).index(1)]) * 100
        contrib = None
        if hasattr(model, "coef_") and model.coef_.shape[0] == 1:
            contrib = pd.DataFrame({"Feature": [LABELS[f] for f in info["feature_order"]], "Contribution": model.coef_[0] * X[0]})
        confidence = None if p_ready is None else (p_ready if label == 1 else 100 - p_ready)
        return {"label": label, "p_ready": p_ready, "confidence": confidence, "contrib": contrib, "warnings": range_warnings(ml)}
    except Exception as exc:  # noqa: BLE001
        st.error(f"The prediction could not be calculated: {exc}")
        return None


# ---------------------------------------------------------------------------
# Optional company benchmark (company_requirements.csv). Separate from the job analysis.
# ---------------------------------------------------------------------------
REQ_MAP = {"Min_CGPA": ("CGPA", "CGPA"), "Min_Coding": ("Coding score", "Coding_Score"), "Min_DSA": ("DSA score", "DSA_Score"),
           "Min_SQL": ("SQL score", "SQL_Score"), "Min_Python": ("Python score", "Python_Score"),
           "Min_Projects": ("Projects", "Projects"), "Min_Internships": ("Internships", "Internships")}


@st.cache_data(show_spinner=False)
def load_companies():
    path = find_file("company_requirements.csv")
    if path is None:
        return None
    try:
        df = pd.read_csv(path)
        return df if "Company" in df.columns and any(c in df.columns for c in REQ_MAP) else None
    except Exception:  # noqa: BLE001
        return None


def evaluate_companies(ml: dict) -> list[dict] | None:
    df = load_companies()
    if df is None:
        return None
    out = []
    for _, c in df.iterrows():
        reqs, unknown = [], []
        for col, (label, key) in REQ_MAP.items():
            if col in df.columns and pd.notna(c[col]):
                if ml.get(key) is None:
                    unknown.append(label)
                else:
                    reqs.append((label, float(ml[key]), float(c[col])))
        missing = [r for r in reqs if r[1] < r[2]]
        match = 100 * sum(min(cur / req, 1) if req > 0 else 1 for _, cur, req in reqs) / len(reqs) if reqs else None
        out.append(dict(company=c["Company"], status="Incomplete profile" if unknown else ("Eligible" if not missing else "Not eligible"),
                        match=match, missing=missing, unknown=unknown))
    return sorted(out, key=lambda r: (r["status"] != "Eligible", -(r["match"] or 0)))