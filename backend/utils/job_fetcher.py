import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from utils.jd_parser import parse_job_description
import json


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


# -----------------------------
# Detect platform from URL
# -----------------------------
def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if "indeed" in domain:
        return "indeed"
    elif "linkedin" in domain:
        return "linkedin"
    else:
        return "other"


# -----------------------------
# Fetch raw HTML from URL
# -----------------------------
def fetch_page_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return response.text


# -----------------------------
# Clean text helper
# -----------------------------
def clean_text(text: str) -> str:
    return " ".join(text.split())


# -----------------------------
# Extract text from Indeed HTML
# -----------------------------
def extract_indeed_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    text_parts = []

    # Try common title selectors
    title_tag = soup.find("h1")
    if title_tag:
        text_parts.append(f"Role: {title_tag.get_text(strip=True)}")

    # Try company selectors
    company_candidates = [
        soup.find(attrs={"data-testid": "inlineHeader-companyName"}),
        soup.find("div", class_="jobsearch-CompanyInfoWithoutHeaderImage"),
        soup.find("span", class_="css-1saizt3"),
    ]

    for company_tag in company_candidates:
        if company_tag:
            text_parts.append(f"Company: {company_tag.get_text(strip=True)}")
            break

    # Try job description container
    description_candidates = [
        soup.find("div", id="jobDescriptionText"),
        soup.find(attrs={"data-testid": "jobsearch-JobComponent-description"}),
    ]

    for desc in description_candidates:
        if desc:
            text_parts.append(desc.get_text("\n", strip=True))
            break

    return "\n".join(text_parts).strip()


# -----------------------------
# Extract text from LinkedIn HTML
# -----------------------------
def extract_linkedin_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    text_parts = []

    # Job title
    title_tag = soup.find("h1")
    if title_tag:
        text_parts.append(f"Role: {title_tag.get_text(strip=True)}")

    # Company
    company_candidates = [
        soup.find("a", class_="topcard__org-name-link"),
        soup.find("span", class_="topcard__flavor"),
        soup.find("div", class_="topcard__org-name-link"),
    ]

    for company_tag in company_candidates:
        if company_tag:
            text_parts.append(f"Company: {company_tag.get_text(strip=True)}")
            break

    # Description
    description_candidates = [
        soup.find("div", class_="show-more-less-html__markup"),
        soup.find("div", class_="description__text"),
        soup.find("section", class_="show-more-less-html"),
    ]

    for desc in description_candidates:
        if desc:
            text_parts.append(desc.get_text("\n", strip=True))
            break

    return "\n".join(text_parts).strip()


# -----------------------------
# Generic extraction for other job pages
# -----------------------------
def extract_generic_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    text_parts = []

    title_tag = soup.find("h1")
    if title_tag:
        text_parts.append(f"Role: {title_tag.get_text(strip=True)}")

    # collect large paragraph/div text
    body = soup.get_text("\n", strip=True)
    text_parts.append(body[:15000])  # keep reasonable size

    return "\n".join(text_parts).strip()


# -----------------------------
# Main extractor by platform
# -----------------------------
def extract_job_text(url: str) -> str:
    platform = detect_platform(url)
    html = fetch_page_html(url)

    if platform == "indeed":
        job_text = extract_indeed_job_text(html)
    elif platform == "linkedin":
        job_text = extract_linkedin_job_text(html)
    else:
        job_text = extract_generic_job_text(html)

    return clean_text(job_text)


# -----------------------------
# Full pipeline:
# URL -> raw text -> parsed requirements
# -----------------------------
def extract_requirements_from_url(url: str):
    raw_text = extract_job_text(url)

    if not raw_text.strip():
        return {
            "error": "Could not extract job text from URL."
        }

    parsed = parse_job_description(raw_text)

    return {
        "source_url": url,
        "raw_text_preview": raw_text[:1200],
        "parsed_requirements": parsed
    }


# -----------------------------
# Run in terminal
# -----------------------------
if __name__ == "__main__":
    url = input("Paste Indeed / LinkedIn Job URL: ").strip()

    try:
        result = extract_requirements_from_url(url)

        print("\n===== JOB EXTRACTION RESULT =====\n")
        print(json.dumps(result, indent=4))

    except Exception as e:
        print(f"\nError while fetching job data: {e}")