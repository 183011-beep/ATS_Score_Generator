import streamlit as st
import docx2txt
import PyPDF2
import re

# ---------------------------
# Function to extract text from resume files
# ---------------------------
def extract_text(file):
    text = ""
    if file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    elif file.name.endswith(".docx"):
        text = docx2txt.process(file)
    else:
        text = file.read().decode("utf-8")
    return text

# ---------------------------
# Scoring Function
# ---------------------------
def calculate_ats_score(resume_text, jd_text):
    resume_text = resume_text.lower()
    jd_text = jd_text.lower()

    # Define scoring categories (weights can be tuned)
    weights = {
        "skills": 30,
        "experience": 20,
        "tools": 15,
        "education": 10,
        "soft_skills": 10,
        "keywords": 10,
        "achievements": 5
    }

    # Sample keyword lists (customize per role)
    skills = ["python", "sql", "excel", "tableau", "communication"]
    tools = ["power bi", "aws", "git", "jira"]
    education = ["b.tech", "mca", "mba", "bachelor", "master"]
    soft_skills = ["leadership", "teamwork", "problem solving"]
    achievements = ["improved", "reduced", "increased", "managed"]

    # Count matches
    def score_category(keywords):
        return sum(1 for kw in keywords if kw in resume_text and kw in jd_text)

    scores = {}
    scores["skills"] = score_category(skills)
    scores["experience"] = 1 if "year" in resume_text or "experience" in resume_text else 0
    scores["tools"] = score_category(tools)
    scores["education"] = score_category(education)
    scores["soft_skills"] = score_category(soft_skills)
    scores["keywords"] = sum(1 for word in jd_text.split() if word in resume_text)
    scores["achievements"] = score_category(achievements)

    # Weighted total
    total_score = 0
    for cat, weight in weights.items():
        total_score += (scores[cat] * weight)

    # Normalize to 100
    final_score = min(100, total_score)

    return final_score, scores

# ---------------------------
# Business Decision Function
# ---------------------------
def decision(final_score):
    if final_score >= 80:
        return "Strong Fit ✅ (Shortlist)", "green"
    elif 60 <= final_score < 80:
        return "Medium Fit ⚖️ (Consider / Training)", "orange"
    else:
        return "Weak Fit ❌ (Reject)", "red"

# ---------------------------
# Streamlit UI
# ---------------------------
st.title("📊 ATS Score Generator with Business Decisions")

jd_text = st.text_area("Paste Job Description (JD) here")

uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])

if jd_text and uploaded_file:
    resume_text = extract_text(uploaded_file)
    final_score, breakdown = calculate_ats_score(resume_text, jd_text)
    decision_text, color = decision(final_score)

    # Dashboard
    st.subheader("📈 ATS Scoring Dashboard")
    st.metric("Final ATS Score", f"{final_score}/100")
    st.markdown(f"<h4 style='color:{color}'>{decision_text}</h4>", unsafe_allow_html=True)

    st.write("### Breakdown by Category")
    for cat, score in breakdown.items():
        st.progress(min(score, 10))  # simple bar up to 10
        st.write(f"{cat.capitalize()}: {score}")

    st.info("💡 Suggestions: Add missing skills, highlight measurable achievements, and match keywords from JD for a higher score.")
