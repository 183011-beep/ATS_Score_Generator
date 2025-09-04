import streamlit as st
import docx2txt
import PyPDF2
import re
from collections import Counter

# ---------------------------
# File text extraction
# ---------------------------
def extract_text(uploaded_file):
    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if uploaded_file.name.lower().endswith(".docx"):
        return docx2txt.process(uploaded_file)
    # txt fallback
    return uploaded_file.read().decode("utf-8", errors="ignore")

# ---------------------------
# Helpers
# ---------------------------
def normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[\W_]+', ' ', s)  # keep letters/numbers/space
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def find_years(text: str):
    """
    Returns (min_years, max_years) for JD, or single numeric for resume.
    """
    # ranges like "2–4 years", "2-4 years", "2 to 4 years"
    m = re.search(r'(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:yrs?|years?)', text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    # "3+ years", "at least 3 years"
    m = re.search(r'(?:at\s+least\s+)?(\d+)\s*\+?\s*(?:yrs?|years?)', text)
    if m:
        a = int(m.group(1))
        return a, None

    return None, None

def find_resume_years(text: str):
    # simple heuristic: first "X years/yrs" mentioned
    m = re.search(r'(\d+)\s*\+?\s*(?:yrs?|years?)', text)
    return int(m.group(1)) if m else None

def extract_required_sets(jd_norm: str):
    # lexicons (customize as you like)
    SKILL_POOL = {
        "python", "sql", "excel", "tableau", "java", "nlp", "machine learning",
        "deep learning", "statistics", "power bi", "powerbi"
    }
    TOOL_POOL = {"aws", "git", "jira", "docker", "power bi", "powerbi", "tableau"}
    SOFT_POOL = {"communication", "teamwork", "problem solving", "leadership", "analytical"}

    EDU_POOL = {
        "b tech", "btech", "bachelor", "bachelors", "master", "masters",
        "mtech", "mca", "mba", "b sc", "bsc", "computer science", "statistics"
    }

    def pick(pool):
        # keep any lexicon items that actually appear in the JD
        found = set()
        for kw in pool:
            if kw in jd_norm:
                found.add(kw)
        return found

    req_skills = pick(SKILL_POOL)
    req_tools = pick(TOOL_POOL)
    req_soft  = pick(SOFT_POOL)
    req_edu   = pick(EDU_POOL)

    jd_min_yrs, jd_max_yrs = find_years(jd_norm)

    return req_skills, req_tools, req_soft, req_edu, jd_min_yrs, jd_max_yrs

def contains_any(text: str, items: set):
    return {k for k in items if k in text}

def pct(numer, denom):
    if denom <= 0:
        return 1.0  # if JD doesn’t require that category, give full credit
    return max(0.0, min(1.0, numer / denom))

# ---------------------------
# Main scoring
# ---------------------------
def score_resume(jd_text: str, resume_text: str):
    jd_norm = normalize(jd_text)
    res_norm = normalize(resume_text)

    # Extract requirements from JD
    req_skills, req_tools, req_soft, req_edu, jd_min_yrs, jd_max_yrs = extract_required_sets(jd_norm)

    # Category weights
    WEIGHTS = {
        "skills": 30,
        "experience": 20,
        "tools": 15,
        "education": 10,
        "soft_skills": 10,
        "achievements": 5,
        "formatting": 5,
        "keywords": 5
    }

    # --- Skills / Tools / Soft skills ---
    matched_skills = contains_any(res_norm, req_skills)
    matched_tools  = contains_any(res_norm, req_tools)
    matched_soft   = contains_any(res_norm, req_soft)

    skills_pct = pct(len(matched_skills), len(req_skills))
    tools_pct  = pct(len(matched_tools), len(req_tools))
    soft_pct   = pct(len(matched_soft), len(req_soft))

    # --- Education ---
    if req_edu:
        edu_match = contains_any(res_norm, req_edu)
        edu_pct = 1.0 if edu_match else 0.0
    else:
        edu_pct = 1.0  # no explicit education requirement

    # --- Experience (years closeness) ---
    res_years = find_resume_years(res_norm)
    if jd_min_yrs is None and jd_max_yrs is None:
        exp_pct = 1.0  # JD didn't specify years
    elif res_years is None:
        exp_pct = 0.0
    else:
        if jd_max_yrs is not None:
            # full if inside range; taper if outside
            if jd_min_yrs <= res_years <= jd_max_yrs:
                exp_pct = 1.0
            else:
                # distance penalty
                dist = min(abs(res_years - jd_min_yrs), abs(res_years - jd_max_yrs))
                exp_pct = max(0.2, 1.0 - 0.15 * dist)
        else:
            # "X+ years": full if >= X, partial if below
            if res_years >= jd_min_yrs:
                exp_pct = 1.0
            else:
                gap = jd_min_yrs - res_years
                exp_pct = max(0.2, 1.0 - 0.2 * gap)

    # --- Achievements (action verbs + numbers/%) ---
    ACTION_VERBS = {"delivered","implemented","improved","increased","reduced","optimized","automated","designed","built","developed","managed"}
    has_action = any(v in res_norm for v in ACTION_VERBS)
    has_number = bool(re.search(r'\b\d+(\.\d+)?\s*(%|k|m|million|billion)?\b', res_norm))
    ach_pct = 1.0 if (has_action and has_number) else (0.5 if (has_action or has_number) else 0.0)

    # --- Formatting (sections present) ---
    sections = sum(s in res_norm for s in ["experience","education","skills"])
    fmt_pct = sections / 3.0

    # --- Keywords usage (JD vocab coverage) ---
    STOP = {"and","or","the","a","an","to","for","of","in","on","with","we","are","is","be","as","by","you","our","your"}
    jd_tokens = [t for t in jd_norm.split() if t not in STOP and len(t) > 2]
    jd_counts = Counter(jd_tokens)
    top_jd = {w for w, _ in jd_counts.most_common(30)}  # top signal words
    kw_hits = contains_any(res_norm, top_jd)
    kw_pct = pct(len(kw_hits), len(top_jd))

    # Assemble category points
    cat_pct = {
        "skills": skills_pct,
        "experience": exp_pct,
        "tools": tools_pct,
        "education": edu_pct,
        "soft_skills": soft_pct,
        "achievements": ach_pct,
        "formatting": fmt_pct,
        "keywords": kw_pct,
    }

    cat_points = {k: round(v * WEIGHTS[k], 2) for k, v in cat_pct.items()}
    final_score = round(sum(cat_points.values()), 2)

    # Gap analysis
    gaps = {
        "missing_skills": sorted(req_skills - matched_skills),
        "missing_tools": sorted(req_tools - matched_tools),
        "missing_soft_skills": sorted(req_soft - matched_soft),
        "education_required": sorted(req_edu) if req_edu else [],
        "years_required": (jd_min_yrs, jd_max_yrs),
        "years_found_in_resume": res_years
    }

    return final_score, cat_points, cat_pct, gaps

def business_decision(score: float):
    if score >= 80:
        return "Strong Fit ✅ (Shortlist)", "green"
    if score >= 60:
        return "Medium Fit ⚖️ (Consider / Training)", "orange"
    return "Weak Fit ❌ (Reject)", "red"

# ---------------------------
# UI
# ---------------------------
st.title("📊 ATS Score Generator (Realistic Scoring)")
st.caption("Paste a JD and upload a resume. Get a normalized 0–100 score with business decision.")

jd_text = st.text_area("Paste Job Description (JD)")
uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])

