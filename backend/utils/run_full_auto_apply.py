import os
import json

from search_page_fetcher import extract_jobs_from_search_url
from job_details_fetcher import extract_job_requirements_from_url
from resume_parser import parse_all_resumes, UPLOADS_DIR
from matcher import rank_resumes_for_job
from auto_apply_engine import auto_apply_to_job
from candidate_profile import CANDIDATE_PROFILE


def build_matcher_job_payload(job_result: dict):
    parsed = job_result.get("parsed_requirements", {}) or {}

    return {
        "company": parsed.get("company") or job_result.get("extracted_company") or "",
        "job_title": parsed.get("job_title") or job_result.get("extracted_title") or "",
        "experience_required": parsed.get("experience_required", ""),
        "required_skills": parsed.get("required_skills", []),
        "preferred_skills": parsed.get("preferred_skills", []),
        "education": parsed.get("education", [])
    }


def get_resume_path(resume_name: str):
    return os.path.join(UPLOADS_DIR, resume_name)


def run_full_pipeline(search_url: str, max_jobs: int = 5):
    print("\nSTEP 1: Extracting jobs from search page...")
    search_result = extract_jobs_from_search_url(search_url)
    print(json.dumps(search_result, indent=4))

    jobs = search_result.get("jobs", [])
    if not jobs:
        print("No jobs found.")
        return []

    jobs = jobs[:max_jobs]

    print("\nSTEP 2: Parsing all resumes...")
    resumes = parse_all_resumes()
    print(f"Total resumes parsed: {len(resumes)}")

    final_results = []

    for idx, job in enumerate(jobs, start=1):
        print("\n" + "=" * 80)
        print(f"JOB {idx}/{len(jobs)}")
        print("=" * 80)

        job_url = job.get("job_url")
        print("Job URL:", job_url)

        if not job_url:
            print("Skipping job because job_url is missing.")
            continue

        # ---------------- Extract JD ----------------
        print("\nSTEP 3: Extracting job details...")
        jd_result = extract_job_requirements_from_url(job_url)

        if jd_result.get("error"):
            print("Skipping job, extraction failed:", jd_result["error"])
            final_results.append({
                "job": job,
                "jd_result": jd_result,
                "ranking_result": None,
                "apply_result": None
            })
            continue

        print(json.dumps(jd_result, indent=4))

        # ---------------- Build matcher payload ----------------
        matcher_job = build_matcher_job_payload(jd_result)

        print("\nSTEP 4: Ranking resumes for this job...")
        ranking_result = rank_resumes_for_job(matcher_job, resumes)
        print(json.dumps(ranking_result, indent=4))

        best_resume_name = ranking_result.get("best_resume")
        if not best_resume_name:
            print("No best resume found. Skipping auto-apply.")
            final_results.append({
                "job": job,
                "jd_result": jd_result,
                "ranking_result": ranking_result,
                "apply_result": {
                    "status": "skipped",
                    "reason": "No best resume found"
                }
            })
            continue

        best_resume_path = get_resume_path(best_resume_name)

        if not os.path.exists(best_resume_path):
            print(f"Resume file not found on disk: {best_resume_path}")
            final_results.append({
                "job": job,
                "jd_result": jd_result,
                "ranking_result": ranking_result,
                "apply_result": {
                    "status": "failed",
                    "reason": f"Resume file not found: {best_resume_path}"
                }
            })
            continue

        print(f"\nSelected best resume: {best_resume_name}")
        print(f"Resume path: {best_resume_path}")

        # ---------------- Auto apply ----------------
        print("\nSTEP 5: Auto-applying...")
        apply_result = auto_apply_to_job(
            job_url=job_url,
            resume_path=best_resume_path,
            profile=CANDIDATE_PROFILE,
            interactive=False,   # IMPORTANT: no input() in Streamlit
            headless=False
        )

        final_results.append({
            "job": job,
            "jd_result": jd_result,
            "ranking_result": ranking_result,
            "apply_result": apply_result
        })

    print("\n\n===== FINAL PIPELINE RESULT =====\n")
    print(json.dumps(final_results, indent=4))

    return final_results


if __name__ == "__main__":
    search_url = input("Paste job search URL: ").strip()
    max_jobs = input("How many jobs to process? (default 5): ").strip()

    if not max_jobs.isdigit():
        max_jobs = 5
    else:
        max_jobs = int(max_jobs)

    run_full_pipeline(search_url, max_jobs=max_jobs)