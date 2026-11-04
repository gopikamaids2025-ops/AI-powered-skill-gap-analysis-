"""Resume Analysis: read a PDF/DOCX/TXT, extract information (rule-based) and run a simple quality check.

Extraction uses patterns and keywords. It is NOT 100% accurate, so the student always verifies and edits the result.
"""
from __future__ import annotations

import io
import re

from utils.helpers import install_hint
from utils.skill_database import detect_skills

try:
    from pypdf import PdfReader
except ImportError:  # shown to the user with an install command
    PdfReader = None
try:
    from docx import Document  # comes from the 'python-docx' package
except ImportError:
    Document = None


class ResumeReadError(Exception):
    """A problem with the uploaded file, written in plain language for the user."""


def read_document(upload) -> str:
    """Return the text of an uploaded PDF, DOCX or TXT file, or raise ResumeReadError with a friendly message."""
    name = (getattr(upload, "name", "") or "").lower()
    data = upload.getvalue()
    if not data:
        raise ResumeReadError("The uploaded file is empty.")
    try:
        if name.endswith(".pdf"):
            if PdfReader is None:
                raise ResumeReadError(f"PDF reading is not installed. Run this command, then restart the app: {install_hint('pypdf')}")
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted and not reader.decrypt(""):
                raise ResumeReadError("This PDF is password-protected. Remove the password or paste the text instead.")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        elif name.endswith(".docx"):
            if Document is None:
                raise ResumeReadError(f"DOCX reading is not installed. Run this command, then restart the app: {install_hint('python-docx')}")
            d = Document(io.BytesIO(data))
            parts = [p.text for sec in d.sections for p in sec.header.paragraphs]
            parts += [p.text for p in d.paragraphs]
            parts += [cell.text for t in d.tables for row in t.rows for cell in row.cells]
            text = "\n".join(p for p in parts if p.strip())
        elif name.endswith(".txt"):
            text = data.decode("utf-8", errors="ignore")
        else:
            raise ResumeReadError("Unsupported file type. Upload a PDF, DOCX or TXT file, or paste the text.")
    except ResumeReadError:
        raise
    except Exception as exc:  # damaged file, fake extension, etc.
        raise ResumeReadError(f"This file could not be read as a valid {name.rsplit('.', 1)[-1].upper()} ({type(exc).__name__}). "
                              "It may be damaged. Try another file or paste the text.") from exc
    if len(text.strip()) < 30:
        raise ResumeReadError("No readable text was found. Scanned (image-only) files are not supported, so please paste the text.")
    return text


# ---------------------------------------------------------------------------
# Quality check (rule-based score used only for the 'Resume score' feature and tips)
# ---------------------------------------------------------------------------
TECH_KEYWORDS = ["python", "java", "sql", "machine learning", "deep learning", "pandas", "numpy", "scikit-learn",
                 "tensorflow", "pytorch", "streamlit", "flask", "django", "html", "css", "javascript", "react",
                 "git", "github", "data structures", "algorithms", "power bi", "tableau", "excel", "mysql",
                 "mongodb", "docker", "linux", "nlp", "statistics", "data analysis", "api"]

SECTION_PATTERNS = {"Education": r"\beducation\b|\bb\.?\s?tech\b|\bbachelor|\bcgpa\b|\buniversity\b|\bcollege\b",
                    "Skills": r"\b(technical\s+)?skills\b", "Projects": r"\bprojects?\b",
                    "Internships / Experience": r"\binternships?\b|\bexperience\b|\bwork history\b",
                    "Certifications": r"\bcertificat", "Achievements": r"\bachievements?\b|\bawards?\b|\bhackathon"}

