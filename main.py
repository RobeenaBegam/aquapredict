import hashlib
import os
import sqlite3
from datetime import datetime

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from database import get_connection, create_tables

app = FastAPI(title="AquaPredict")
create_tables()
model = joblib.load("model.pkl")


def make_hash(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()
    return salt + "$" + digest


class RegisterBody(BaseModel):
    name: str
    email: str
    password: str


class LoginBody(BaseModel):
    email: str
    password: str


class TankBody(BaseModel):
    user_id: int
    name: str
    capacity: float


class ReadingBody(BaseModel):
    tank_id: int
    level: float


@app.post("/auth/register")
def register(body: RegisterBody):
    conn = get_connection()
    try:
        password_hash = make_hash(body.password)
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (body.name, body.email, password_hash),
        )
        conn.commit()
        return {"message": "User registered", "user_id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        conn.close()


@app.post("/auth/login")
def login(body: LoginBody):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?", (body.email,)
    ).fetchone()
    conn.close()
    if user is None:
        raise HTTPException(status_code=401, detail="Wrong email or password")
    salt = user["password_hash"].split("$")[0]
    if make_hash(body.password, salt) != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return {
        "message": "Login successful",
        "user_id": user["id"],
        "name": user["name"],
    }


@app.post("/tanks")
def add_tank(body: TankBody):
    if body.capacity <= 0:
        raise HTTPException(status_code=400, detail="Capacity must be above 0")
    conn = get_connection()
    user = conn.execute(
        "SELECT id FROM users WHERE id = ?", (body.user_id,)
    ).fetchone()
    if user is None:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    cursor = conn.execute(
        "INSERT INTO tanks (user_id, name, capacity) VALUES (?, ?, ?)",
        (body.user_id, body.name, body.capacity),
    )
    conn.commit()
    tank_id = cursor.lastrowid
    conn.close()
    return {"message": "Tank added", "tank_id": tank_id}


@app.post("/readings")
def add_reading(body: ReadingBody):
    conn = get_connection()
    tank = conn.execute(
        "SELECT * FROM tanks WHERE id = ?", (body.tank_id,)
    ).fetchone()
    if tank is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Tank not found")

    capacity = tank["capacity"]
    if body.level < 0 or body.level > capacity:
        conn.close()
        raise HTTPException(
            status_code=400, detail="Level must be between 0 and capacity"
        )

    previous = conn.execute(
        "SELECT level FROM readings WHERE tank_id = ? ORDER BY id DESC LIMIT 1",
        (body.tank_id,),
    ).fetchone()
    if previous is None:
        fill_speed = 0
    else:
        fill_speed = body.level - previous["level"]

    motor_on = 1 if fill_speed > 1 else 0
    minutes_left = None

    if body.level >= 0.99 * capacity:
        status = "Full"
    elif motor_on == 0:
        status = "Idle"
    else:
        now = datetime.now()
        inputs = pd.DataFrame(
            [
                {
                    "capacity": capacity,
                    "level": body.level,
                    "fill_speed": fill_speed,
                    "motor_on": motor_on,
                    "hour": now.hour,
                }
            ]
        )
        minutes_left = round(float(model.predict(inputs)[0]), 1)
        if minutes_left <= 2:
            status = "Critical"
        elif minutes_left <= 5:
            status = "Warning"
        else:
            status = "Normal"

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO readings (tank_id, level, fill_speed, motor_on, "
        "minutes_left, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            body.tank_id,
            body.level,
            fill_speed,
            motor_on,
            minutes_left,
            status,
            created_at,
        ),
    )
    reading_id = cursor.lastrowid

    ring = 0
    if status == "Warning":
        message = "Tank will be full in about " + str(minutes_left) + " minutes"
        conn.execute(
            "INSERT INTO notifications (tank_id, message, status, ring, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (body.tank_id, message, status, 0, created_at),
        )
    elif status == "Critical":
        ring = 1
        message = "Switch off the motor now. Tank will be full in about " + str(
            minutes_left
        ) + " minutes"
        conn.execute(
            "INSERT INTO notifications (tank_id, message, status, ring, "
            "created_at) VALUES (?, ?, ?, ?, ?)",
            (body.tank_id, message, status, 1, created_at),
        )

    conn.commit()
    conn.close()
    return {
        "reading_id": reading_id,
        "level": body.level,
        "fill_speed": fill_speed,
        "motor_on": motor_on,
        "minutes_left": minutes_left,
        "status": status,
        "ring": ring,
    }


@app.get("/history")
def get_history(tank_id: int):
    conn = get_connection()
    tank = conn.execute(
        "SELECT id FROM tanks WHERE id = ?", (tank_id,)
    ).fetchone()
    if tank is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Tank not found")
    rows = conn.execute(
        "SELECT * FROM readings WHERE tank_id = ? ORDER BY id DESC",
        (tank_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/notifications")
def get_notifications(tank_id: int):
    conn = get_connection()
    tank = conn.execute(
        "SELECT id FROM tanks WHERE id = ?", (tank_id,)
    ).fetchone()
    if tank is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Tank not found")
    rows = conn.execute(
        "SELECT * FROM notifications WHERE tank_id = ? ORDER BY id DESC",
        (tank_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]