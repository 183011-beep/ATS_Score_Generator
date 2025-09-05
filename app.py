import streamlit as st
import docx2txt
import PyPDF2
import re
import pandas as pd

# -------------------------
# Function to extract text
# -------------------------
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

# -------------------------
# Scoring Function
# -------------------------
def calculate_ats_score(resume_text, jd_text):
    resume_text = resume_text.lower()
    jd_text = jd_text.lower()

    categories = {
        "Skills": (["python", "excel", "sql", "machine learning", "communication", "leadership"], 0.40),
        "Tools": (["power bi", "tableau", "jira", "git", "tensorflow"], 0.25),
        "Experience": (["years", "worked", "developed", "managed", "led"], 0.20),
        "Education": (["bachelor", "master", "phd", "mba", "b.tech", "m.tech"], 0.15),
    }

    breakdown = {}
    total_score = 0
    keyword_matches = {}

    for cat, (keywords, weight) in categories.items():
        matches = [word for word in keywords if word in resume_text and word in jd_text]
        misses = [word for word in keywords if word in jd_text and word not in resume_text]
        keyword_matches[cat] = {"Matched": matches, "Missing": misses}

        category_score = (len(matches) / len(keywords)) * 100
        weighted_score = category_score * weight
        breakdown[cat] = round(category_score, 2)
        total_score += weighted_score

    final_score = round(total_score)
    return final_score, breakdown, keyword_matches

# -------------------------
# Decision Function
# -------------------------
def business_decision(score):
    if score >= 80:
        return "Strong Fit ✅ (Shortlist)", "green"
    elif 60 <= score < 80:
        return "Medium Fit ⚖️ (Consider/Training)", "orange"
    else:
        return "Weak Fit ❌ (Reject)", "red"

# -------------------------
# Streamlit App
# -------------------------
st.set_page_config(page_title="ATS Score Generator", page_icon="📊", layout="wide")
st.title("📊 ATS Score Generator")
st.write("Upload Job Description (JD) and Resume(s) to evaluate fit. Mimics real ATS systems used in HR.")

# Mode Selector
mode = st.radio("Choose Mode:", ["Single Resume Analysis", "Multi-Resume Ranking"])

# -------------------------
# Single Resume Mode
# -------------------------
if mode == "Single Resume Analysis":
    jd_text = st.text_area("📄 Paste Job Description (JD)", height=150)
    uploaded_file = st.file_uploader("📂 Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])

    if st.button("Analyze") and jd_text and uploaded_file:
        resume_text = extract_text(uploaded_file)
        final_score, breakdown, keyword_matches = calculate_ats_score(resume_text, jd_text)
        decision, color = business_decision(final_score)

        # Dashboard
        st.subheader("📊 ATS Scoring Dashboard")
        st.metric("Final ATS Score", f"{final_score}/100")
        st.markdown(f"<h4 style='color:{color}'>{decision}</h4>", unsafe_allow_html=True)

        st.subheader("📌 Breakdown by Category")
        for cat, score in breakdown.items():
            st.progress(score / 100)
            st.write(f"**{cat}**: {score}%")

        st.subheader("🔍 Keyword Analysis")
        for cat, details in keyword_matches.items():
            st.write(f"**{cat}**")
            st.write(f"✅ Matched: {', '.join(details['Matched']) if details['Matched'] else 'None'}")
            st.write(f"❌ Missing: {', '.join(details['Missing']) if details['Missing'] else 'None'}")

# -------------------------
# Multi-Resume Mode
# -------------------------
elif mode == "Multi-Resume Ranking":
    jd_text = st.text_area("📄 Paste Job Description (JD)", height=150)
    uploaded_files = st.file_uploader("📂 Upload Multiple Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)

    if st.button("Rank Candidates") and jd_text and uploaded_files:
        results = []
        for file in uploaded_files:
            resume_text = extract_text(file)
            final_score, breakdown, _ = calculate_ats_score(resume_text, jd_text)
            decision, _ = business_decision(final_score)
            results.append({"Candidate": file.name, "Score": final_score, "Decision": decision})

        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader("🏆 Candidate Leaderboard")
        st.dataframe(df.reset_index(drop=True))