def analyze_resume(text: str) -> dict:
    low = text.lower()
    words = len(re.findall(r"\w+", text))
    email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))
    phone = bool(re.search(r"(\+?\d[\d\s\-()]{8,}\d)", text))
    github, linkedin = "github.com" in low, "linkedin.com" in low
    sections = {s: bool(re.search(pat, low)) for s, pat in SECTION_PATTERNS.items()}
    kws = [k for k in TECH_KEYWORDS if re.search(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", low)]
    numbers = len(re.findall(r"\d+\s?%|\b\d{2,}\b", text))
    length_pts = 10 if 300 <= words <= 900 else (5 if 150 <= words < 300 or 900 < words <= 1200 else 0)
    parts = {"Contact (email, phone)": (8 * email + 7 * phone, 15), "Education": (10 * sections["Education"], 10),
             "Skills section": (10 * sections["Skills"], 10), "Technical keywords": (min(len(kws) / 8, 1) * 10, 10),
             "Projects": (15 * sections["Projects"], 15), "Internships / Experience": (10 * sections["Internships / Experience"], 10),
             "Certifications": (5 * sections["Certifications"], 5), "GitHub link": (5 * github, 5),
             "LinkedIn link": (5 * linkedin, 5), "Length": (length_pts, 10),
             "Quantified impact": (5 if numbers >= 3 else 0, 5)}
    tips = []
    if not (email and phone):
        tips.append("Add a professional email and phone number at the top.")
    for s, found in sections.items():
        if not found and s != "Achievements":
            tips.append(f"Add a clear '{s}' section.")
    if not github:
        tips.append("Add your GitHub profile link.")
    if not linkedin:
        tips.append("Add your LinkedIn profile link.")
    if len(kws) < 8:
        tips.append("List more relevant technical keywords (languages, libraries, tools).")
    if words < 300:
        tips.append("The resume looks short; expand project and internship descriptions.")
    if words > 900:
        tips.append("The resume looks long; trim it to one or two pages.")
    if numbers < 3:
        tips.append("Quantify achievements (e.g. 'improved accuracy to 96%').")
    return dict(score=round(sum(v for v, _ in parts.values())), parts=parts, sections=sections, keywords=kws,
                contact={"Email": email, "Phone": phone, "GitHub": github, "LinkedIn": linkedin},
                words=words, tips=tips)


# ---------------------------------------------------------------------------
# Information extraction
# ---------------------------------------------------------------------------
BULLET = r"^[\s\W_]+"  # any leading bullet / dash / symbol (PDF bullets often become strange characters)
HEADING_WORDS = {"education", "details", "academic", "academics", "qualification", "qualifications", "background", "schooling",
                 "technical", "skills", "skill", "key", "core", "technologies", "technology", "tools", "and", "projects", "project",
                 "work", "personal", "professional", "experience", "internship", "internships", "training", "certifications",
                 "certification", "certificates", "certificate", "courses", "course", "licenses", "achievements", "achievement",
                 "awards", "award", "hackathons", "hackathon", "competitions", "competition", "extracurricular", "extra",
                 "curricular", "activities", "activity", "publications", "summary", "objective", "profile", "career", "about", "me",
                 "positions", "position", "responsibility", "responsibilities", "of", "programming", "languages", "proficiency",
                 "expertise", "interests", "interest", "declaration", "history", "employment", "relevant", "other", "additional",
                 "information", "the"}
HEADING_ORDER = [("hackathon|competition", "hackathons"), ("project", "projects"), ("internship", "internships"),
                 ("experience|employment|history|training|work", "experience"), ("certif|course|licen", "certifications"),
                 ("education|academic|qualification|schooling", "education"),
                 ("skill|technolog|tools|languages|proficienc|expertise", "skills"),
                 ("achievement|award|accomplish|extra|activit|publication|position|responsib|interest|declaration", "other"),
                 ("summary|objective|profile|about|career", "summary")]
DEGREE_RE = re.compile(r"\b(B\.?\s?Tech|(?-i:B\.\s?E\b|BE\b)|Bachelor[’']?s? of [A-Za-z ]+|Bachelor[’']?s?|B\.?\s?Sc|BCA|B\.?\s?Com|M\.?\s?Tech|(?-i:M\.\s?E\b|ME\b)|Master[’']?s? of [A-Za-z ]+|Master[’']?s?|M\.?\s?Sc|MCA|MBA|Diploma)\b", re.I)
COLLEGE_RE = re.compile(r"\b(college|university|institute|iit|nit|iiit|school of|academy|vit|srm|anna university)\b", re.I)
NAME_STOP = re.compile(r"resume|curriculum|vitae|profile|objective|summary|engineer|developer|student|email|phone|mobile|address|contact|"
                       r"linkedin|github|skills|education|projects?|experience|technical|details", re.I)
ACTION_VERB = re.compile(r"(built|developed|designed|implemented|created|used|using|worked|achieved|responsible|integrated|deployed|"
                         r"analy[sz]ed|performed|trained|collected|applied|improved|managed|led|wrote|tested|automated|reduced|increased|"
                         r"evaluated|explored|compared|engineered|leveraged|utilized|contributed|collaborated|cleaned|handled|assisted|"
                         r"supported|prepared|conducted|participated|organi[sz]ed)\b", re.I)
HACK_NEGATIVE = re.compile(r"interested in|interest in|plan to|planning to|want to|wants to|looking to|looking forward|eager|would like|upcoming|"
                           r"not participated|no hackathon|never|yet to", re.I)
HACK_POSITIVE = re.compile(r"participat|won\b|winner|finalist|secured|rank|runner|placed|took part|organi[sz]ed|awarded|prize|"
                           r"\b(?:first|second|third)\b|top \d+|built|developed|team", re.I)


def heading_key(line: str) -> str | None:
    """Section name if the line is a heading such as 'EDUCATION DETAILS' or 'Internship Experience:', else None."""
    if len(line) > 50 or "@" in line:
        return None
    words = re.sub(r"[^A-Za-z& ]", " ", line).lower().replace("&", " and ").split()
    if not words or len(words) > 6 or not all(w in HEADING_WORDS for w in words):
        return None
    joined = " ".join(words)
    return next((key for pat, key in HEADING_ORDER if re.search(pat, joined)), None)


def split_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = heading_key(re.sub(r"[:\-–—]+$", "", line).strip())
        if key:
            current = key
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return sections


def _clean(line: str) -> str:
    return re.sub(BULLET, "", line).strip()


def _is_bullet(line: str) -> bool:
    return bool(re.match(r"^\s*[•*▪●○◦‣\-–—]", line)) or bool(re.match(r"^\s*[^\w\s(+]", line))


def _group_entries(lines: list[str]) -> list[str]:
    """Group a section into entries: a header line (role/company/date) followed by its description lines."""
    entries: list[list[str]] = []
    for ln in lines:
        body = _clean(ln)
        if not body:
            continue
        is_header = (not _is_bullet(ln) and 8 <= len(body) <= 140 and not body.endswith(".") and not ACTION_VERB.match(body) and (
            re.search(r"\b(19|20)\d{2}\b", body) or re.search(
                r"intern|trainee|engineer|developer|analyst|associate|assistant|consultant|pvt|ltd|technologies|solutions|inc\b", body, re.I)))
        if is_header or not entries:
            entries.append([body])
        else:
            entries[-1].append(body)
    return [" | ".join(e)[:400] for e in entries]


def _looks_like_title(line: str) -> bool:
    """Project titles are short and mostly capitalised; description sentences are not."""
    body = _clean(re.sub(r"^\s*\d+[.)]\s*", "", line))
    if _is_bullet(line) or len(body) > 95 or body.endswith(".") or ACTION_VERB.match(body):
        return False
    if re.match(r"(tech(nolog(y|ies))?|tools?|stack|built with|environment|link|github|demo|role|duration|description)\b", body, re.I):
        return False
    if re.match(r"^\s*\d+[.)]\s", line) or re.search(r"\s[|–—]\s|\s-\s", body):
        return True
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]*", body)
    small = {"and", "of", "the", "for", "to", "in", "a", "an", "on", "with", "using", "by", "at"}
    major = [w for w in words if w.lower() not in small]
    return 1 <= len(words) <= 9 and bool(major) and sum(w[0].isupper() for w in major) / len(major) >= 0.6


def extract_hackathons(text: str, sections: dict[str, list[str]]) -> list[str]:
    """Only lines whose context shows participation. Interest/intent statements and bare mentions are ignored."""
    found: list[str] = []
    for ln in sections.get("hackathons", []):
        body = _clean(ln)
        if len(body) >= 6 and not HACK_NEGATIVE.search(body):
            found.append(body[:160])
    for ln in text.splitlines():
        body = _clean(ln)
        if re.search(r"hackathon", body, re.I) and HACK_POSITIVE.search(body) and not HACK_NEGATIVE.search(body) and body[:160] not in found:
            found.append(body[:160])
    return found[:6]


def _find_name(lines: list[str]) -> str:
    for n, ln in enumerate(lines[:8]):
        cand = re.sub(r"^\s*name\s*[:\-]\s*", "", re.split(r"\s*[|•·,/@]\s*|\s{2,}|\d", ln)[0], flags=re.I).strip()
        words = cand.split()
        if (1 <= len(words) <= 4 and (len(words) > 1 or n == 0) and re.fullmatch(r"[A-Za-z.'\- ]+", cand)
                and not NAME_STOP.search(cand) and not heading_key(cand)):
            return cand.title() if cand.isupper() and len(words) > 1 else cand
    return ""


def extract_resume_info(text: str) -> dict:
    """Pull structured information out of resume text. Empty values mean 'not detected'."""
    sec = split_sections(text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    info = {"name": "", "email": "", "phone": "", "linkedin": "", "github": "", "degree": "", "department": "", "college": "",
            "cgpa": "", "skills": [], "internships": [], "experience": [], "projects": [], "certifications": [], "hackathons": [], "other": ""}
    m = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    info["email"] = m.group(0) if m else ""
    for cand in re.findall(r"\+?\d[\d\s().-]{8,}\d", text):
        digits = re.sub(r"\D", "", cand)
        if 10 <= len(digits) <= 13 and not re.fullmatch(r"(19|20)\d{2}\D*(19|20)\d{2}", cand.strip()):
            info["phone"] = cand.strip()
            break
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|pub)/[\w\-%/]+", text, re.I)
    info["linkedin"] = m.group(0).rstrip("/") if m else ""
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", text, re.I)
    info["github"] = m.group(0) if m else ""
    info["name"] = _find_name(lines)
    # --- education
    edu_lines = sec.get("education") or lines
    for ln in edu_lines:
        dm = DEGREE_RE.search(ln)
        if dm:
            info["degree"] = ln[:110]
            rest = re.sub(r"^(in|of)\s+", "", ln[dm.end():].strip(" .:-–—,"), flags=re.I)
            dep = re.split(r"\s+[-–—|]\s+|,|\(|\d{4}", rest)[0].strip()
            info["department"] = dep if 3 <= len(dep) <= 60 and not COLLEGE_RE.search(dep) else ""
            break
    for ln in edu_lines:
        if COLLEGE_RE.search(ln) and not re.search(r"higher secondary|\bhsc\b|\bssc\b|matriculation|10th|12th", ln, re.I):
            info["college"] = ln[:110]
            break
    for ln in edu_lines + lines:
        m = (re.search(r"(?:cgpa|gpa)\s*(?:of|is|[:\-–=])?\s*(\d{1,2}(?:\.\d{1,2})?)", ln, re.I)
             or re.search(r"(\d{1,2}(?:\.\d{1,2})?)\s*(?:/\s*10\b|cgpa|gpa)", ln, re.I))
        if m and 0 < float(m.group(1)) <= 10:
            info["cgpa"] = m.group(1)
            break
    # --- skills: the degree / college lines are skipped so that "Data Science" in a degree name is not counted as a skill
    info["skills"] = detect_skills("\n".join(ln for ln in lines if not (DEGREE_RE.search(ln) or COLLEGE_RE.search(ln))))
    # --- internships: everything under an "Internships" heading; under "Experience" only entries that say "intern"
    intern_entries = _group_entries(sec.get("internships", []))
    exp_entries = _group_entries(sec.get("experience", []))
    info["internships"] = intern_entries + [e for e in exp_entries if re.search(r"\bintern(ship)?s?\b", e.split(" | ")[0], re.I)]
    info["experience"] = [e for e in exp_entries if e not in info["internships"]]
    # --- projects
    projects: list[dict] = []
    for ln in sec.get("projects", []):
        body = _clean(re.sub(r"^\s*\d+[.)]\s*", "", ln))
        if not body:
            continue
        if _looks_like_title(ln) or not projects:
            projects.append({"name": re.split(r"\s+[|–—]\s+|\s+-\s+|:\s|\s*\(", body)[0].strip(" :-"), "block": body})
        else:
            projects[-1]["block"] += " " + body
    info["projects"] = [{"name": p["name"], "tech": detect_skills(p["block"]), "detail": p["block"][:300]} for p in projects if p["name"]]
    # --- certifications and hackathons
    certs = [_clean(ln) for ln in sec.get("certifications", [])]
    if not certs:
        certs = [_clean(ln) for ln in lines if re.search(r"certif", ln, re.I) and len(ln) < 140 and not heading_key(ln)]
    info["certifications"] = [c[:140] for c in certs if len(c) >= 4][:10]
    info["hackathons"] = extract_hackathons(text, sec)
    info["other"] = "; ".join(_clean(ln) for ln in sec.get("other", [])[:5])[:400]
    return info


def cgpa_number(info: dict) -> float | None:
    """CGPA as a number on a 10-point scale, or None (percentages are never converted automatically)."""
    raw = str(info.get("cgpa", "")).strip()
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if 0 < v <= 10 else None
