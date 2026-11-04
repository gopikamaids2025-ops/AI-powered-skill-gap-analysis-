# AI-Powered Skill Gap Analysis and Placement Readiness Prediction System

A Streamlit app for students. It compares your resume with a job description, shows your skill gaps, builds a learning
roadmap, and (separately) predicts placement readiness with an ML model.

## Three separate calculations (never mixed)

| Idea | Question it answers | Type | File |
|------|---------------------|------|------|
| A. Skill Gap | What does my resume have compared with THIS job? | Rule-based | `app/skill_gap.py` |
| B. Placement Readiness | What does the trained model predict from my numeric profile? | ML model | `app/placement_model.py` |
| C. Career Roles | Which predefined roles match my current skills? | Rule-based | `app/recommendations.py` |

No AI/LLM is used anywhere. The "Study Advisor" and the mock-interview feedback are rule-based.
None of the numbers is a guarantee of getting a job.

## Folder layout

```
project/
├── .streamlit/config.toml     dark theme
├── app/                       app.py (start here), views*.py, resume_analyzer.py, job_analyzer.py, skill_gap.py,
│                              placement_model.py, recommendations.py, roadmap.py, mentor.py, interview.py,
│                              auth.py, state.py, ui.py
├── utils/                     skill_database.py, helpers.py
├── models/                    placement_model.pkl, scaler.pkl        (your trained files, unchanged)
├── data/                      company_requirements.csv (optional), the training dataset (optional)
├── requirements.txt
└── README.md
```

The training dataset can be `data/placement_dataset.csv` or `data/AI_Powered_Skill_Gap_Placement_Dataset_1000.xlsx`.
It is optional: it is only used to show the model's training ranges and to double-check the feature order.
Registered accounts are saved in `data/users.json` (created automatically, passwords are hashed).

## Run on Windows (Command Prompt or PowerShell)

```
cd path\to\project
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app\app.py
```

Next time, only run `venv\Scripts\activate` and `streamlit run app\app.py`.

## How a student uses it

1. Create an account and log in.
2. **Resume Analysis**: upload a PDF/DOCX/TXT or paste text, then check and fix what was extracted.
3. **Target Job**: paste or upload a job description, then check and fix the Required / Preferred requirements.
4. **Skill Gap**: see MATCH / PARTIAL / GAP for every requirement, with evidence, and the Job Requirement Match %.
5. **Profile**: fill the numeric values the ML model needs (some come from your resume). Then open **Placement Readiness**.
6. **Roadmap**, **Career Roles**, **Progress Tracker**, **Mock Interview**, **Study Advisor**.

## Important facts about the ML inputs

* Feature order is read from the scaler and double-checked against the training dataset.
* Hackathon is coded Yes = 1, No = 0 (checked against the scaler).
* Each number box has a VALID range (for example Attendance 0-100). A value outside the TRAINING range
  (for example Internships: the model saw only 0-2) is kept exactly as entered, but a warning says the prediction is less reliable.
* Values taken from your resume are checked first; impossible values are not stored.

## Known limits

* Resume and job extraction is pattern-based and can make mistakes, which is why you verify and edit it.
* Scanned (image-only) PDFs cannot be read. Paste the text instead.
* Login is a simple demo for a college project, not production security.