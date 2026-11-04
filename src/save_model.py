import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression


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
# 3. Convert Hackathon
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


# ==========================================
# 6. Feature Scaling
# ==========================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)


# ==========================================
# 7. Train Logistic Regression
# ==========================================

model = LogisticRegression(
    max_iter=1000
)

model.fit(X_train_scaled, y_train)


# ==========================================
# 8. Save Model
# ==========================================

joblib.dump(
    model,
    "models/placement_model.pkl"
)

joblib.dump(
    scaler,
    "models/scaler.pkl"
)


print("\n========================================")
print("MODEL SAVED SUCCESSFULLY")
print("========================================")

print("Model: Logistic Regression")
print("Saved: models/placement_model.pkl")
print("Saved: models/scaler.pkl")