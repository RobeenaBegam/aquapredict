import json
import random
import time
import urllib.request

BASE_URL = "http://127.0.0.1:8000"
USER_ID = 1
CAPACITY = 500
SECONDS_BETWEEN_READINGS = 2


def post(path, data):
    request = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


tank = post(
    "/tanks",
    {"user_id": USER_ID, "name": "Simulated tank", "capacity": CAPACITY},
)
tank_id = tank["tank_id"]
print("Tank created, tank_id =", tank_id)

level = 0.0
while True:
    result = post("/readings", {"tank_id": tank_id, "level": round(level, 1)})
    print(
        "Level", result["level"],
        "| speed", result["fill_speed"],
        "| minutes left", result["minutes_left"],
        "| status", result["status"],
        "| ring", result["ring"],
    )
    if result["status"] == "Full":
        print("Tank is full. Sensor stopped.")
        break
    time.sleep(SECONDS_BETWEEN_READINGS)
    level = min(level + random.uniform(25, 33), CAPACITY)