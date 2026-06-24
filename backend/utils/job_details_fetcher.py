import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import json
import re

from utils.jd_parser import parse_job_description


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------
# Detect platform from URL
# ---------------------------------------
def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()

    if "indeed" in domain:
        return "indeed"
    elif "linkedin" in domain:
        return "linkedin"
    else:
        return "other"


# ---------------------------------------
# Fetch page HTML
# ---------------------------------------
def fetch_page_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.text


# ---------------------------------------
# Clean text helper
# ---------------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------
# Indeed: extract job details text
# ---------------------------------------
def extract_indeed_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    text_parts = []

    # Job title
    title_tag = soup.find("h1")
    if title_tag:
        title = clean_text(title_tag.get_text(" ", strip=True))
        if title:
            text_parts.append(f"Role: {title}")

    # Company
    company_candidates = [
        soup.find(attrs={"data-testid": "inlineHeader-companyName"}),
        soup.find("div", class_="jobsearch-CompanyInfoWithoutHeaderImage"),
        soup.find("span", class_="css-1saizt3"),
        soup.find("div", attrs={"data-company-name": True}),
    ]

    company_name = ""
    for tag in company_candidates:
        if tag:
            company_name = clean_text(tag.get_text(" ", strip=True))
            if company_name:
                text_parts.append(f"Company: {company_name}")
                break

    # Main description
    description_candidates = [
        soup.find("div", id="jobDescriptionText"),
        soup.find(attrs={"data-testid": "jobsearch-JobComponent-description"}),
    ]

    description_text = ""
    for desc in description_candidates:
        if desc:
            description_text = desc.get_text("\n", strip=True)
            break

    if description_text:
        text_parts.append(description_text)

    return "\n".join(text_parts).strip()


# ---------------------------------------
# LinkedIn: extract job details text
# ---------------------------------------
def extract_linkedin_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    text_parts = []

    # Job title
    title_tag = soup.find("h1")
    if title_tag:
        title = clean_text(title_tag.get_text(" ", strip=True))
        if title:
            text_parts.append(f"Role: {title}")

    # Company
    company_candidates = [
        soup.find("a", class_="topcard__org-name-link"),
        soup.find("span", class_="topcard__flavor"),
        soup.find("div", class_="topcard__org-name-link"),
    ]

    for tag in company_candidates:
        if tag:
            company = clean_text(tag.get_text(" ", strip=True))
            if company:
                text_parts.append(f"Company: {company}")
                break

    # Description
    description_candidates = [
        soup.find("div", class_="show-more-less-html__markup"),
        soup.find("div", class_="description__text"),
        soup.find("section", class_="show-more-less-html"),
    ]

    for desc in description_candidates:
        if desc:
            desc_text = desc.get_text("\n", strip=True)
            if desc_text:
                text_parts.append(desc_text)
                break

    return "\n".join(text_parts).strip()


# ---------------------------------------
# Generic fallback extractor
# ---------------------------------------
def extract_generic_job_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    text_parts = []

    title_tag = soup.find("h1")
    if title_tag:
        title = clean_text(title_tag.get_text(" ", strip=True))
        if title:
            text_parts.append(f"Role: {title}")

    full_text = soup.get_text("\n", strip=True)
    full_text = re.sub(r"\n+", "\n", full_text)

    if full_text:
        text_parts.append(full_text[:20000])  # avoid too huge text

    return "\n".join(text_parts).strip()


# ---------------------------------------
# Main raw text extractor
# ---------------------------------------
def extract_job_text_from_url(url: str) -> dict:
    platform = detect_platform(url)
    html = fetch_page_html(url)

    if platform == "indeed":
        raw_text = extract_indeed_job_text(html)
    elif platform == "linkedin":
        raw_text = extract_linkedin_job_text(html)
    else:
        raw_text = extract_generic_job_text(html)

    return {
        "platform": platform,
        "source_url": url,
        "raw_text": raw_text
    }


# ---------------------------------------
# Full pipeline:
# URL -> raw text -> jd_parser
# ---------------------------------------
def extract_job_requirements_from_url(url: str) -> dict:
    data = extract_job_text_from_url(url)
    raw_text = data["raw_text"]

    if not raw_text.strip():
        return {
            "source_url": url,
            "platform": data["platform"],
            "error": "Could not extract job text from this page."
        }

    parsed = parse_job_description(raw_text)

    return {
        "source_url": url,
        "platform": data["platform"],
        "raw_job_text_preview": raw_text[:1500],
        "parsed_requirements": parsed
    }


# ---------------------------------------
# Terminal test
# ---------------------------------------
if __name__ == "__main__":
    job_url = input("Paste DIRECT job URL (Indeed / LinkedIn): ").strip()

    try:
        result = extract_job_requirements_from_url(job_url)

        print("\n===== JOB DETAILS EXTRACTION RESULT =====\n")
        print(json.dumps(result, indent=4))

    except Exception as e:
        print(f"\nError while extracting job details: {e}")