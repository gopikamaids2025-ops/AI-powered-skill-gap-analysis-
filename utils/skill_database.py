"""Skill database: detection vocabulary, related skills, learning content and role definitions.

This file only DESCRIBES skills. A skill is reported for a student only if it is found in that student's resume,
and a gap exists only if it appears in the job requirement the student supplied.
"""
from __future__ import annotations

import re

# =============================================================================
# SKILL DATABASE (detection vocabulary only - a skill is reported ONLY if it is
# actually found in the user's resume or in the user's requirement text)
# =============================================================================
# "!" before a name = do not auto-match the bare name (too ambiguous, e.g. "R", "Go").
_SKILL_SRC = {
    "Language": "Python;Java;C++|cpp;C#|csharp|c sharp;JavaScript|js|java script;TypeScript;!Go|golang|go language|go programming;"
                "Kotlin;PHP;Ruby;Scala;Swift;MATLAB;Bash|shell scripting|shell script;!R|r programming|r language|rstudio;"
                "!C|c programming|c language",
    "Database": "SQL;MySQL;PostgreSQL|postgres;SQLite;Oracle|pl/sql|plsql;MongoDB|mongo db;NoSQL;Redis;Firebase;"
                "DBMS|database management systems|database management",
    "Data & Analytics": "Excel|ms excel|microsoft excel|advanced excel;Power BI|powerbi;Tableau;Looker|looker studio;Pandas;NumPy;"
                        "Matplotlib;Seaborn;Statistics|statistical analysis|statistical;"
                        "Data Analysis|data analytics|exploratory data analysis|eda;Data Visualization|data visualisation|data viz;"
                        "Data Cleaning|data preprocessing|data wrangling|data preparation;ETL;Big Data;Hadoop;"
                        "Spark|pyspark|apache spark;Airflow;Google Analytics;A/B Testing|ab testing;Data Modeling|data modelling;Data Mining;Plotly",
    "ML / AI": "Machine Learning|ml;Deep Learning;Data Science;NLP|natural language processing;Computer Vision;"
               "Neural Networks|neural network;TensorFlow;Keras;PyTorch;Scikit-learn|sklearn|scikit learn;OpenCV;"
               "Generative AI|genai|gen ai;LLM|llms|large language models;Feature Engineering;Model Deployment|mlops;"
               "Time Series;Reinforcement Learning;NLTK;XGBoost;Artificial Intelligence",
    "Web": "HTML|html5;CSS|css3;React|reactjs|react.js;Angular|angularjs;Vue|vue.js|vuejs;Node.js|nodejs|node js;"
           "!Express|express.js|expressjs;Django;Flask;FastAPI;Spring Boot|springboot|spring framework|spring mvc;"
           "REST API|rest apis|restful|restful api|restful apis|rest services|restful services;GraphQL;Bootstrap;"
           "Tailwind|tailwind css;jQuery;Web Development|web technologies|full stack|full-stack;Microservices|microservice;"
           ".NET|asp.net|dotnet;Streamlit;Android;Flutter;Next.js|nextjs",
    "Core CS": "Data Structures|dsa|data structure|data structures and algorithms;Algorithms|algorithm|algorithm design;"
               "OOP|oops|object oriented programming|object-oriented programming|object oriented;"
               "Operating Systems|operating system;Computer Networks|computer networking|networking;System Design;"
               "Design Patterns;Problem Solving|problem-solving;Competitive Programming",
    "Tools": "Git;GitHub;Docker;Kubernetes|k8s;Linux|unix;Jira;Postman;Jupyter|jupyter notebook|jupyter notebooks;"
             "Agile|scrum;Version Control|version control system",
    "Cloud / DevOps": "AWS|amazon web services|ec2;Azure|microsoft azure;GCP|google cloud|google cloud platform;"
                      "Cloud Computing|cloud;CI/CD|cicd|continuous integration;DevOps;Jenkins;Terraform",
    "Testing": "Unit Testing|unit tests|pytest|junit;Selenium;Manual Testing;Test Automation|automation testing|automated testing",
    "Soft Skill": "Communication|communication skills|verbal communication|written communication;"
                  "Teamwork|team work|team player|collaboration|collaborative;Leadership;Time Management;Critical Thinking;"
                  "Presentation|presentation skills|public speaking;Adaptability;Analytical Skills|analytical thinking|analytical;"
                  "Project Management;Stakeholder Management",
}
SKILL_CATEGORY: dict[str, str] = {}
SKILL_PATTERNS: dict[str, re.Pattern] = {}
for _cat, _src in _SKILL_SRC.items():
    for _entry in _src.split(";"):
        _parts = [x.strip() for x in _entry.split("|") if x.strip()]
        _noauto = _parts[0].startswith("!")
        _canon = _parts[0].lstrip("!")
        _alts = sorted({a.lower() for a in (_parts[1:] if _noauto else _parts)}, key=len, reverse=True)
        _body = "|".join(re.escape(a).replace(r"\ ", r"\s+") for a in _alts)
        SKILL_PATTERNS[_canon] = re.compile(r"(?<![A-Za-z0-9+#])(?:" + _body + r")(?![A-Za-z0-9+#])", re.I)
        SKILL_CATEGORY[_canon] = _cat
