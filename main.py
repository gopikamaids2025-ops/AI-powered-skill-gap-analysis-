"""
AI-Powered Skill Gap Analysis and Placement Readiness Prediction System
-----------------------------------------------------------------------
Main entry point. Supports running directly:
    streamlit run main.py
or
    streamlit run app/app.py
"""
import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    app_file = Path(__file__).resolve().parent / "app" / "app.py"
    if not app_file.is_file():
        print(f"Error: Could not find application file at {app_file}")
        sys.exit(1)
    runpy.run_path(str(app_file), run_name="__main__")
