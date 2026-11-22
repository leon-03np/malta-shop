
import os
import json
import time
import logging
import sqlite3
import threading

import pika
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("notification-service")

notification = FastAPI()

AMQP_URL = os.getenv(
    "AMQP_URL",
    "amqp://guest:guest@rabbitmq:5672/%2F"
)
QUEUE_NAME = "order_events"
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    "notifications.db"
)

consumer_thread = None
stop_event = threading.Event()


def database_connection():
    return sqlite3.connect(DATABASE_PATH)


def create_table():
    conn = database_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            correlation_id TEXT
        )
    """)
    conn.commit()
    conn.close()


create_table()


def save_notification(order_id, message, correlation_id):
    conn = database_connection()
    conn.execute(
        """
        INSERT INTO notifications
        (order_id, message, correlation_id)
        VALUES (?, ?, ?)
        """,
        (order_id, message, correlation_id)
    )
    conn.commit()
    conn.close()


def consume_events():
    while not stop_event.is_set():
        connection = None

        try:
            parameters = pika.URLParameters(AMQP_URL)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()

            channel.queue_declare(
                queue=QUEUE_NAME,
                durable=True
            )

            channel.basic_qos(prefetch_count=1)

            def process_event(ch, method, properties, body):
                correlation_id = (
                    properties.correlation_id
                    if properties and properties.correlation_id
                    else "missing-correlation-id"
                )

                try:
                    event = json.loads(body.decode("utf-8"))

                    if event.get("event_type") != "OrderPlaced":
                        raise ValueError("Unsupported event type")

                    order_id = event["order_id"]
                    order_name = event["order_name"]

                    message = (
                        f"Your order {order_name} "
                        "has been received successfully!"
                    )

                    save_notification(
                        order_id,
                        message,
                        correlation_id
                    )

                    logger.info(
                        "Consumed OrderPlaced event order_id=%s "
                        "correlation_id=%s",
                        order_id,
                        correlation_id
                    )

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception:
                    logger.exception(
                        "Event processing failed correlation_id=%s",
                        correlation_id
                    )
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=False
                    )

            channel.basic_consume(
                queue=QUEUE_NAME,
                on_message_callback=process_event
            )

            logger.info("RabbitMQ consumer started")
            channel.start_consuming()

        except Exception:
            logger.exception(
                "RabbitMQ connection failed; retrying in 5 seconds"
            )
            time.sleep(5)

        finally:
            if connection and connection.is_open:
                connection.close()


@notification.on_event("startup")
def start_consumer():
    global consumer_thread

    stop_event.clear()
    consumer_thread = threading.Thread(
        target=consume_events,
        daemon=True
    )
    consumer_thread.start()


@notification.on_event("shutdown")
def stop_consumer():
    stop_event.set()


@notification.get("/")
def home():
    return {
        "message": "Malta Shop Notification Service is running!"
    }


@notification.get("/notifications")
def get_notifications():
    conn = database_connection()
    rows = conn.execute(
        """
        SELECT notification_id, order_id, message, correlation_id
        FROM notifications
        ORDER BY notification_id DESC
        """
    ).fetchall()
    conn.close()

    return [
        {
            "notification_id": row[0],
            "order_id": row[1],
            "message": row[2],
            "correlation_id": row[3]
        }
        for row in rows
    ]


@notification.get("/notifications/{notification_id}")
def get_notification(notification_id: int):
    conn = database_connection()
    row = conn.execute(
        """
        SELECT notification_id, order_id, message, correlation_id
        FROM notifications
        WHERE notification_id = ?
        """,
        (notification_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return {"message": "Notification not found"}

    return {
        "notification_id": row[0],
        "order_id": row[1],
        "message": row[2],
        "correlation_id": row[3]
    }


@notification.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int):
    conn = database_connection()
    cursor = conn.execute(
        "DELETE FROM notifications WHERE notification_id = ?",
        (notification_id,)
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        return {"message": "Notification not found"}

    return {
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }
