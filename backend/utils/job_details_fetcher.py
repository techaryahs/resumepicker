import json
import re
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from jd_parser import parse_job_description


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "indeed" in domain:
        return "indeed"
    elif "linkedin" in domain:
        return "linkedin"
    return "other" 


def extract_indeed_job_text(job_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        for txt in ["Accept", "I agree", "Got it"]:
            try:
                page.locator(f"button:has-text('{txt}')").first.click(timeout=1500)
                page.wait_for_timeout(1000)
            except:
                pass

        title = ""
        company = ""
        description = ""

        try:
            title = page.locator("h1").first.inner_text().strip()
        except:
            pass

        company_selectors = [
            "[data-testid='inlineHeader-companyName']",
            ".jobsearch-CompanyInfoWithoutHeaderImage",
            "div[data-company-name]",
            "span.css-1saizt3"
        ]
        for selector in company_selectors:
            try:
                company = page.locator(selector).first.inner_text().strip()
                if company:
                    break
            except:
                continue

        description_selectors = [
            "#jobDescriptionText",
            "[data-testid='jobsearch-JobComponent-description']"
        ]
        for selector in description_selectors:
            try:
                description = page.locator(selector).first.inner_text().strip()
                if description:
                    break
            except:
                continue

        if not description:
            try:
                description = page.locator("body").inner_text()
            except:
                description = ""

        browser.close()

        raw = f"Role: {title}\nCompany: {company}\n{description}".strip()
        return {
            "title": title,
            "company": company,
            "raw_text": raw
        }


def extract_linkedin_job_text(job_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        title = ""
        company = ""
        description = ""

        try:
            title = page.locator("h1").first.inner_text().strip()
        except:
            pass

        company_selectors = [
            "a.topcard__org-name-link",
            "span.topcard__flavor",
            "div.topcard__org-name-link"
        ]
        for selector in company_selectors:
            try:
                company = page.locator(selector).first.inner_text().strip()
                if company:
                    break
            except:
                continue

        description_selectors = [
            "div.show-more-less-html__markup",
            "div.description__text",
            "section.show-more-less-html"
        ]
        for selector in description_selectors:
            try:
                description = page.locator(selector).first.inner_text().strip()
                if description:
                    break
            except:
                continue

        if not description:
            try:
                description = page.locator("body").inner_text()
            except:
                description = ""

        browser.close()

        raw = f"Role: {title}\nCompany: {company}\n{description}".strip()
        return {
            "title": title,
            "company": company,
            "raw_text": raw
        }


def extract_generic_job_text(job_url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        body = ""
        try:
            body = page.locator("body").inner_text()
        except:
            pass

        browser.close()

        return {
            "title": "",
            "company": "",
            "raw_text": body
        }


def extract_job_requirements_from_url(job_url: str):
    platform = detect_platform(job_url)

    if platform == "indeed":
        data = extract_indeed_job_text(job_url)
    elif platform == "linkedin":
        data = extract_linkedin_job_text(job_url)
    else:
        data = extract_generic_job_text(job_url)

    raw_text = data["raw_text"].strip()

    if not raw_text:
        return {
            "source_url": job_url,
            "platform": platform,
            "error": "Could not extract job text."
        }

    parsed = parse_job_description(raw_text)

    return {
        "source_url": job_url,
        "platform": platform,
        "extracted_title": data["title"],
        "extracted_company": data["company"],
        "raw_job_text_preview": raw_text[:2000],
        "parsed_requirements": parsed
    }


if __name__ == "__main__":
    url = input("Paste job URL: ").strip()
    result = extract_job_requirements_from_url(url)

    print("\n===== JOB DETAILS EXTRACTION RESULT =====\n")
    print(json.dumps(result, indent=4))