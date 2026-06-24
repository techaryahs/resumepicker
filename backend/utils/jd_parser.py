import re
import json

# -----------------------------
# Skill database (can expand later)
# -----------------------------
SKILLS_DB = [
    "python", "java", "c++", "javascript", "react", "node.js", "mongodb",
    "sql", "mysql", "postgresql", "tensorflow", "pytorch", "machine learning",
    "deep learning", "nlp", "computer vision", "aws", "docker", "kubernetes",
    "flask", "django", "git", "rest api", "scikit-learn", "pandas", "numpy"
]

EDUCATION_KEYWORDS = [
    "b.tech", "b.e", "m.tech", "m.e", "mca", "bca",
    "bachelor", "master", "computer science", "information technology"
]

# -----------------------------
# Clean job description
# -----------------------------
def clean_text(text: str) -> str:
    text = text.replace("\r", " ")
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# -----------------------------
# Extract company name
# Looks for "Company: XYZ"
# -----------------------------
def extract_company(text: str):
    match = re.search(r'company\s*:\s*(.+)', text, re.IGNORECASE)
    if match:
        return match.group(1).split("\n")[0].strip()
    return None

# -----------------------------
# Extract job title
# Looks for "Role: XYZ" or "Job Title: XYZ"
# -----------------------------
def extract_job_title(text: str):
    patterns = [
        r'role\s*:\s*(.+)',
        r'job title\s*:\s*(.+)',
        r'position\s*:\s*(.+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).split("\n")[0].strip()
    return None

# -----------------------------
# Extract experience
# Examples:
# 2+ years
# 3 years
# 1-3 years
# minimum 2 years
# -----------------------------
def extract_experience(text: str):
    patterns = [
        r'(\d+\+?\s*years)',
        r'(\d+\s*-\s*\d+\s*years)',
        r'(minimum\s*\d+\+?\s*years)'
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return match.group(1)
    return None

# -----------------------------
# Extract all skills found in JD
# -----------------------------
def extract_all_skills(text: str):
    text_lower = text.lower()
    found_skills = []

    for skill in SKILLS_DB:
        if skill in text_lower:
            found_skills.append(skill.title())

    return sorted(list(set(found_skills)))

# -----------------------------
# Extract education requirements
# -----------------------------
def extract_education(text: str):
    text_lower = text.lower()
    found = []

    for edu in EDUCATION_KEYWORDS:
        if edu in text_lower:
            found.append(edu.title())

    return sorted(list(set(found)))

# -----------------------------
# Extract required and preferred skills
# Basic logic:
# - if skill appears near words like "required", "must have", "mandatory"
#   -> required
# - if skill appears near words like "preferred", "good to have", "plus"
#   -> preferred
#
# For MVP, we’ll do a simple split by lines.
# -----------------------------
def extract_required_preferred_skills(text: str):
    required_markers = ["required", "must have", "mandatory", "essential"]
    preferred_markers = ["preferred", "good to have", "nice to have", "plus"]

    required_skills = set()
    preferred_skills = set()

    lines = text.split("\n")

    for line in lines:
        line_lower = line.lower()

        # find skills in this line
        skills_in_line = [skill.title() for skill in SKILLS_DB if skill in line_lower]

        if any(marker in line_lower for marker in required_markers):
            required_skills.update(skills_in_line)

        elif any(marker in line_lower for marker in preferred_markers):
            preferred_skills.update(skills_in_line)

    return sorted(list(required_skills)), sorted(list(preferred_skills))

# -----------------------------
# Main parser
# -----------------------------
def parse_job_description(jd_text: str):
    jd_text = clean_text(jd_text)

    required_skills, preferred_skills = extract_required_preferred_skills(jd_text)
    all_skills = extract_all_skills(jd_text)

    # If no required skills found via markers,
    # treat all detected skills as required for MVP
    if not required_skills:
        required_skills = all_skills

    result = {
        "company": extract_company(jd_text),
        "job_title": extract_job_title(jd_text),
        "experience_required": extract_experience(jd_text),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "education": extract_education(jd_text)
    }

    return result

# -----------------------------
# Test in terminal
# -----------------------------
if __name__ == "__main__":
    sample_jd = """
    Company: Infosys
    Role: Machine Learning Engineer

    We are looking for a Machine Learning Engineer with 2+ years of experience in Python, TensorFlow, SQL, NLP and Deep Learning.
    Required skills: Python, TensorFlow, SQL, Machine Learning, NLP
    Preferred skills: AWS, Docker
    Bachelor's degree in Computer Science or related field preferred.
    """

    result = parse_job_description(sample_jd)

    print("\n===== EXTRACTED JOB REQUIREMENTS =====\n")
    print(json.dumps(result, indent=4))