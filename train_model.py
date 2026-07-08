import pandas as pd
import numpy as np
from xgboost import XGBRegressor
import pickle

# ✅ Load the dataset
data = pd.read_csv('insurance.csv')

# ✅ Encode categorical variables
data['sex'] = data['sex'].map({'male': 0, 'female': 1})
data['smoker'] = data['smoker'].map({'yes': 1, 'no': 0})
data['region'] = data['region'].map({'southeast': 0, 'southwest': 1, 'northeast': 2, 'northwest': 3})

# ✅ Define features and target
X = data[['age', 'sex', 'bmi', 'children', 'smoker', 'region']]  # 6 features
y = data['charges']

# ✅ Initialize and train XGBoost Regressor
model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=5,
    subsample=0.9,
    colsample_bytree=0.9,
    objective='reg:squarederror',
    random_state=42
)
model.fit(X, y)

# ✅ Save the model
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ XGBoost model trained and saved as model.pkl.")