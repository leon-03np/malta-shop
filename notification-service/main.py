
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3

notification = FastAPI()


# Notification data model
class NotificationData(BaseModel):
    order_id: int
    message: str


# Database connection
def database_connection():
    conn = sqlite3.connect("notifications.db")
    return conn


# Create notification table
def create_table():
    conn = database_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            message TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


create_table()


# Save notification in database
def save_notification(notification_data):
    conn = database_connection()

    conn.execute("""
        INSERT INTO notifications (order_id, message)
        VALUES (?, ?)
    """, (
        notification_data.order_id,
        notification_data.message
    ))

    conn.commit()
    conn.close()


# Get all notifications
def get_all_notifications():
    conn = database_connection()

    rows = conn.execute("""
        SELECT notification_id, order_id, message
        FROM notifications
    """).fetchall()

    conn.close()

    return [
        {
            "notification_id": row[0],
            "order_id": row[1],
            "message": row[2]
        }
        for row in rows
    ]


# Get notification by ID
def get_notification_by_id(notification_id):
    conn = database_connection()

    row = conn.execute("""
        SELECT notification_id, order_id, message
        FROM notifications
        WHERE notification_id = ?
    """, (notification_id,)).fetchone()

    conn.close()

    return row


# Home endpoint
@notification.get("/")
def home():
    return {
        "message": "Malta Shop Notification Service is running!"
    }


# Health check endpoint
@notification.get("/status")
def service_status():
    return {
        "status": "healthy"
    }


# Create notification endpoint
@notification.post("/notify")
def send_notification(notification_data: NotificationData):

    save_notification(notification_data)

    return {
        "message": "Notification created successfully!",
        "order_id": notification_data.order_id,
        "notification": notification_data.message
    }


# Get all notifications endpoint
@notification.get("/notifications")
def get_notifications():
    return get_all_notifications()


# Get notification by ID endpoint
@notification.get("/notifications/{notification_id}")
def get_notification(notification_id: int):

    row = get_notification_by_id(notification_id)

    if row is None:
        return {
            "message": "Notification not found"
        }

    return {
        "notification_id": row[0],
        "order_id": row[1],
        "message": row[2]
    }


# Delete notification endpoint
@notification.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int):

    conn = database_connection()

    cursor = conn.execute("""
        DELETE FROM notifications
        WHERE notification_id = ?
    """, (notification_id,))

    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return {
            "message": "Notification not found"
        }

    return {
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }
