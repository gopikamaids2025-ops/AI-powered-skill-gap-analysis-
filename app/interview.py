"""Mock Interview: rule-based questions built from the student's target job and resume skills.

Answers are scored by checking key concepts, length and structure. No AI/LLM evaluates the answer.
"""
from __future__ import annotations

import re

from utils.skill_database import learning_plan

# Each keyword group is "alt1|alt2"; a group counts as covered if any alternative appears in the answer.
QUESTIONS = {
    "Python": {
        "Easy": [("What is the difference between a list and a tuple in Python?", ["mutable", "immutable", "tuple", "hashable|dictionary key|faster|memory"]),
                 ("Explain how a Python dictionary works and where you would use it.", ["key", "value", "hash", "lookup|o(1)|constant", "get|items|keys"])],
        "Medium": [("Explain the difference between a shallow copy and a deep copy.", ["reference", "nested|inner", "shallow|copy.copy", "deepcopy|deep copy", "independent|modify|change"]),
                   ("What are generators and why would you use them?", ["yield", "lazy|on demand|one at a time", "memory", "iterator|iterable|next"])],
        "Hard": [("Explain the GIL and how it affects multithreading in Python.", ["global interpreter lock|gil", "one thread|single thread", "cpu-bound|cpu bound", "multiprocessing|process", "i/o|io-bound|asyncio|threading"]),
                 ("How does Python manage memory?", ["reference count", "garbage collect|gc", "cycle|circular", "heap", "allocator|pymalloc|del"])]},
    "SQL": {
        "Easy": [("What is the difference between WHERE and HAVING?", ["where", "having", "group by|aggregate", "row|filter|before|after"]),
                 ("What is the difference between a primary key and a foreign key?", ["unique", "null", "foreign", "reference|link|relationship", "table"])],
        "Medium": [("Explain the different types of SQL joins.", ["inner", "left", "right", "full|outer", "match|null|rows"]),
                   ("What is normalization and why is it used?", ["redundan|duplicate", "1nf|2nf|3nf|normal form", "anomal|integrity", "table"])],
        "Hard": [("What is an index and when can it hurt performance?", ["b-tree|tree|lookup", "speed|faster|query", "write|insert|update|slow", "storage|space|memory", "selective|cardinality|column"]),
                 ("Explain the ACID properties of transactions.", ["atomic", "consisten", "isolat", "durab", "commit|rollback|transaction"])]},
    "DSA": {
        "Easy": [("Compare an array and a linked list.", ["contiguous|index|random access", "o(1)", "insert|delete", "o(n)", "pointer|node|dynamic"]),
                 ("What is the difference between a stack and a queue?", ["lifo|last in", "fifo|first in", "push|pop", "enqueue|dequeue|front|rear"])],
        "Medium": [("How does binary search work and what is its complexity?", ["sorted", "middle|mid", "half|divide", "o(log n)|log n|logarithmic"]),
                   ("Explain BFS and DFS and when to use each.", ["queue", "stack|recursion", "level|shortest path", "depth|backtrack|deep", "graph|tree|visited"])],
        "Hard": [("Explain dynamic programming with an example.", ["overlapping|subproblem", "optimal substructure|optimal", "memo|table|tabulation", "fibonacci|knapsack|lcs|coin", "recursion|brute force|exponential"]),
                 ("How does a hash table handle collisions?", ["chaining|linked list", "open addressing|probing", "hash function|hash", "load factor|resize|rehash", "o(1)|average"])]},
    "Machine Learning": {
        "Easy": [("What is the difference between supervised and unsupervised learning?", ["label", "supervised", "unsupervised", "cluster|k-means|pattern", "classification|regression"]),
                 ("What is overfitting?", ["training", "test|unseen|generaliz", "complex|noise|memoriz", "regulariz|cross-validation|more data|simplif"])],
        "Medium": [("Explain precision, recall and F1-score.", ["precision", "recall", "f1|harmonic", "false positive", "false negative|imbalanc"]),
                   ("What is the bias-variance tradeoff?", ["bias", "variance", "underfit", "overfit", "complex|tradeoff|balance"])],
        "Hard": [("Why do we scale features, and which models are sensitive to it?", ["scale|standardi|normali", "distance|knn|svm", "gradient|convergence|logistic|regression", "tree|not sensitive|invariant", "mean|variance|standard deviation|range"]),
                 ("Explain how L1 and L2 regularization work.", ["penalt", "l1|lasso", "l2|ridge", "sparse|zero|feature selection", "shrink|weights|coefficient|overfit"])]},
    "Data Science": {
        "Easy": [("What steps are in a typical data science workflow?", ["collect|acquire", "clean|preprocess", "explor|eda", "model", "evaluat|deploy|communicat"]),
                 ("How would you handle missing values in a dataset?", ["drop|remove", "impute|fill|mean|median", "mode", "pattern|why|indicator|domain"])],
        "Medium": [("What is cross-validation and why use it?", ["fold|k-fold", "train", "validation|test", "generaliz|overfit", "average|mean|variance"]),
                   ("How do you detect and treat outliers?", ["iqr|z-score|box plot|boxplot", "outlier", "remove|cap|winsor|transform", "domain|context|error|genuine|valid"])],
        "Hard": [("How would you handle a highly imbalanced dataset?", ["smote|oversampl", "undersampl", "class weight|class_weight", "precision|recall|f1|roc|pr curve", "stratif|resampl|threshold"]),
                 ("Explain the difference between correlation and causation with an example.", ["correlat", "caus", "confound|third variable|hidden", "experiment|a/b|randomi", "example|ice cream|for instance"])]},
    "HR": {
        "Easy": [("Tell me about yourself.", ["student|b.tech|degree|studying", "project", "skill|python|technolog", "goal|interest|aspir|looking", "internship|experience"]),
                 ("Why do you want to work for our company?", ["research|know|learn about|culture|product", "skill|fit|contribute|align", "grow|learn|opportunit", "team|value|mission"])],
        "Medium": [("Describe a challenge you faced in a team project and how you handled it.", ["situation|challenge|problem", "task|role|responsib", "action|i did|i decided|i suggested", "result|outcome|delivered|resolved", "learn"]),
                   ("What are your strengths and weaknesses?", ["strength", "weakness", "example|for instance|project", "improv|working on|learning|steps", "because"])],
        "Hard": [("Tell me about a time you failed and what you learned.", ["fail|mistake|missed", "responsib|ownership|my part", "action|corrected|fixed|changed", "learn", "result|now|since|next time|improv"]),
                 ("Where do you see yourself in five years?", ["grow|learn|skill", "role|senior|lead|engineer|analyst", "contribut|impact|company", "realistic|goal|plan|step", "team|mentor"])]},
}

