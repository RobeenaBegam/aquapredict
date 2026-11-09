# AquaPredict

An AI-based water tank monitoring backend. A sensor sends the water level every minute, the backend works out the fill speed, a machine learning model predicts how many minutes are left until the tank is full, and an alert is created before it overflows.

This is a rebuilt version of my summer internship project (Data Science internship, Top Tech Developers, Chennai, June 2026). The original code was not saved, so I rebuilt the backend and the model from scratch with a new sensor-based design. The Flutter mobile app is not part of this rebuild yet (see Future Work).

## How it works

1. The user enters only the tank capacity, once.
2. A sensor sends the water level to the backend every minute. For now a Python script (`simulator.py`) acts as a simulated sensor.
3. The backend calculates the fill speed from the last two readings. Example: 400 L at 6:00 pm and 420 L at 6:01 pm means 20 litres per minute.
4. The model predicts the minutes left until the tank is full. Model inputs: capacity, current level, fill speed, motor on or off, and hour of day.
5. The backend sets a status. For Warning and Critical it saves an alert, and a Critical alert is marked `ring = 1` for a future call-style alarm.

Status levels:

- Full: level is at least 99% of capacity
- Idle: the motor is off (the tank is not filling)
- Critical: 2 minutes or less left
- Warning: 5 minutes or less left
- Normal: more than 5 minutes left

## Tech stack

- Python 3.14
- FastAPI and uvicorn (backend)
- SQLite (database)
- scikit-learn RandomForestRegressor, pandas, numpy, joblib (model)
- pytest and httpx (tests)

## Project files

- `generate_data.py` creates 6,000 synthetic readings and saves `training_data.csv`
- `train_model.py` trains the model and saves `model.pkl`
- `database.py` creates the four tables: users, tanks, readings, notifications
- `main.py` is the FastAPI backend
- `simulator.py` is the simulated sensor
- `test_aquapredict.py` has the tests

## API endpoints

- `POST /auth/register` creates a user
- `POST /auth/login` logs in
- `POST /tanks` adds a tank with its capacity
- `POST /readings` sends a water level and returns fill speed, minutes left, status and ring
- `GET /history?tank_id=1` returns the readings of a tank, newest first
- `GET /notifications?tank_id=1` returns the alerts of a tank, newest first

Passwords are stored as salted PBKDF2-SHA256 hashes, never as plain text.

## Results

- Trained on 6,000 synthetic readings (4,215 rows where the tank is filling), 80/20 split
- RandomForestRegressor with 200 trees, max depth 14, min 3 samples per leaf
- MAE: 0.19 minutes
- R²: 0.9973
- Tests: 14 passed (10 functional and 4 database tests)

## An honest note about the model

The training data is synthetic. It was made with a simple rule: minutes left = litres missing divided by fill speed, with values based on my home tank (about 500 litres, filled in 15 to 20 minutes). The model learns this rule from the tank's current state, so the high score is expected and does not prove accuracy on a real tank. The readings saved in the history table are not used to train the model yet.

## How to run

1. Install the packages: `python -m pip install pandas numpy scikit-learn joblib fastapi uvicorn pytest httpx`
2. Create the data: `python generate_data.py`
3. Train the model: `python train_model.py`
4. Start the backend: `python -m uvicorn main:app --reload`
5. Open `http://127.0.0.1:8000/docs` in a browser to try the endpoints
6. With the backend running, run the simulated sensor: `python simulator.py` (it uses user 1, so register a user first in the docs page)
7. Run the tests: `python -m pytest -v`

The tests use a temporary database, so they never touch `aquapredict.db`.

## Future Work

- Move from SQLite to PostgreSQL or MySQL. The SQL is almost the same, so only `database.py` needs to change.
- Real hardware: an ESP32 with a waterproof ultrasonic sensor (JSN-SR04T), fixed under the tank lid pointing straight down at the water, away from the inlet pipe. The level is the tank height minus the measured distance. It cannot read the top 20 to 25 cm below the lid, and Wi-Fi must reach the roof.
- Flutter mobile app with login, dashboard, history chart and notifications.
- Alarm-style, call-like alert in the mobile app (long ringtone, full-screen, hard to miss) using the `ring` column that is already saved.
- Train the model on real sensor readings from the history table instead of only synthetic data.
- Let other houses use it. The database already supports many users and tanks, but it needs a sensor in each house and a backend running online all the time.
- Research ideas: estimate the water level from a photo of the tank, or from a small camera inside the tank. Both are hard because of the dark tank, fogged lens and rippling water.
- Tidy the long decimals in the simulator output (a small cosmetic fix).

## Author

Robeena Begam, BE Computer Science, Anna University Regional Campus, Tirunelveli.
GitHub: RobeenaBegam