# "C" is matched case-sensitively and only in unambiguous contexts (e.g. "Section C" must not match).
SKILL_PATTERNS["C"] = re.compile(r"(?<![A-Za-z0-9+#.])C\s*/\s*C\+\+|(?<![A-Za-z0-9+#.])C\s*,\s*C\+\+|"
                                 r"(?<![A-Za-z0-9+#.])C\s+(?:programming|language)\b|"
                                 r"\b(?:Java|Python|C\+\+|C#)\s*,\s*C(?![A-Za-z0-9+#.])|\bC\s*,\s*(?:Java|Python)\b")

# Related skills give a PARTIAL match (umbrella skills only; never a full match).
RELATED = {
    "SQL": ["MySQL", "PostgreSQL", "SQLite", "Oracle"], "MySQL": ["SQL", "PostgreSQL", "Oracle"],
    "PostgreSQL": ["SQL", "MySQL"], "NoSQL": ["MongoDB"], "MongoDB": ["NoSQL"],
    "Machine Learning": ["Scikit-learn", "Deep Learning", "TensorFlow", "PyTorch", "Keras", "Data Science"],
    "Deep Learning": ["TensorFlow", "PyTorch", "Keras", "Neural Networks"], "Data Science": ["Machine Learning", "Pandas", "Statistics"],
    "Data Visualization": ["Power BI", "Tableau", "Matplotlib", "Seaborn", "Looker"], "Power BI": ["Tableau", "Data Visualization"],
    "Tableau": ["Power BI", "Data Visualization"], "Data Analysis": ["Pandas", "Excel", "SQL", "Statistics", "NumPy"],
    "Cloud Computing": ["AWS", "Azure", "GCP"], "AWS": ["Cloud Computing", "Azure", "GCP"], "Azure": ["Cloud Computing", "AWS", "GCP"],
    "GCP": ["Cloud Computing", "AWS", "Azure"], "REST API": ["Flask", "Django", "FastAPI", "Spring Boot", "Express", "Node.js"],
    "Web Development": ["HTML", "CSS", "JavaScript", "React", "Angular", "Node.js", "Django", "Flask"],
    "Data Structures": ["Algorithms"], "Algorithms": ["Data Structures"], "Git": ["GitHub"], "GitHub": ["Git"],
    "JavaScript": ["TypeScript", "React", "Angular", "Node.js"], "CI/CD": ["Jenkins", "DevOps"],
    "DevOps": ["Docker", "Kubernetes", "CI/CD", "Jenkins"], "Generative AI": ["LLM"], "LLM": ["Generative AI", "NLP"],
    "Communication": ["Presentation"], "Presentation": ["Communication"],
}

