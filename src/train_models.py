import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


# ==========================================
# 1. Load Dataset
# ==========================================

df = pd.read_excel(
    "dataset/AI_Powered_Skill_Gap_Placement_Dataset_1000.xlsx"
)

print("Dataset loaded successfully!")


# ==========================================
# 2. Remove Student ID
# ==========================================

df = df.drop("Student_ID", axis=1)


# ==========================================
# 3. Convert Hackathon Yes/No to 1/0
# ==========================================

df["Hackathon"] = df["Hackathon"].map({
    "Yes": 1,
    "No": 0
})


# ==========================================
# 4. Separate Features and Target
# ==========================================

X = df.drop("Placement_Ready", axis=1)

y = df["Placement_Ready"].map({
    "Yes": 1,
    "No": 0
})


# ==========================================
# 5. Train-Test Split
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# ==========================================
# 6. Feature Scaling
# ==========================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)


# ==========================================
# 7. Create Models
# ==========================================

models = {

    "Logistic Regression": LogisticRegression(
        max_iter=1000
    ),

    "KNN": KNeighborsClassifier(),

    "SVM": SVC(),

    "Decision Tree": DecisionTreeClassifier(
        random_state=42
    ),

    "Random Forest": RandomForestClassifier(
        random_state=42
    )
}


# ==========================================
# 8. Train and Evaluate Models
# ==========================================

results = []

for name, model in models.items():

    # Scaling for Logistic Regression, KNN and SVM
    if name in ["Logistic Regression", "KNN", "SVM"]:
        model.fit(X_train_scaled, y_train)
        predictions = model.predict(X_test_scaled)

    # No scaling required for Tree models
    else:
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)


    accuracy = accuracy_score(y_test, predictions)

    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )


    results.append({
        "Model": name,
        "Accuracy": accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1 Score": f1
    })


# ==========================================
# 9. Display Results
# ==========================================

results_df = pd.DataFrame(results)

print("\n========================================")
print("MODEL COMPARISON")
print("========================================")

print(results_df.to_string(index=False))