import streamlit as st
import docx2txt
import pdfplumber
import os

# ---------- Keyword Dictionary ----------
CATEGORIES = {
    "Skills": (["python", "sql", "excel", "machine learning", "communication"], 0.40),
    "Tools": (["power bi", "tableau", "jira", "git"], 0.25),
    "Experience": (["years", "developed", "analyzed", "managed", "led"], 0.20),
    "Education": (["bachelor", "master", "mba", "b.tech", "m.tech"], 0.15),
}

# ---------- File Reader ----------
def extract_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return " ".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file.name.endswith(".docx"):
        return docx2txt.process(file)
    else:
        return file.read().decode("utf-8", errors="ignore")

# ---------- ATS Score Calculator ----------
def calculate_ats_score(resume_text, jd_text):
    resume_text = resume_text.lower()
    jd_text = jd_text.lower()

    breakdown = {}
    matched_keywords = {}
    missing_keywords = {}
    total_score = 0

    for category, (keywords, weight) in CATEGORIES.items():
        matches = [word for word in keywords if word in resume_text and word in jd_text]
        missing = [word for word in keywords if word in jd_text and word not in resume_text]

        category_score = (len(matches) / len(keywords)) * 100 if keywords else 0
        weighted_score = category_score * weight

        breakdown[category] = round(category_score, 2)
        matched_keywords[category] = matches
        missing_keywords[category] = missing
        total_score += weighted_score

    final_score = round(total_score)
    return final_score, breakdown, matched_keywords, missing_keywords

# ---------- Business Decision ----------
def business_decision(score):
    if score >= 80:
        return "✅ Strong Fit – Shortlist", "green"
    elif score >= 60:
        return "⚖️ Medium Fit – Consider/Training", "orange"
    else:
        return "❌ Weak Fit – Reject", "red"

# ---------- UI ----------
st.set_page_config(page_title="ATS Score Generator", layout="wide")

st.title("📊 ATS Score Generator")
st.markdown("Upload a **Job Description** and one or more **Resumes** to see ATS scoring, gap analysis, and ranking.")

# JD Upload
jd_file = st.file_uploader("📄 Upload Job Description", type=["txt", "pdf", "docx"])

# Resume Upload
resume_files = st.file_uploader("👤 Upload Resume(s)", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if jd_file and resume_files:
    jd_text = extract_text(jd_file)

    results = []
    for resume_file in resume_files:
        resume_text = extract_text(resume_file)
        score, breakdown, matched, missing = calculate_ats_score(resume_text, jd_text)
        decision, color = business_decision(score)
        results.append((resume_file.name, score, breakdown, matched, missing, decision, color))

    # ---------- Leaderboard ----------
    st.subheader("🏆 Candidate Leaderboard")
    leaderboard = sorted(results, key=lambda x: x[1], reverse=True)
    for i, (name, score, _, _, _, decision, color) in enumerate(leaderboard, 1):
        st.markdown(f"**{i}. {name}** → Score: **{score}/100** | <span style='color:{color}'>{decision}</span>", unsafe_allow_html=True)

    # ---------- Detailed Report ----------
    from io import BytesIO
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Function to generate PDF report
def generate_pdf(name, score, breakdown, matched, missing, decision):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 750, f"ATS Report for {name}")
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Final Score: {score}/100")
    c.drawString(100, 710, f"Decision: {decision}")

    y = 680
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Category Scores:")
    c.setFont("Helvetica", 11)
    for cat, val in breakdown.items():
        y -= 20
        c.drawString(120, y, f"{cat}: {val}%")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Matched Keywords:")
    y -= 20
    c.setFont("Helvetica", 11)
    for cat, words in matched.items():
        if words:
            c.drawString(120, y, f"{cat}: {', '.join(words)}")
            y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y, "Missing Keywords:")
    y -= 20
    c.setFont("Helvetica", 11)
    for cat, words in missing.items():
        if words:
            c.drawString(120, y, f"{cat}: {', '.join(words)}")
            y -= 20

    c.save()
    buffer.seek(0)
    return buffer

# -------- Inside Candidate Reports Loop --------
for name, score, breakdown, matched, missing, decision, color in results:
    st.markdown(f"### {name}")
    st.markdown(f"**Final Score: {score}/100**")
    st.markdown(f"<span style='color:{color}'>{decision}</span>", unsafe_allow_html=True)

    # Progress Bars
    for cat, value in breakdown.items():
        st.progress(value / 100)
        st.write(f"**{cat}: {value}%**")

    # Matched & Missing
    st.markdown("**✅ Matched Keywords:** " + (", ".join([", ".join(v) for v in matched.values() if v]) if any(matched.values()) else "None"))
    st.markdown("**❌ Missing Keywords:** " + (", ".join([", ".join(v) for v in missing.values() if v]) if any(missing.values()) else "None"))

    # Download Buttons
    pdf_buffer = generate_pdf(name, score, breakdown, matched, missing, decision)
    st.download_button(
        label="📥 Download ATS Report (PDF)",
        data=pdf_buffer,
        file_name=f"{name}_ATS_Report.pdf",
        mime="application/pdf"
    )

    df = pd.DataFrame({
        "Category": list(breakdown.keys()),
        "Score (%)": list(breakdown.values())
    })
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Breakdown (CSV)",
        data=csv,
        file_name=f"{name}_ATS_Breakdown.csv",
        mime="text/csv"
    )

    st.markdown("---")


        # Progress Bars
        for cat, value in breakdown.items():
            st.progress(value / 100)
            st.write(f"**{cat}: {value}%**")

        # Matched & Missing Keywords
        st.markdown("**✅ Matched Keywords:** " + ", ".join([", ".join(v) for v in matched.values() if v]) if any(matched.values()) else "None")
        st.markdown("**❌ Missing Keywords:** " + ", ".join([", ".join(v) for v in missing.values() if v]) if any(missing.values()) else "None")

        st.markdown("---")