# Learning content per skill: (topics separated by "|", practice project). Used ONLY for skills that are real gaps.
LEARNING = {
    "Python": ("Syntax, data types and control flow|Functions, modules and error handling|Working with files and libraries|OOP basics and virtual environments", "Build a command-line tool that automates a small data task"),
    "Java": ("Java syntax and OOP|Collections and exception handling|File I/O and multithreading basics|JDBC and database connectivity", "Build a console-based management system in Java"),
    "C++": ("C++ syntax, pointers and references|OOP and templates|STL containers and algorithms|Memory management", "Implement a small library-management program using the STL"),
    "JavaScript": ("Core syntax, functions and scope|DOM manipulation and events|Asynchronous JavaScript and fetch|ES6 features", "Build an interactive to-do app that fetches data from an API"),
    "SQL": ("SELECT, WHERE, GROUP BY and HAVING|Joins and subqueries|Window functions and CTEs|Indexes and query optimisation", "Answer 15 business questions on a sample sales database"),
    "MySQL": ("Installing MySQL and basic queries|Joins and normalisation|Stored procedures and views|Connecting MySQL to an application", "Design and query a small MySQL database for a campus application"),
    "MongoDB": ("Documents and collections|CRUD operations|Aggregation pipeline|Connecting MongoDB to an application", "Build a small app that stores and queries data in MongoDB"),
    "Excel": ("Formulas and lookup functions|Pivot tables and charts|Data cleaning and validation|Dashboards and basic automation", "Build a monthly sales report with pivot tables and a dashboard sheet"),
    "Power BI": ("Power BI fundamentals|Data visualization|Dashboard creation|DAX basics", "Build an interactive sales dashboard in Power BI from a public dataset"),
    "Tableau": ("Tableau fundamentals|Charts and calculated fields|Dashboard design|Publishing and sharing", "Build an interactive dashboard in Tableau from a public dataset"),
    "Statistics": ("Descriptive statistics|Probability|Hypothesis testing|Regression basics", "Run a hypothesis test and a simple regression on a public dataset and report the findings"),
    "Data Analysis": ("Data cleaning with Pandas|Exploratory data analysis|Summary statistics and grouping|Communicating insights", "Complete an end-to-end analysis of a public dataset and write up the insights"),
    "Data Visualization": ("Choosing the right chart|Plotting with Matplotlib/Seaborn or Plotly|Dashboard layout and storytelling|Common visualization mistakes", "Create a dashboard that tells a story from a public dataset"),
    "Pandas": ("Series and DataFrames|Cleaning and transforming data|Grouping, merging and pivoting|Time-series handling", "Clean and analyse a messy CSV dataset with Pandas"),
    "NumPy": ("Arrays and indexing|Vectorised operations|Broadcasting|Linear algebra basics", "Re-implement a simple algorithm using NumPy arrays"),
    "Machine Learning": ("Supervised vs unsupervised learning|Training, validation and test splits|Model evaluation metrics|Feature engineering and tuning", "Train and evaluate a classification model on a public dataset"),
    "Deep Learning": ("Neural network basics|Backpropagation and optimisers|CNNs and RNNs|Training and regularisation", "Train a small image classifier and report its accuracy"),
    "NLP": ("Text preprocessing|Tokenisation and embeddings|Text classification|Evaluating NLP models", "Build a sentiment classifier on a public text dataset"),
    "TensorFlow": ("Tensors and the Keras API|Building and training models|Saving and loading models|Callbacks and tuning", "Train and save a small model with TensorFlow/Keras"),
    "PyTorch": ("Tensors and autograd|Building nn.Module models|Training loops|Saving models", "Train a small neural network with PyTorch"),
    "Scikit-learn": ("Estimator API and pipelines|Model selection and cross-validation|Preprocessing and scaling|Metrics and reporting", "Build a scikit-learn pipeline and compare two models"),
    "Data Structures": ("Arrays, linked lists, stacks and queues|Trees and hash tables|Graphs and traversal|Complexity analysis", "Implement core structures from scratch and solve 20 practice problems"),
    "Algorithms": ("Sorting and searching|Recursion and backtracking|Dynamic programming|Greedy methods", "Solve 20 practice problems and explain each solution"),
    "OOP": ("Classes and objects|Inheritance and polymorphism|Encapsulation and abstraction|Design principles", "Model a small system (library, bank) using OOP principles"),
    "Git": ("Repositories, commits and branches|Merging and resolving conflicts|Pull requests and code review|Collaborating through GitHub", "Publish a project to GitHub using branches and pull requests"),
    "GitHub": ("Creating and organising repositories|Writing a clear README|Issues and pull requests|GitHub Pages or Actions basics", "Publish two documented projects with a clear README"),
    "Docker": ("Images and containers|Writing a Dockerfile|Volumes and networking|Docker Compose", "Containerise a small web application with Docker"),
    "Kubernetes": ("Pods, deployments and services|Configuration and secrets|Scaling and updates|Troubleshooting", "Deploy a containerised app to a local Kubernetes cluster"),
    "Linux": ("Shell navigation and file permissions|Process and package management|Shell scripting|Networking commands", "Write a shell script that automates a routine task"),
    "AWS": ("Core services: EC2, S3, IAM|Networking basics (VPC)|Deploying a web app|Cost and security basics", "Deploy a small web app on AWS free tier"),
    "Azure": ("Core services and the portal|Storage and virtual machines|Deploying a web app|Identity and security basics", "Deploy a small web app on Azure"),
    "GCP": ("Core services and the console|Compute and storage|Deploying a web app|IAM basics", "Deploy a small web app on Google Cloud"),
    "Cloud Computing": ("Cloud service models (IaaS, PaaS, SaaS)|Compute, storage and networking|Deploying an application|Security and cost basics", "Deploy a small application to a cloud provider's free tier"),
    "CI/CD": ("Continuous integration concepts|Writing a pipeline|Automated testing in pipelines|Deployment automation", "Add an automated test-and-build pipeline to a GitHub project"),
    "HTML": ("Document structure and semantic tags|Forms and tables|Accessibility basics|Responsive layout", "Build a multi-section personal portfolio page"),
    "CSS": ("Selectors and the box model|Flexbox and grid|Responsive design|Animations", "Style a responsive landing page"),
    "React": ("Components and props|State and hooks|Routing|Fetching data from an API", "Build a small single-page app that consumes an API"),
    "Angular": ("Components and modules|Services and dependency injection|Routing and forms|HTTP client", "Build a small CRUD single-page app in Angular"),
    "Node.js": ("Node runtime and modules|Express basics|Working with databases|Authentication basics", "Build a REST API with Node.js and a database"),
    "Django": ("Models, views and templates|URL routing and forms|Django ORM|Authentication and deployment", "Build a CRUD web application in Django"),
    "Flask": ("Routes and templates|Forms and sessions|Connecting to a database|Building JSON APIs", "Build a small Flask web app with a database"),
    "FastAPI": ("Path operations and models|Validation with Pydantic|Async endpoints|Authentication and docs", "Build and document a small API with FastAPI"),
    "Spring Boot": ("Spring Boot fundamentals|REST APIs|Dependency Injection|CRUD application", "Build a CRUD REST service with Spring Boot and a database"),
    "REST API": ("HTTP methods and status codes|Designing resource endpoints|Authentication and validation|Testing APIs with Postman", "Build and document a small REST API with CRUD endpoints"),
    "Selenium": ("Locators and WebDriver basics|Writing automated test scripts|Waits and assertions|Test reports", "Automate the login and search flow of a demo website"),
    "Unit Testing": ("Test structure and assertions|Test-driven development basics|Mocking|Coverage reports", "Write a unit-test suite for one of your projects"),
    "Communication": ("Structuring answers with the STAR method|Explaining a project in two minutes|Professional email writing|Active listening", "Record a two-minute project pitch and refine it"),
    "Teamwork": ("Roles in a team|Giving and receiving feedback|Resolving conflict|Working in sprints", "Lead one task in a team project and write a short retrospective"),
    "Leadership": ("Taking ownership|Delegation and motivation|Decision making|Mentoring peers", "Lead a small team project or student event"),
    "Presentation": ("Structuring a talk|Slide design|Handling questions|Confident delivery", "Present a project to peers and collect feedback"),
    "Problem Solving": ("Breaking problems into steps|Common problem patterns|Time and space trade-offs|Explaining your reasoning", "Solve 20 mixed problems and explain each approach aloud"),
    "System Design": ("Requirements and estimation|Databases and caching|Scaling and load balancing|Trade-offs and diagrams", "Design a URL shortener and document the architecture"),
    "ETL": ("Extract, transform, load concepts|Data cleaning pipelines|Scheduling jobs|Data quality checks", "Build a small pipeline that loads CSV data into a database"),
    "Spark": ("Spark architecture|DataFrames and SQL|Transformations and actions|Performance basics", "Process a large CSV file with PySpark"),
    "DBMS": ("Relational model and keys|Normalisation|Transactions and ACID|Indexing", "Design a normalised schema for a small application"),
    "Operating Systems": ("Processes and threads|Scheduling|Memory management|File systems", "Simulate a CPU scheduling algorithm in code"),
    "Computer Networks": ("OSI and TCP/IP models|IP addressing and routing|HTTP and DNS|Network security basics", "Write a simple client-server program using sockets"),
    "Agile": ("Agile principles|Scrum roles and events|User stories and backlogs|Sprint planning", "Plan a sprint for a small project using a Kanban board"),
    "Web Development": ("HTML and CSS foundations|JavaScript basics|Backend and databases|Deploying a site", "Build and deploy a small full-stack website"),
    "TypeScript": ("Types and interfaces|Generics|Compiling and configuration|Using TypeScript with a framework", "Convert a small JavaScript project to TypeScript"),
    "Data Science": ("Data collection and cleaning|Exploratory analysis|Modelling basics|Communicating results", "Complete an end-to-end data science mini project"),
}
FALLBACK_LEARNING = {
    "Language": ("{s} syntax and data types|Control flow and functions|Data structures and libraries in {s}|Modular or object-oriented design in {s}", "Build a small console application in {s}"),
    "Database": ("{s} fundamentals|Data modelling and queries|Indexes and performance|Connecting {s} to an application", "Design and query a small {s} database"),
    "Data & Analytics": ("{s} fundamentals|Working with a real dataset|Core techniques and best practices|Reporting your findings", "Analyse a public dataset using {s} and write up the insights"),
    "ML / AI": ("Core concepts behind {s}|Hands-on practice with {s}|Evaluating results|Applying {s} to a real dataset", "Train and evaluate a small model using {s}"),
    "Web": ("{s} fundamentals|Building components or endpoints|Connecting to data|Deploying a small app", "Build and publish a small web project with {s}"),
    "Core CS": ("{s} fundamentals|Common patterns and problems|Practice problems|Applying {s} in a project", "Solve 20 practice problems on {s} and explain the solutions"),
    "Tools": ("{s} basics and setup|Everyday commands and workflows|Using {s} in a project|Troubleshooting and best practices", "Use {s} throughout a small project"),
    "Cloud / DevOps": ("{s} fundamentals|Core services or concepts|Hands-on lab|Deploying a small application", "Deploy a small application using {s}"),
    "Testing": ("{s} fundamentals|Writing test cases|Automating tests|Reporting defects", "Write a test suite for a small application using {s}"),
    "Soft Skill": ("What {s} means at work|Practice exercises for {s}|Examples from your own projects|Presenting your {s} in interviews", "Prepare two STAR-format examples that show {s}"),
    "Other": ("{s} fundamentals|Key concepts and terminology|Hands-on practice|Applying {s} in a small project", "Complete a small project that demonstrates {s}"),
}

