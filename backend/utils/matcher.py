import json
import re
from typing import List, Dict

from jd_parser import parse_job_description
from resume_parser import parse_all_resumes


# ---------------------------------------
# Normalize text for comparison
# ---------------------------------------
def normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


# ---------------------------------------
# Convert skill list to normalized set
# ---------------------------------------
def normalize_skill_list(skills: List[str]) -> set:
    return {normalize(skill) for skill in skills if skill}


# ---------------------------------------
# Parse "6+ years" / "5 years" into int
# ---------------------------------------
def extract_year_number(year_text: str):
    if not year_text:
        return None

    match = re.search(r"(\d+)", str(year_text))
    if match:
        return int(match.group(1))
    return None


# ---------------------------------------
# Check experience match
# Job requires X years, resume has Y years
# ---------------------------------------
def check_experience_match(job_experience: str, resume_experience_list: List[str]) -> bool:
    job_years = extract_year_number(job_experience)
    if job_years is None:
        return False

    best_resume_years = None
    for exp in resume_experience_list:
        val = extract_year_number(exp)
        if val is not None:
            if best_resume_years is None or val > best_resume_years:
                best_resume_years = val

    if best_resume_years is None:
        return False

    return best_resume_years >= job_years


# ---------------------------------------
# Check education match
# very simple rule:
# if job asks Master and resume has Master -> match
# if job asks Bachelor and resume has Bachelor or Master -> match
# ---------------------------------------
def check_education_match(job_education: List[str], resume_education: List[str]) -> bool:
    job_edu_norm = [normalize(x) for x in job_education]
    resume_edu_norm = [normalize(x) for x in resume_education]

    if not job_edu_norm:
        return False

    # master requirement
    if any("master" in e for e in job_edu_norm):
        return any("master" in e for e in resume_edu_norm)

    # bachelor requirement
    if any("bachelor" in e for e in job_edu_norm):
        return any(("bachelor" in e or "master" in e) for e in resume_edu_norm)

    # fallback: any overlap
    return any(j in r for j in job_edu_norm for r in resume_edu_norm)


# ---------------------------------------
# Score one resume against one job
# ---------------------------------------
def score_resume_against_job(job_data: Dict, resume_data: Dict) -> Dict:
    job_required_skills = job_data.get("required_skills", [])
    job_preferred_skills = job_data.get("preferred_skills", [])
    job_experience = job_data.get("experience_required", "")
    job_education = job_data.get("education", [])

    resume_skills = resume_data.get("skills", [])
    resume_experience = resume_data.get("experience_years", [])
    resume_education = resume_data.get("education", [])

    req_job_set = normalize_skill_list(job_required_skills)
    pref_job_set = normalize_skill_list(job_preferred_skills)
    resume_skill_set = normalize_skill_list(resume_skills)

    # ---------------- Required skills ----------------
    matched_required = sorted(list(req_job_set.intersection(resume_skill_set)))
    missing_required = sorted(list(req_job_set - resume_skill_set))

    if len(req_job_set) > 0:
        required_skill_score = (len(matched_required) / len(req_job_set)) * 60
    else:
        required_skill_score = 0

    # ---------------- Preferred skills ----------------
    matched_preferred = sorted(list(pref_job_set.intersection(resume_skill_set)))
    if len(pref_job_set) > 0:
        preferred_skill_score = (len(matched_preferred) / len(pref_job_set)) * 10
    else:
        preferred_skill_score = 0

    # ---------------- Experience ----------------
    experience_match = check_experience_match(job_experience, resume_experience)
    experience_score = 20 if experience_match else 0

    # ---------------- Education ----------------
    education_match = check_education_match(job_education, resume_education)
    education_score = 10 if education_match else 0

    # ---------------- Final score ----------------
    final_score = required_skill_score + preferred_skill_score + experience_score + education_score

    result = {
        "resume_name": resume_data.get("resume_name"),
        "score": round(final_score, 2),
        "matched_required_skills": sorted(job_required_skills_match_display(job_required_skills, resume_skills)),
        "missing_required_skills": sorted(job_required_skills_missing_display(job_required_skills, resume_skills)),
        "matched_preferred_skills": sorted(job_required_skills_match_display(job_preferred_skills, resume_skills)),
        "experience_match": experience_match,
        "education_match": education_match
    }

    return result


# ---------------------------------------
# Display helper preserving original skill names
# ---------------------------------------
def job_required_skills_match_display(job_skills: List[str], resume_skills: List[str]) -> List[str]:
    resume_norm = normalize_skill_list(resume_skills)
    matched = []

    for skill in job_skills:
        if normalize(skill) in resume_norm:
            matched.append(skill)

    return matched


def job_required_skills_missing_display(job_skills: List[str], resume_skills: List[str]) -> List[str]:
    resume_norm = normalize_skill_list(resume_skills)
    missing = []

    for skill in job_skills:
        if normalize(skill) not in resume_norm:
            missing.append(skill)

    return missing


# ---------------------------------------
# Rank all resumes for one job
# ---------------------------------------
def rank_resumes_for_job(job_data: Dict, resumes_data: List[Dict]) -> Dict:
    rankings = []

    for resume in resumes_data:
        # skip broken resume entries
        if "error" in resume:
            continue

        score_result = score_resume_against_job(job_data, resume)
        rankings.append(score_result)

    rankings.sort(key=lambda x: x["score"], reverse=True)

    best_resume = rankings[0] if rankings else None

    return {
        "job_title": job_data.get("job_title"),
        "company": job_data.get("company"),
        "best_resume": best_resume["resume_name"] if best_resume else None,
        "best_score": best_resume["score"] if best_resume else 0,
        "rankings": rankings
    }


# ---------------------------------------
# TEST MODE:
# use the same job sample as earlier
# ---------------------------------------
if __name__ == "__main__":
    sample_job = {
        "company": "Amazon Development Center U.S., Inc.",
        "job_title": "Senior Applied Scientist, Applied AI Solutions GTM",
        "experience_required": "6+ years",
        "required_skills": ["Aws", "Deep Learning", "Machine Learning", "Nlp"],
        "preferred_skills": ["Aws"],
        "education": ["Master"]
    }

    resumes = parse_all_resumes()

    result = rank_resumes_for_job(sample_job, resumes)

    print("\n===== RESUME MATCHING RESULT =====\n")
    print(json.dumps(result, indent=4))