import os
import re
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from candidate_profile import CANDIDATE_PROFILE


# ---------------------------------------
# Helpers
# ---------------------------------------
def normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if "indeed" in domain:
        return "indeed"
    elif "linkedin" in domain:
        return "linkedin"
    return "other"


# ---------------------------------------
# Field alias mapping
# We use these to guess which input belongs to which profile field
# ---------------------------------------
FIELD_ALIASES = {
    "full_name": ["full name", "name"],
    "first_name": ["first name", "given name"],
    "last_name": ["last name", "surname", "family name"],
    "email": ["email", "email address"],
    "phone": ["phone", "mobile", "phone number", "contact number"],
    "location": ["location", "city", "address"],
    "linkedin": ["linkedin"],
    "github": ["github"],
    "portfolio": ["portfolio", "website", "personal website"],
    "current_company": ["current company", "employer", "company"],
    "current_title": ["current title", "job title", "designation"],
    "years_experience": ["years of experience", "experience"],
}


# ---------------------------------------
# Detect likely field key from label text
# ---------------------------------------
def guess_field_key(label_text: str):
    label_text = normalize(label_text)

    for field_key, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in label_text:
                return field_key

    return None


# ---------------------------------------
# Fill an input if possible
# ---------------------------------------
def try_fill_input(locator, value: str):
    try:
        locator.fill("")
        locator.fill(value)
        return True
    except:
        try:
            locator.click()
            locator.type(value, delay=20)
            return True
        except:
            return False


# ---------------------------------------
# Fill text-like inputs based on labels / placeholders / names
# ---------------------------------------
def fill_common_form_fields(page, profile):
    filled = []

    # collect all input + textarea fields
    elements = page.locator("input, textarea").all()

    for el in elements:
        try:
            input_type = (el.get_attribute("type") or "").lower()
            name_attr = normalize(el.get_attribute("name") or "")
            placeholder = normalize(el.get_attribute("placeholder") or "")
            aria_label = normalize(el.get_attribute("aria-label") or "")
            value = el.input_value() if el.is_visible() else ""

            # skip hidden / already-filled / file inputs / buttons / radios / checkboxes
            if input_type in ["hidden", "submit", "button", "file", "radio", "checkbox"]:
                continue

            if not el.is_visible():
                continue

            # Build a combined label-like text
            label_text = " ".join([name_attr, placeholder, aria_label]).strip()

            # If empty, try associated label via DOM
            if not label_text:
                try:
                    element_id = el.get_attribute("id")
                    if element_id:
                        lbl = page.locator(f"label[for='{element_id}']").first
                        if lbl.count() > 0:
                            label_text = normalize(lbl.inner_text())
                except:
                    pass

            field_key = guess_field_key(label_text)
            if not field_key:
                continue

            profile_value = profile.get(field_key)
            if not profile_value:
                continue

            # don't overwrite if already filled with something meaningful
            if value and value.strip():
                continue

            success = try_fill_input(el, str(profile_value))
            if success:
                filled.append((field_key, str(profile_value)))

        except:
            continue

    return filled


# ---------------------------------------
# Upload resume to visible file inputs
# ---------------------------------------
def upload_resume_if_present(page, resume_path: str):
    uploaded = False

    file_inputs = page.locator("input[type='file']").all()

    for inp in file_inputs:
        try:
            if inp.is_visible():
                inp.set_input_files(resume_path)
                uploaded = True
        except:
            continue

    return uploaded


# ---------------------------------------
# Try clicking apply buttons
# ---------------------------------------
def click_apply_button(page):
    apply_texts = [
        "Apply now",
        "Apply with Indeed",
        "Apply",
        "Continue application",
        "Continue to application"
    ]

    for txt in apply_texts:
        try:
            btn = page.get_by_role("button", name=txt)
            if btn.count() > 0:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(3000)
                return True
        except:
            pass

    # fallback: click visible text match
    for txt in apply_texts:
        try:
            loc = page.locator(f"text={txt}")
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                page.wait_for_timeout(3000)
                return True
        except:
            pass

    return False