if jd_text and uploaded_file:
    resume_text = extract_text(uploaded_file)
    score, cat_points, cat_pct, gaps = score_resume(jd_text, resume_text)
    decision_text, color = business_decision(score)

    st.subheader("📈 ATS Scoring Dashboard")
    st.metric("Final ATS Score", f"{score}/100")
    st.markdown(f"<h4 style='color:{color}'>{decision_text}</h4>", unsafe_allow_html=True)

    st.write("### Breakdown by Category")
    for k in ["skills","experience","tools","education","soft_skills","achievements","formatting","keywords"]:
        pct_val = int(round(cat_pct[k] * 100))
        st.progress(pct_val)
        st.write(f"**{k.replace('_',' ').title()}**: {cat_points[k]} / { {'skills':30,'experience':20,'tools':15,'education':10,'soft_skills':10,'achievements':5,'formatting':5,'keywords':5}[k] }  ({pct_val}%)")

    # Optional but useful: explain WHY
    st.write("### Gap Analysis")
    if gaps["missing_skills"] or gaps["missing_tools"] or gaps["missing_soft_skills"]:
        if gaps["missing_skills"]:
            st.write("- Missing skills from JD:", ", ".join(gaps["missing_skills"]))
        if gaps["missing_tools"]:
            st.write("- Missing tools from JD:", ", ".join(gaps["missing_tools"]))
        if gaps["missing_soft_skills"]:
            st.write("- Missing soft skills from JD:", ", ".join(gaps["missing_soft_skills"]))
    else:
        st.write("- No critical gaps detected in skills/tools/soft skills.")

    miny, maxy = gaps["years_required"]
    if miny or maxy:
        st.write(f"- JD years required: {miny}{'–'+str(maxy) if maxy else '+'}")
    if gaps["years_found_in_resume"] is None:
        st.write("- Could not find explicit years of experience in resume. Add e.g., “3 years of experience”.")
