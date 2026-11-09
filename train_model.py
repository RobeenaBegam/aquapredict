import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

data = pd.read_csv("training_data.csv")
filling = data[data["minutes_left"] < 999]
print("Rows used for training:", len(filling))

features = ["capacity", "level", "fill_speed", "motor_on", "hour"]
X = filling[features]
y = filling["minutes_left"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestRegressor(
    n_estimators=200, max_depth=14, min_samples_leaf=3, random_state=42
)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
print("MAE (minutes):", round(mean_absolute_error(y_test, predictions), 2))
print("R2 score:", round(r2_score(y_test, predictions), 4))

joblib.dump(model, "model.pkl")
print("Model saved as model.pkl")