# ---------------------------------------
# Fill common select/dropdowns if we find simple yes/no questions
# ---------------------------------------
def answer_basic_yes_no_questions(page, profile):
    answered = []

    yes_no_map = {
        "authorized to work": profile.get("work_authorization", "Yes"),
        "work authorization": profile.get("work_authorization", "Yes"),
        "require sponsorship": profile.get("require_sponsorship", "No"),
        "visa sponsorship": profile.get("require_sponsorship", "No"),
    }

    # Handle select dropdowns
    selects = page.locator("select").all()
    for sel in selects:
        try:
            if not sel.is_visible():
                continue

            name_attr = normalize(sel.get_attribute("name") or "")
            aria_label = normalize(sel.get_attribute("aria-label") or "")
            combined = f"{name_attr} {aria_label}"

            for key_text, answer in yes_no_map.items():
                if key_text in combined:
                    # attempt direct select
                    try:
                        sel.select_option(label=answer)
                        answered.append((key_text, answer))
                        break
                    except:
                        try:
                            if answer.lower().startswith("y"):
                                sel.select_option(index=1)
                            else:
                                sel.select_option(index=2)
                            answered.append((key_text, answer))
                            break
                        except:
                            pass
        except:
            continue

    return answered


# ---------------------------------------
# Indeed Auto Apply
# ---------------------------------------
def auto_apply_indeed(job_url: str, resume_path: str, profile: dict):
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume file not found: {resume_path}")

    result = {
        "platform": "indeed",
        "job_url": job_url,
        "resume_path": resume_path,
        "apply_clicked": False,
        "filled_fields": [],
        "uploaded_resume": False,
        "answered_questions": [],
        "status": "started"
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        # dismiss popups if present
        for txt in ["Accept", "I agree", "Got it", "Continue"]:
            try:
                page.locator(f"button:has-text('{txt}')").first.click(timeout=2000)
                page.wait_for_timeout(1000)
            except:
                pass

        # Click Apply
        result["apply_clicked"] = click_apply_button(page)

        # If apply button wasn't found, still attempt filling if form is already on page
        page.wait_for_timeout(3000)

        # Fill fields
        filled = fill_common_form_fields(page, profile)
        result["filled_fields"] = filled

        # Answer simple dropdowns
        answered = answer_basic_yes_no_questions(page, profile)
        result["answered_questions"] = answered

        # Upload resume
        uploaded = upload_resume_if_present(page, resume_path)
        result["uploaded_resume"] = uploaded

        result["status"] = "filled_review_pending"

        print("\n===== AUTO APPLY STATUS =====\n")
        print("Apply clicked:", result["apply_clicked"])
        print("Fields filled:", result["filled_fields"])
        print("Answered questions:", result["answered_questions"])
        print("Resume uploaded:", result["uploaded_resume"])

        print("\nApplication is filled as much as possible.")
        print("Review the browser manually now.")
        print("Press ENTER here after reviewing / when you want to close the browser...")

        input()

        browser.close()

    return result


# ---------------------------------------
# Main wrapper
# ---------------------------------------
def auto_apply(job_url: str, resume_path: str, profile: dict):
    platform = detect_platform(job_url)

    if platform == "indeed":
        return auto_apply_indeed(job_url, resume_path, profile)

    return {
        "platform": platform,
        "job_url": job_url,
        "status": "unsupported_for_now",
        "message": "This version currently supports Indeed auto-fill only."
    }


# ---------------------------------------
# Terminal test
# ---------------------------------------
if __name__ == "__main__":
    job_url = input("Paste Indeed job URL: ").strip()
    resume_path = input("Paste full resume file path: ").strip()

    try:
        result = auto_apply(job_url, resume_path, CANDIDATE_PROFILE)

        print("\n===== FINAL RESULT =====\n")
        print(result)

    except Exception as e:
        print(f"\nError during auto-apply: {e}")