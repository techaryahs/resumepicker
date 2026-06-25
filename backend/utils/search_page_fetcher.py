import json
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "indeed" in domain:
        return "indeed"
    elif "linkedin" in domain:
        return "linkedin"
    return "other"


def extract_indeed_jobs_from_search(page):
    jobs = []
    seen = set()

    page.wait_for_timeout(5000)

    for txt in ["Accept", "I agree", "Got it"]:
        try:
            page.locator(f"button:has-text('{txt}')").first.click(timeout=1500)
            page.wait_for_timeout(1000)
        except:
            pass

    cards = page.locator("a[data-jk], a[href*='/viewjob'], a[href*='/rc/clk']").all()

    for card in cards:
        try:
            href = card.get_attribute("href") or ""
            if not href:
                continue

            job_url = urljoin("https://www.indeed.com", href)

            if job_url in seen:
                continue
            seen.add(job_url)

            title = ""
            try:
                title = card.inner_text().strip()
            except:
                pass

            if not title:
                try:
                    title = card.get_attribute("aria-label") or ""
                except:
                    title = ""

            jobs.append({
                "title": title.strip() or "Unknown Title",
                "company": "Unknown",
                "job_url": job_url
            })
        except:
            continue

    return jobs


def extract_linkedin_jobs_from_search(page):
    jobs = []
    seen = set()

    page.wait_for_timeout(5000)

    cards = page.locator("a[href*='/jobs/view/']").all()

    for card in cards:
        try:
            href = card.get_attribute("href") or ""
            if not href:
                continue

            job_url = urljoin("https://www.linkedin.com", href.split("?")[0])

            if job_url in seen:
                continue
            seen.add(job_url)

            title = ""
            try:
                title = card.inner_text().strip()
            except:
                pass

            jobs.append({
                "title": title or "Unknown Title",
                "company": "Unknown",
                "job_url": job_url
            })
        except:
            continue

    return jobs


# THIS is the function your run_full_auto_apply.py is trying to import
def extract_jobs_from_search_url(search_url: str):
    platform = detect_platform(search_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        if platform == "indeed":
            jobs = extract_indeed_jobs_from_search(page)
        elif platform == "linkedin":
            jobs = extract_linkedin_jobs_from_search(page)
        else:
            jobs = []

        browser.close()

    return {
        "platform": platform,
        "search_url": search_url,
        "total_jobs_found": len(jobs),
        "jobs": jobs
    }


if __name__ == "__main__":
    search_url = input("Paste search page URL: ").strip()
    result = extract_jobs_from_search_url(search_url)

    print("\n===== SEARCH PAGE EXTRACTION RESULT =====\n")
    print(json.dumps(result, indent=4))