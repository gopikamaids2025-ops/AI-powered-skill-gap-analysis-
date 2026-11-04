import pandas as pd
import joblib


# ==========================================
# 1. Load Saved Model and Scaler
# ==========================================

model = joblib.load("models/placement_model.pkl")
scaler = joblib.load("models/scaler.pkl")


# ==========================================
# 2. Student Input
# ==========================================

student = {
    "CGPA": 8.5,
    "Attendance": 90,
    "Aptitude_Score": 80,
    "Coding_Score": 85,
    "DSA_Score": 75,
    "SQL_Score": 80,
    "Python_Score": 85,
    "Communication": 80,
    "Soft_Skills": 85,
    "Projects": 3,
    "Internships": 2,
    "Certifications": 3,
    "Resume_Score": 85,
    "Mock_Interview": 80,
    "Hackathon": 1,
    "GitHub_Score": 80,
    "LeetCode_Solved": 100
}


# ==========================================
# 3. Convert Input into DataFrame
# ==========================================

input_data = pd.DataFrame([student])


# ==========================================
# 4. Scale Input
# ==========================================

input_scaled = scaler.transform(input_data)


# ==========================================
# 5. Make Prediction
# ==========================================

prediction = model.predict(input_scaled)


# ==========================================
# 6. Display Result
# ==========================================

print("\n========================================")
print("PLACEMENT READINESS PREDICTION")
print("========================================")

if prediction[0] == 1:
    print("Result: PLACEMENT READY")
else:
    print("Result: NOT PLACEMENT READY")