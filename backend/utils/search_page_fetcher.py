import json
import time
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright


# ---------------------------------------
# Detect platform
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
# Indeed search page extraction using Playwright
# ---------------------------------------
def extract_indeed_jobs_with_playwright(search_url: str):
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)   # keep False for testing first
        page = browser.new_page()

        # Open page
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

        # Give page some time to render job cards
        page.wait_for_timeout(5000)

        # Try to close cookie popups / interruptions if needed
        # (safe ignore if not present)
        try:
            page.locator("button:has-text('Accept')").click(timeout=2000)
        except:
            pass

        try:
            page.locator("button:has-text('I agree')").click(timeout=2000)
        except:
            pass

        page.wait_for_timeout(3000)

        # Extract all anchors on page
        anchors = page.locator("a").all()

        seen = set()

        for a in anchors:
            try:
                href = a.get_attribute("href")
                text = a.inner_text().strip()

                if not href:
                    continue

                # Indeed job result links often contain /viewjob or /rc/clk
                if "/viewjob" in href or "/rc/clk" in href:
                    full_url = urljoin("https://www.indeed.com", href)

                    title = text.strip()
                    if not title:
                        continue

                    # avoid duplicates
                    if full_url in seen:
                        continue

                    seen.add(full_url)

                    jobs.append({
                        "title": title,
                        "company": "Unknown",   # company extraction comes later / can be improved
                        "job_url": full_url
                    })

            except:
                continue

        browser.close()

    # remove noisy duplicates by title/url
    cleaned = []
    seen_keys = set()

    for job in jobs:
        key = (job["title"].lower(), job["job_url"].lower())
        if key not in seen_keys:
            cleaned.append(job)
            seen_keys.add(key)

    return cleaned


# ---------------------------------------
# LinkedIn search page extraction (starter version)
# ---------------------------------------
def extract_linkedin_jobs_with_playwright(search_url: str):
    jobs = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        anchors = page.locator("a").all()
        seen = set()

        for a in anchors:
            try:
                href = a.get_attribute("href")
                text = a.inner_text().strip()

                if not href:
                    continue

                if "/jobs/view/" in href:
                    full_url = urljoin("https://www.linkedin.com", href)

                    if not text:
                        continue

                    if full_url in seen:
                        continue

                    seen.add(full_url)

                    jobs.append({
                        "title": text,
                        "company": "Unknown",
                        "job_url": full_url
                    })
            except:
                continue

        browser.close()

    return jobs


# ---------------------------------------
# Main extraction
# ---------------------------------------
def extract_jobs_from_search_page(search_url: str):
    platform = detect_platform(search_url)

    if platform == "indeed":
        jobs = extract_indeed_jobs_with_playwright(search_url)
    elif platform == "linkedin":
        jobs = extract_linkedin_jobs_with_playwright(search_url)
    else:
        jobs = []

    return {
        "platform": platform,
        "search_url": search_url,
        "total_jobs_found": len(jobs),
        "jobs": jobs
    }


# ---------------------------------------
# Terminal test
# ---------------------------------------
if __name__ == "__main__":
    search_url = input("Paste Indeed / LinkedIn SEARCH PAGE URL: ").strip()

    try:
        result = extract_jobs_from_search_page(search_url)

        print("\n===== SEARCH PAGE EXTRACTION RESULT =====\n")
        print(json.dumps(result, indent=4))

    except Exception as e:
        print(f"\nError while extracting jobs from search page: {e}")