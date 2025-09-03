import streamlit as st
import re
import PyPDF2
import docx2txt

# ----- Helper Functions -----
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_docx(file):
    return docx2txt.process(file)

def clean_text(text):
    return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower()

def calculate_score(jd, resume):
    # Convert to lowercase
    jd = clean_text(jd)
    resume = clean_text(resume)

    # Example categories (can be expanded)
    weights = {
        "skills": 30,
        "experience": 20,
        "tools": 15,
        "education": 10,
        "soft_skills": 10,
        "achievements": 5,
        "formatting": 5,
        "keywords": 5
    }

    # Simple keyword lists (expand as needed)
    skills = ["python", "sql", "tableau", "excel", "java", "aws"]
    tools = ["powerbi", "salesforce", "hadoop", "spark"]
    education = ["btech", "mba", "msc", "phd", "bachelor", "master"]
    soft_skills = ["leadership", "teamwork", "communication", "problem solving"]
    action_verbs = ["developed", "managed", "designed", "implemented", "delivered"]

    # Scoring
    scores = {}
    scores["skills"] = sum([1 for s in skills if s in resume]) / len(skills) * weights["skills"]
    scores["tools"] = sum([1 for t in tools if t in resume]) / len(tools) * weights["tools"]
    scores["education"] = (1 if any(e in resume for e in education) else 0) * weights["education"]
    scores["soft_skills"] = sum([1 for s in soft_skills if s in resume]) / len(soft_skills) * weights["soft_skills"]
    scores["achievements"] = sum([1 for v in action_verbs if v in resume]) / len(action_verbs) * weights["achievements"]

    # Experience match (very basic: look for "years")
    exp_match = re.search(r'(\d+)\+?\s*year', resume)
    scores["experience"] = weights["experience"] if exp_match else weights["experience"] * 0.5

    # Formatting check
    sections = ["experience", "education", "skills"]
    scores["formatting"] = sum([1 for s in sections if s in resume]) / len(sections) * weights["formatting"]

    # Keyword density
    jd_keywords = jd.split()
    matched_keywords = sum([1 for k in jd_keywords if k in resume])
    scores["keywords"] = min(matched_keywords / len(jd_keywords), 1) * weights["keywords"]

    # Final score
    total_score = sum(scores.values())

    return total_score, scores

# ----- Streamlit UI -----
st.title("📊 ATS Score Generator (Advanced)")
st.write("Upload a Job Description and Resume to get a detailed ATS Score with gap analysis.")

jd_text = st.text_area("Paste Job Description (JD)")

resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])

if st.button("Analyze"):
    if jd_text and resume_file:
        # Extract text from resume
        if resume_file.type == "application/pdf":
            resume_text = extract_text_from_pdf(resume_file)
        elif resume_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            resume_text = extract_text_from_docx(resume_file)
        else:
            resume_text = resume_file.read().decode("utf-8")

        score, breakdown = calculate_score(jd_text, resume_text)

        st.subheader(f"Overall ATS Score: {score:.2f}/100")
        st.write("### Breakdown by Category:")
        for k, v in breakdown.items():
            st.write(f"- {k.capitalize()}: {v:.2f}")

        # Gap Analysis
        st.write("### Gap Analysis & Suggestions:")
        if "aws" not in resume_text:
            st.write("- Missing keyword: AWS (add relevant project).")
        if "leadership" not in resume_text:
            st.write("- Add leadership experience under projects.")
        if not re.search(r'(\d+)\+?\s*year', resume_text):
            st.write("- Mention years of experience clearly.")
    else:
        st.warning("Please provide both JD and Resume.")
