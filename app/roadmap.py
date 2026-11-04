"""Roadmap: a learning plan built ONLY from the student's real skill gaps (one week per gap)."""
from __future__ import annotations

from utils.skill_database import learning_plan, skill_practice, skill_why


def build_roadmap(gaps: list[dict], role: str) -> list[dict]:
    """gaps = skills that are GAP or PARTIAL (Required first). Returns one week per skill."""
    weeks = []
    for i, g in enumerate(gaps, 1):
        lp = learning_plan(g["skill"])
        why = skill_why(g["skill"], g["level"], role)
        if g["status"] == "PARTIAL":
            why += " Your resume shows only weak evidence, so the goal is to learn it properly and show it in a project."
        weeks.append(dict(week=i, skill=g["skill"], level=g["level"], status=g["status"], why=why, topics=lp["topics"],
                          practice=skill_practice(g["skill"]), project=lp["project"], generic=lp["generic"]))
    return weeks


def skill_items(skill: str) -> list[str]:
    """Every checkbox for one skill (used by the Roadmap and the Progress Tracker)."""
    lp = learning_plan(skill)
    return lp["topics"] + ["Practice task: " + skill_practice(skill), "Mini project: " + lp["project"]]


def skill_progress(skill: str, done: dict) -> tuple[int, int]:
    items = skill_items(skill)
    return sum(1 for it in items if done.get(f"{skill}|{it}")), len(items)


def progress_label(gap: dict, done: dict) -> str:
    d, n = skill_progress(gap["skill"], done)
    return "Completed" if d == n else "In progress" if d else ("Partial" if gap["status"] == "PARTIAL" else "Missing")


def completed_skills(gaps: list[dict], done: dict) -> set:
    return {g["skill"] for g in gaps if progress_label(g, done) == "Completed"}