"""
train_gradient_boosting_windowed.py

Same model type as before (Gradient Boosting), but now trained on the
windowed/trend features from build_windowed_dataset.py, predicting
congestion HORIZON steps into the future instead of right now.

Run build_windowed_dataset.py first.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

DATA_FILE = os.path.expanduser("~/sdn_ai_project/data/windowed_network_data.csv")
MODEL_OUT = os.path.expanduser("~/sdn_ai_project/gradient_boosting_windowed_model.pkl")

data = pd.read_csv(DATA_FILE)

feature_cols = [c for c in data.columns if c != "label_future_congestion"]
X = data[feature_cols]
y = data["label_future_congestion"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y if y.nunique() > 1 else None
)

model = GradientBoostingClassifier(random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print("\nWindowed Gradient Boosting Forecasting Model")
print("---------------------------------------------")
print(f"Dataset samples: {len(data)}")
print(f"Feature count: {len(feature_cols)}")
print(f"Training samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")
print(f"Accuracy: {accuracy * 100:.2f}%")

print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# feature importance -- useful for your paper/demo to show the model
# actually learned trend signals (slope features), not just raw values
importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
print("\nTop 10 most important features:")
print(importances.head(10))

joblib.dump(model, MODEL_OUT)
# also save the feature column order -- the live controller MUST build
# its feature vector in this exact order
joblib.dump(feature_cols, os.path.expanduser("~/sdn_ai_project/windowed_feature_columns.pkl"))

print(f"\nModel saved to: {MODEL_OUT}")
print(f"Feature column order saved to: windowed_feature_columns.pkl")