# Role knowledge base for "Suggested Career Roles" (definitions only; results are computed from the resume).
ROLE_SKILLS = {
    "Data Analyst": ["SQL", "Excel", "Python", "Power BI", "Tableau", "Statistics", "Data Visualization", "Pandas"],
    "Data Scientist": ["Python", "Machine Learning", "Statistics", "Pandas", "NumPy", "Scikit-learn", "SQL", "Data Visualization"],
    "Machine Learning Engineer": ["Python", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn", "Docker", "Git"],
    "Python Developer": ["Python", "Django", "Flask", "REST API", "SQL", "Git", "OOP"],
    "Java Developer": ["Java", "Spring Boot", "REST API", "SQL", "Git", "OOP", "Data Structures"],
    "Full-Stack / Web Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "Git", "REST API"],
    "Software Engineer": ["Data Structures", "Algorithms", "OOP", "Git", "SQL", "Problem Solving"],
    "Cloud / DevOps Engineer": ["Linux", "Docker", "Kubernetes", "AWS", "CI/CD", "Git", "Python"],
    "Business Analyst": ["SQL", "Excel", "Power BI", "Communication", "Data Analysis", "Statistics"],
    "QA / Test Engineer": ["Selenium", "Unit Testing", "SQL", "Git", "Java", "Python"],
}


def strip_urls(text: str) -> str:
    return re.sub(r"https?://\S+|[\w.+-]+@[\w-]+\.[\w.]+|\b(?:www\.)?[\w-]+\.(?:com|in|io|org|net|edu)(?:/\S*)?", " ", text)


def detect_skills(text: str) -> list[str]:
    """Canonical skills found in the text, in order of first appearance."""
    t = strip_urls(text)
    hits = sorted((m.start(), c) for c, p in SKILL_PATTERNS.items() if (m := p.search(t)))
    return [c for _, c in hits]


def canonicalize(term: str) -> str:
    """Map a user-typed skill to the canonical name when it is unambiguous; otherwise keep it as typed."""
    t = re.sub(r"\s+", " ", term.strip(" \t-*•.,;"))
    hits = detect_skills(t)
    return hits[0] if len(hits) == 1 and len(t.split()) <= 4 else t


def parse_skill_lines(text: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[\n,;]+", text or ""):
        part = re.sub(r"^[\s•*\-–—]+", "", part).strip()
        if part:
            c = canonicalize(part)
            if c.lower() not in {x.lower() for x in out}:
                out.append(c)
    return out


def skill_category(skill: str) -> str:
    return SKILL_CATEGORY.get(skill, "Other")


def learning_plan(skill: str) -> dict:
    topics, project = LEARNING.get(skill) or FALLBACK_LEARNING[skill_category(skill)]
    fmt = (lambda s: s) if skill in LEARNING else (lambda s: s.replace("{s}", skill))
    return {"topics": [fmt(t) for t in topics.split("|")], "project": fmt(project), "generic": skill not in LEARNING}


def term_in_text(term: str, text: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I))


def find_evidence(text: str, skill: str) -> str:
    pat = SKILL_PATTERNS.get(skill)
    for line in text.splitlines():
        clean = strip_urls(line)
        if (pat.search(clean) if pat else term_in_text(skill, clean)):
            line = re.sub(r"^[\s•*\-–—▪●]+", "", line).strip()
            return line[:110] + ("..." if len(line) > 110 else "")
    return ""


def skill_regex(skill: str) -> re.Pattern:
    """Pattern for a skill: the database pattern if known, otherwise a whole-word search for the typed term."""
    return SKILL_PATTERNS.get(skill) or re.compile(r"(?<![A-Za-z0-9])" + re.escape(skill) + r"(?![A-Za-z0-9])", re.I)


def mentions(skill: str, text: str) -> bool:
    return bool(skill_regex(skill).search(strip_urls(text)))


WHY_BY_CATEGORY = {
    "Language": "Programming languages are the base skill employers test first; interviews and coding rounds depend on them.",
    "Database": "Almost every software or data job reads and writes data, so database skills are checked in interviews.",
    "Data & Analytics": "Analysing and presenting data is a core daily task in data-related roles.",
    "ML / AI": "Machine-learning knowledge shows you can build models, not only use them.",
    "Web": "Web skills let you build and ship applications that other people can use.",
    "Core CS": "Computer-science fundamentals are tested in almost every technical interview.",
    "Tools": "Everyday engineering tools are assumed knowledge in a team; missing them slows you down.",
    "Cloud / DevOps": "Teams deploy and run software in the cloud, so basic cloud and deployment skills are valued.",
    "Testing": "Testing skills show you can check that software really works.",
    "Soft Skill": "Employers look for people who can work with a team and explain their ideas clearly.",
    "Other": "It appears in the requirement you provided, so the employer expects it.",
}
PRACTICE_BY_CATEGORY = {
    "Language": "Solve 10 small problems in {s} and keep the code in a GitHub repository.",
    "Database": "Write 10 queries or operations in {s} on a sample dataset.",
    "Data & Analytics": "Complete one small exercise with {s} on a public dataset.",
    "ML / AI": "Re-create one tutorial example with {s} and explain each step in your own words.",
    "Web": "Build one small page or endpoint with {s} every two days.",
    "Core CS": "Solve 10 practice problems on {s} and explain each solution aloud.",
    "Tools": "Use {s} daily for one week in a small project.",
    "Cloud / DevOps": "Follow one hands-on lab for {s} and write down the steps you used.",
    "Testing": "Write 10 test cases using {s} for a small program.",
    "Soft Skill": "Practise one STAR-format example for {s} and say it aloud.",
    "Other": "Do one small hands-on exercise with {s} every day for a week.",
}
PRACTICE_OVERRIDE = {
    "SQL": "Solve 15 SQL practice problems: joins, GROUP BY, subqueries and window functions.",
    "Git": "Create a repository, make 10 commits on two branches, then merge them and resolve one conflict.",
    "GitHub": "Push a project to GitHub with a README and open one pull request.",
    "AWS": "Complete the AWS free-tier lab: launch an EC2 instance and store a file in S3.",
    "Data Structures": "Solve 15 problems covering arrays, linked lists, stacks, queues, trees and hash maps.",
    "Algorithms": "Solve 15 problems on sorting, searching, recursion and dynamic programming.",
    "Python": "Solve 15 beginner-to-medium Python problems and write unit tests for three of them.",
    "Power BI": "Recreate a sample sales dashboard in Power BI with three visuals and one slicer.",
    "Excel": "Build a pivot table and chart from a sample dataset, then add two lookup formulas.",
    "Statistics": "Calculate mean, variance and a hypothesis test by hand and then in Python.",
    "Docker": "Write a Dockerfile for a small app, build the image and run the container.",
    "Spring Boot": "Create a Spring Boot project and add three REST endpoints.",
}


def skill_why(skill: str, level: str, role: str) -> str:
    kind = "a required skill" if level == "Required" else "a preferred (bonus) skill"
    return f"{skill} is {kind} in the {role} requirement. " + WHY_BY_CATEGORY[skill_category(skill)]


def skill_practice(skill: str) -> str:
    return PRACTICE_OVERRIDE.get(skill) or PRACTICE_BY_CATEGORY[skill_category(skill)].replace("{s}", skill)
