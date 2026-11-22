
import os
import json
import uuid
import time
import logging
import sqlite3

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("order-service")

order = FastAPI()

AMQP_URL = os.getenv(
    "AMQP_URL",
    "amqp://guest:guest@rabbitmq:5672/%2F"
)
QUEUE_NAME = "order_events"
DATABASE_PATH = os.getenv("DATABASE_PATH", "orders.db")


class Order(BaseModel):
    order_id: int
    order_name: str
    quantity: int


def database_connection():
    return sqlite3.connect(DATABASE_PATH)


def create_table():
    conn = database_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            order_name TEXT NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


create_table()


def save_order(order_data):
    conn = database_connection()
    conn.execute(
        """
        INSERT INTO orders(order_id, order_name, quantity)
        VALUES (?, ?, ?)
        """,
        (
            order_data.order_id,
            order_data.order_name,
            order_data.quantity
        )
    )
    conn.commit()
    conn.close()


def publish_order_event(event, correlation_id):
    parameters = pika.URLParameters(AMQP_URL)

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True
    )

    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
            correlation_id=correlation_id
        )
    )

    connection.close()

    logger.info(
        "Published OrderPlaced event order_id=%s correlation_id=%s",
        event["order_id"],
        correlation_id
    )


@order.get("/")
def get_order():
    return {
        "message": "Malta shop is running smoothly"
    }


@order.get("/status")
def service_status():
    return {"status": "healthy"}


@order.post("/order")
def create_order(order_data: Order):
    correlation_id = str(uuid.uuid4())

    try:
        save_order(order_data)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Order ID already exists"
        )

    event = {
        "event_type": "OrderPlaced",
        "order_id": order_data.order_id,
        "order_name": order_data.order_name,
        "quantity": order_data.quantity
    }

    try:
        publish_order_event(event, correlation_id)
    except Exception as error:
        logger.exception(
            "Failed to publish order event correlation_id=%s",
            correlation_id
        )
        raise HTTPException(
            status_code=503,
            detail="Order saved but event publishing failed. "
                   "Please contact support. "
                   f"Correlation ID: {correlation_id}"
        )

    return {
        "message": "Order created and event published successfully",
        "order_id": order_data.order_id,
        "order_name": order_data.order_name,
        "quantity": order_data.quantity,
        "event": "OrderPlaced",
        "correlation_id": correlation_id
    }


@order.get("/orders")
def get_orders():
    conn = database_connection()
    rows = conn.execute(
        "SELECT order_id, order_name, quantity FROM orders"
    ).fetchall()
    conn.close()

    return [
        {
            "order_id": row[0],
            "order_name": row[1],
            "quantity": row[2]
        }
        for row in rows
    ]


@order.get("/orders/{order_id}")
def get_order_by_id(order_id: int):
    conn = database_connection()
    row = conn.execute(
        """
        SELECT order_id, order_name, quantity
        FROM orders WHERE order_id = ?
        """,
        (order_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "order_id": row[0],
        "order_name": row[1],
        "quantity": row[2]
    }


@order.delete("/orders/{order_id}")
def delete_order(order_id: int):
    conn = database_connection()
    cursor = conn.execute(
        "DELETE FROM orders WHERE order_id = ?",
        (order_id,)
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if deleted == 0:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return {
        "message": "Order deleted successfully",
        "order_id": order_id
    }