MIN_WORDS = {"Easy": 25, "Medium": 40, "Hard": 60}

def evaluate_answer(answer: str, keywords: list[str], difficulty: str) -> dict:
    low = answer.lower()
    covered = [k for k in keywords if any(alt.strip() in low for alt in k.split("|"))]
    missed = [k.split("|")[0] for k in keywords if k not in covered]
    words = len(re.findall(r"\w+", answer))
    coverage = len(covered) / len(keywords)
    depth = min(words / MIN_WORDS[difficulty], 1)
    structure = 1.0 if (len(re.findall(r"[.!?]", answer)) >= 2 or re.search(r"example|for instance|such as|because", low)) else 0.4
    score = round(70 * coverage + 20 * depth + 10 * structure)
    fb = ["Strong answer covering the key ideas." if coverage >= 0.8 else
          "Partly covered; add the missing concepts." if coverage >= 0.5 else "Key concepts are missing; review the topic."]
    if depth < 1:
        fb.append(f"Answer is short ({words} words); aim for about {MIN_WORDS[difficulty]}+.")
    if structure < 1:
        fb.append("Use complete sentences and add an example.")
    return dict(score=score, covered=len(covered), total=len(keywords), missed=missed, feedback=" ".join(fb), words=words)

BANK_CATEGORY = {"Python": "Python", "SQL": "SQL", "MySQL": "SQL", "PostgreSQL": "SQL", "Data Structures": "DSA", "Algorithms": "DSA",
                 "Machine Learning": "Machine Learning", "Deep Learning": "Machine Learning", "Scikit-learn": "Machine Learning",
                 "Statistics": "Data Science", "Data Analysis": "Data Science", "Data Science": "Data Science", "Pandas": "Data Science"}
GENERIC_WORDS = {"basics", "fundamentals", "fundamental", "using", "with", "project", "build", "small", "working", "concepts", "introduction",
                 "practice", "applying", "application", "real", "core", "common", "best", "practices", "your", "data", "and", "the", "for"}


def topic_keywords(skill: str) -> list[str]:
    groups = []
    for t in learning_plan(skill)["topics"]:
        toks = [w for w in re.findall(r"[a-z][a-z+#.]{3,}", t.lower()) if w not in GENERIC_WORDS and w != skill.lower()]
        if toks:
            groups.append("|".join(dict.fromkeys(toks[:4])))
    return groups


def skill_questions(skill: str, diff: str, role: str) -> list[tuple]:
    if skill in BANK_CATEGORY:
        return [(skill, q, k) for q, k in QUESTIONS[BANK_CATEGORY[skill]][diff]]
    kws = topic_keywords(skill)
    q = {"Easy": f"Explain the core concepts of {skill}.",
         "Medium": f"Describe how you would use {skill} in a project as a {role}. Mention key concepts and a practical example.",
         "Hard": f"What challenges, trade-offs and best practices should you consider when using {skill} in a real project?"}[diff]
    return [(skill, q, kws)] if kws else []


def question_pool(category: str, diff: str, ctx: dict) -> list[tuple]:
    role = ctx["job"]["role"]
    if category == "HR":
        pool = [("HR", q, k) for q, k in QUESTIONS["HR"][diff]]
        pool.append(("HR", f"Why do you want to work as a {role}, and what makes you a good fit?",
                     ["interest|passion|motivat", "skill|experience|project", "learn|grow", "team|company|contribute|value"]))
        return pool
    skills = (ctx["job"]["required"] + ctx["job"]["preferred"]) if category == "Target job skills" else ctx["info"]["skills"]
    return [item for s in skills for item in skill_questions(s, diff, role)]