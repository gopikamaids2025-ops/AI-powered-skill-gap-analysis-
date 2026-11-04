import pandas as pd
from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_excel(
    "dataset/AI_Powered_Skill_Gap_Placement_Dataset_1000.xlsx"
)

# Remove Student_ID because it is only an identifier
df = df.drop("Student_ID", axis=1)

# Separate input features (X) and target (y)
X = df.drop("Placement_Ready", axis=1)
y = df["Placement_Ready"]

# Split dataset into training and testing data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("Total records:", len(df))
print("Training records:", len(X_train))
print("Testing records:", len(X_test))

print("\nInput features:")
print(X.columns.tolist())

print("\nTarget:")
print(y.name)

print("\nTarget distribution:")
print(y.value_counts())