import os
import re
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


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


def guess_field_key(label_text: str):
    label_text = normalize(label_text)
    for field_key, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in label_text:
                return field_key
    return None


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def try_fill_input(locator, value: str):
    if not value:
        return False

    try:
        locator.fill("")
        locator.fill(value)
        return True
    except:
        pass

    try:
        locator.click()
        locator.type(value, delay=20)
        return True
    except:
        pass

    return False


def fill_common_form_fields(page, profile):
    filled = []
    elements = page.locator("input, textarea").all()

    for el in elements:
        try:
            input_type = normalize(el.get_attribute("type") or "")
            name_attr = normalize(el.get_attribute("name") or "")
            placeholder = normalize(el.get_attribute("placeholder") or "")
            aria_label = normalize(el.get_attribute("aria-label") or "")

            if input_type in ["hidden", "submit", "button", "file", "radio", "checkbox", "password"]:
                continue

            if not el.is_visible():
                continue

            label_text = " ".join([name_attr, placeholder, aria_label]).strip()

            if not label_text:
                try:
                    element_id = el.get_attribute("id")
                    if element_id:
                        lbl = page.locator(f"label[for='{element_id}']").first
                        if lbl.count() > 0:
                            label_text = normalize(lbl.inner_text())
                except:
                    pass

            if not label_text:
                continue

            field_key = guess_field_key(label_text)
            if not field_key:
                continue

            profile_value = safe_text(profile.get(field_key))
            if not profile_value:
                continue

            try:
                current_val = el.input_value()
                if current_val and current_val.strip():
                    continue
            except:
                pass

            if try_fill_input(el, profile_value):
                filled.append({
                    "field": field_key,
                    "value": profile_value
                })

        except:
            continue

    return filled


def upload_resume_if_present(page, resume_path: str):
    uploaded = False
    uploaded_inputs = 0

    if not resume_path or not os.path.exists(resume_path):
        return {
            "uploaded": False,
            "inputs_found": 0,
            "resume_path": resume_path
        }

    file_inputs = page.locator("input[type='file']").all()

    for inp in file_inputs:
        try:
            if inp.is_visible():
                inp.set_input_files(resume_path)
                uploaded = True
                uploaded_inputs += 1
        except:
            continue

    return {
        "uploaded": uploaded,
        "inputs_found": uploaded_inputs,
        "resume_path": resume_path
    }


def answer_basic_yes_no_questions(page, profile):
    answered = []

    yes_no_map = {
        "authorized to work": safe_text(profile.get("work_authorization", "Yes")),
        "work authorization": safe_text(profile.get("work_authorization", "Yes")),
        "require sponsorship": safe_text(profile.get("require_sponsorship", "No")),
        "visa sponsorship": safe_text(profile.get("require_sponsorship", "No")),
        "legally authorized": safe_text(profile.get("work_authorization", "Yes")),
    }

    selects = page.locator("select").all()

    for sel in selects:
        try:
            if not sel.is_visible():
                continue

            name_attr = normalize(sel.get_attribute("name") or "")
            aria_label = normalize(sel.get_attribute("aria-label") or "")
            combined = f"{name_attr} {aria_label}".strip()

            if not combined:
                continue

            for key_text, answer in yes_no_map.items():
                if key_text in combined:
                    try:
                        sel.select_option(label=answer)
                        answered.append({
                            "question": key_text,
                            "answer": answer
                        })
                        break
                    except:
                        # fallback: try yes/no by value if label fails
                        try:
                            sel.select_option(answer.lower())
                            answered.append({
                                "question": key_text,
                                "answer": answer
                            })
                            break
                        except:
                            pass
        except:
            continue

    return answered


def click_apply_button(page):
    apply_texts = [
        "Apply now",
        "Apply with Indeed",
        "Apply",
        "Continue application",
        "Continue to application",
        "Easy Apply",
        "Submit application"
    ]

    # Role-based button search
    for txt in apply_texts:
        try:
            btn = page.get_by_role("button", name=txt)
            if btn.count() > 0:
                btn.first.click(timeout=3000)
                page.wait_for_timeout(2500)
                return True
        except:
            pass

    # Generic locator fallback
    for txt in apply_texts:
        try:
            loc = page.locator(f"text={txt}")
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                page.wait_for_timeout(2500)
                return True
        except:
            pass

    return False


def dismiss_common_popups(page):
    popup_texts = [
        "Accept",
        "I agree",
        "Got it",
        "Continue",
        "OK",
        "Allow all"
    ]

    for txt in popup_texts:
        try:
            btn = page.locator(f"button:has-text('{txt}')").first
            if btn.count() > 0:
                btn.click(timeout=1500)
                page.wait_for_timeout(800)
        except:
            pass


def auto_apply_to_job(
    job_url: str,
    resume_path: str,
    profile: dict,
    interactive: bool = False,
    headless: bool = False,
    pause_ms_non_interactive: int = 3000
):
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found: {resume_path}")

    platform = detect_platform(job_url)

    result = {
        "platform": platform,
        "job_url": job_url,
        "resume_path": resume_path,
        "apply_clicked": False,
        "filled_fields": [],
        "answered_questions": [],
        "resume_upload": {},
        "status": "started",
        "error": None
    }

    browser = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()

            page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)

            dismiss_common_popups(page)

            result["apply_clicked"] = click_apply_button(page)
            page.wait_for_timeout(2500)

            result["filled_fields"] = fill_common_form_fields(page, profile)
            result["answered_questions"] = answer_basic_yes_no_questions(page, profile)
            result["resume_upload"] = upload_resume_if_present(page, resume_path)

            result["status"] = "filled_review_pending"

            print("\n===== AUTO APPLY STATUS =====")
            print(result)

            if interactive:
                print("\nReview the browser manually. Press ENTER to continue...")
                try:
                    input()
                except EOFError:
                    # If run in a non-interactive environment by mistake,
                    # do not crash the whole pipeline.
                    pass
            else:
                page.wait_for_timeout(pause_ms_non_interactive)

            browser.close()

    except PlaywrightTimeoutError as e:
        result["status"] = "failed"
        result["error"] = f"Timeout while processing job: {str(e)}"
        try:
            if browser:
                browser.close()
        except:
            pass

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        try:
            if browser:
                browser.close()
        except:
            pass

    return result