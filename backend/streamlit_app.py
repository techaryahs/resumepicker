import os
import sys
import json
import subprocess
import streamlit as st

# -----------------------------------------
# Paths
# -----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UTILS_DIR = os.path.join(BASE_DIR, "utils")
CANDIDATE_PROFILE_FILE = os.path.join(UTILS_DIR, "candidate_profile.py")
RUN_PIPELINE_FILE = os.path.join(UTILS_DIR, "run_full_auto_apply.py")


# -----------------------------------------
# Save candidate profile into candidate_profile.py
# -----------------------------------------
def save_candidate_profile(profile: dict):
    content = "CANDIDATE_PROFILE = " + json.dumps(profile, indent=4)
    with open(CANDIDATE_PROFILE_FILE, "w", encoding="utf-8") as f:
        f.write(content + "\n")


# -----------------------------------------
# Run the full pipeline
# We pass search URL + max jobs via stdin because your
# run_full_auto_apply.py currently asks for input().
# -----------------------------------------
def run_pipeline(search_url: str, max_jobs: int = 5):
    if not os.path.exists(RUN_PIPELINE_FILE):
        raise FileNotFoundError(f"run_full_auto_apply.py not found at: {RUN_PIPELINE_FILE}")

    # Feed the two expected inputs:
    # 1) search_url
    # 2) max_jobs
    user_input = f"{search_url}\n{max_jobs}\n"

    process = subprocess.run(
        [sys.executable, RUN_PIPELINE_FILE],
        input=user_input,
        text=True,
        capture_output=True,
        cwd=UTILS_DIR
    )

    return {
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr
    }


# -----------------------------------------
# Streamlit page config
# -----------------------------------------
st.set_page_config(
    page_title="ResumePicker Auto Apply",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 ResumePicker Auto Apply")
st.write("Paste a job search URL, fill candidate profile details, and start the auto-apply pipeline.")

# -----------------------------------------
# Session defaults
# -----------------------------------------
default_profile = {
    "full_name": "",
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "github": "",
    "portfolio": "",
    "current_company": "",
    "current_title": "",
    "years_experience": "",
    "work_authorization": "Yes",
    "require_sponsorship": "No"
}

if "profile" not in st.session_state:
    st.session_state.profile = default_profile.copy()

if "search_url" not in st.session_state:
    st.session_state.search_url = ""

if "max_jobs" not in st.session_state:
    st.session_state.max_jobs = 5


# -----------------------------------------
# Top section: Search URL
# -----------------------------------------
st.subheader("1) Job Search URL")

search_url = st.text_input(
    "Paste Indeed / LinkedIn Search URL",
    value=st.session_state.search_url,
    placeholder="https://www.indeed.com/jobs?q=AI+Engineer&l=Chicago%2C+IL"
)

max_jobs = st.number_input(
    "How many jobs to process?",
    min_value=1,
    max_value=50,
    value=st.session_state.max_jobs,
    step=1
)

st.session_state.search_url = search_url
st.session_state.max_jobs = max_jobs

st.divider()

# -----------------------------------------
# Candidate profile form
# -----------------------------------------
st.subheader("2) Candidate Profile")

with st.form("candidate_profile_form"):
    col1, col2 = st.columns(2)

    with col1:
        full_name = st.text_input("Full Name", value=st.session_state.profile["full_name"])
        first_name = st.text_input("First Name", value=st.session_state.profile["first_name"])
        last_name = st.text_input("Last Name", value=st.session_state.profile["last_name"])
        email = st.text_input("Email", value=st.session_state.profile["email"])
        phone = st.text_input("Phone", value=st.session_state.profile["phone"])
        location = st.text_input("Location", value=st.session_state.profile["location"])
        linkedin = st.text_input("LinkedIn", value=st.session_state.profile["linkedin"])

    with col2:
        github = st.text_input("GitHub", value=st.session_state.profile["github"])
        portfolio = st.text_input("Portfolio", value=st.session_state.profile["portfolio"])
        current_company = st.text_input("Current Company", value=st.session_state.profile["current_company"])
        current_title = st.text_input("Current Title", value=st.session_state.profile["current_title"])
        years_experience = st.text_input("Years of Experience", value=st.session_state.profile["years_experience"])
        work_authorization = st.selectbox(
            "Work Authorization",
            ["Yes", "No"],
            index=0 if st.session_state.profile["work_authorization"] == "Yes" else 1
        )
        require_sponsorship = st.selectbox(
            "Require Sponsorship",
            ["No", "Yes"],
            index=0 if st.session_state.profile["require_sponsorship"] == "No" else 1
        )

    save_profile_clicked = st.form_submit_button("Save Candidate Profile")

    if save_profile_clicked:
        st.session_state.profile = {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin": linkedin,
            "github": github,
            "portfolio": portfolio,
            "current_company": current_company,
            "current_title": current_title,
            "years_experience": years_experience,
            "work_authorization": work_authorization,
            "require_sponsorship": require_sponsorship
        }

        save_candidate_profile(st.session_state.profile)
        st.success("Candidate profile saved to utils/candidate_profile.py")

st.divider()

# -----------------------------------------
# Start button
# -----------------------------------------
st.subheader("3) Start Auto Apply")

colA, colB = st.columns([1, 3])

with colA:
    start_clicked = st.button("🚀 Start Auto Apply", use_container_width=True)

with colB:
    st.caption("This will save the candidate profile, run the search-page extraction, match resumes, and start the Playwright auto-apply pipeline.")

# -----------------------------------------
# Validation + Run
# -----------------------------------------
if start_clicked:
    # refresh state from current form-ish values if user didn't click Save first
    # (only values already stored in session_state.profile are used unless they pressed save)
    # so we force-save current session copy if missing.
    if not st.session_state.profile.get("full_name"):
        st.warning("Please fill and save the candidate profile first.")
    elif not search_url.strip():
        st.warning("Please enter a job search URL.")
    else:
        try:
            save_candidate_profile(st.session_state.profile)

            st.info("Starting auto-apply pipeline... please wait.")

            with st.spinner("Running pipeline..."):
                result = run_pipeline(search_url=search_url.strip(), max_jobs=int(max_jobs))

            if result["returncode"] == 0:
                st.success("Pipeline finished successfully.")
            else:
                st.error(f"Pipeline exited with code {result['returncode']}")

            st.subheader("Pipeline Output")
            st.code(result["stdout"] if result["stdout"] else "No stdout output.", language="bash")

            if result["stderr"]:
                st.subheader("Pipeline Errors / Logs")
                st.code(result["stderr"], language="bash")

        except Exception as e:
            st.exception(e)