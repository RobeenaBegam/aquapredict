import numpy as np
import pandas as pd

np.random.seed(42)
N = 6000

capacity = np.random.uniform(400, 600, N)
level = np.random.uniform(0, 1, N) * capacity
motor_on = np.random.choice([0, 1], N, p=[0.3, 0.7])
hour = np.random.randint(0, 24, N)

fill_speed = np.where(
    motor_on == 1,
    np.random.uniform(25, 33, N),
    np.random.uniform(-3, 0.5, N),
)
fill_speed = fill_speed + np.random.normal(0, 0.5, N)
fill_speed = np.where(motor_on == 1, fill_speed, np.minimum(fill_speed, 0))

remaining = capacity - level
minutes_left = np.where(
    fill_speed > 1,
    remaining / np.maximum(fill_speed, 1),
    999,
)
minutes_left = np.minimum(minutes_left, 999)

data = pd.DataFrame({
    "capacity": capacity.round(1),
    "level": level.round(1),
    "fill_speed": fill_speed.round(2),
    "motor_on": motor_on,
    "hour": hour,
    "minutes_left": minutes_left.round(1),
})

data.to_csv("training_data.csv", index=False)
print("Rows made:", len(data))
print(data.head())