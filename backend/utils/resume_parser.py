import os
import re
import json
import pdfplumber
from docx import Document

# ---------------------------------------
# Resume folder
# ---------------------------------------
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

# ---------------------------------------
# Skills database
# Expand this later as needed
# ---------------------------------------
SKILLS_DB = [
    "python", "java", "c++", "javascript", "typescript", "react", "next.js",
    "node.js", "express", "mongodb", "mysql", "postgresql", "sql",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "flask", "django", "fastapi", "docker", "kubernetes", "aws",
    "git", "github", "html", "css", "tailwind", "firebase"
]

EDUCATION_KEYWORDS = [
    "b.tech", "b.e", "m.tech", "m.e", "mca", "bca",
    "bachelor", "master", "computer science", "information technology"
]

PROJECT_SECTION_KEYWORDS = [
    "project", "projects", "academic projects", "personal projects"
]

EXPERIENCE_SECTION_KEYWORDS = [
    "experience", "work experience", "professional experience", "employment"
]


# ---------------------------------------
# Clean text
# ---------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", " ")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ---------------------------------------
# Read PDF
# ---------------------------------------
def extract_text_from_pdf(file_path: str) -> str:
    text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return clean_text("\n".join(text))


# ---------------------------------------
# Read DOCX
# ---------------------------------------
def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return clean_text("\n".join(paragraphs))


# ---------------------------------------
# Detect file type and extract text
# ---------------------------------------
def extract_resume_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


# ---------------------------------------
# Extract skills from resume text
# ---------------------------------------
def extract_skills(text: str):
    text_lower = text.lower()
    found = []

    for skill in SKILLS_DB:
        if skill in text_lower:
            found.append(skill.title())

    return sorted(list(set(found)))


# ---------------------------------------
# Extract education
# ---------------------------------------
def extract_education(text: str):
    text_lower = text.lower()
    found = []

    for edu in EDUCATION_KEYWORDS:
        if edu in text_lower:
            found.append(edu.title())

    return sorted(list(set(found)))


# ---------------------------------------
# Extract years of experience mentions
# ---------------------------------------
def extract_experience_mentions(text: str):
    patterns = [
        r'(\d+\+?\s*years)',
        r'(\d+\s*-\s*\d+\s*years)',
        r'(minimum\s*\d+\+?\s*years)'
    ]

    matches = []
    text_lower = text.lower()

    for pattern in patterns:
        found = re.findall(pattern, text_lower)
        matches.extend(found)

    return sorted(list(set(matches)))


# ---------------------------------------
# Extract section text after a heading
# Very simple heuristic version
# ---------------------------------------
def extract_section_lines(text: str, section_keywords):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    collected = []
    capture = False

    for line in lines:
        lower = line.lower()

        # Start capturing if section heading matched
        if any(keyword in lower for keyword in section_keywords):
            capture = True
            continue

        # Stop if another likely heading appears
        if capture and (
            "education" in lower or
            "skills" in lower or
            "certification" in lower or
            "experience" in lower or
            "project" in lower or
            "summary" in lower
        ):
            # stop only if it looks like a new section heading
            if len(lower.split()) <= 4:
                break

        if capture:
            collected.append(line)

            # keep section small for now
            if len(collected) >= 15:
                break

    return collected


# ---------------------------------------
# Extract projects
# ---------------------------------------
def extract_projects(text: str):
    project_lines = extract_section_lines(text, PROJECT_SECTION_KEYWORDS)

    # If no project section found, return empty
    if not project_lines:
        return []

    # keep only meaningful lines
    cleaned = []
    for line in project_lines:
        if len(line.split()) >= 2:
            cleaned.append(line)

    return cleaned[:10]


# ---------------------------------------
# Extract experience section lines
# ---------------------------------------
def extract_experience_section(text: str):
    exp_lines = extract_section_lines(text, EXPERIENCE_SECTION_KEYWORDS)

    if not exp_lines:
        return []

    cleaned = []
    for line in exp_lines:
        if len(line.split()) >= 2:
            cleaned.append(line)

    return cleaned[:10]


# ---------------------------------------
# Parse one resume
# ---------------------------------------
def parse_resume(file_path: str):
    text = extract_resume_text(file_path)

    result = {
        "resume_name": os.path.basename(file_path),
        "skills": extract_skills(text),
        "education": extract_education(text),
        "experience_years": extract_experience_mentions(text),
        "experience_section": extract_experience_section(text),
        "projects": extract_projects(text),
        "raw_text_preview": text[:1500]
    }

    return result


# ---------------------------------------
# Parse all resumes in uploads folder
# ---------------------------------------
def parse_all_resumes():
    resumes = []

    if not os.path.exists(UPLOADS_DIR):
        return resumes

    for filename in os.listdir(UPLOADS_DIR):
        if filename.lower().endswith((".pdf", ".docx")):
            file_path = os.path.join(UPLOADS_DIR, filename)

            try:
                parsed = parse_resume(file_path)
                resumes.append(parsed)
            except Exception as e:
                resumes.append({
                    "resume_name": filename,
                    "error": str(e)
                })

    return resumes


# ---------------------------------------
# Terminal test
# ---------------------------------------
if __name__ == "__main__":
    results = parse_all_resumes()

    print("\n===== PARSED RESUMES =====\n")
    print(json.dumps(results, indent=4))