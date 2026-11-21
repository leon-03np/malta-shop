from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import requests

order = FastAPI()

class Order(BaseModel):
    order_id:int
    order_name:str
    quantity:int


@order.get("/")
def get_order():
    return{"message":"Malta shop is running smoothly......"}

@order.get("/status")
def service_status():
    return{"status":"healthy"}



@order.post("/order")
def create_order(order_data: Order):

    try:
        save_order(order_data)

    except sqlite3.IntegrityError:
        return {
            "error": "Order ID already exists"
        }

    try:
        response = requests.post(
            "http://127.0.0.1:8001/notify",
            json={
                "order_id": order_data.order_id,
                "message": f"Your order {order_data.order_name} has been received successfully!"
            },
            timeout=5
        )

        response.raise_for_status()
        notification_result = response.json()

    except requests.RequestException as error:
        notification_result = {
            "message": "Notification failed",
            "error": str(error)
        }

    return {
        "message": "Order created successfully!",
        "order_id": order_data.order_id,
        "order_name": order_data.order_name,
        "quantity": order_data.quantity,
        "notification": notification_result
    }


def database_connection():
    conn =  sqlite3.connect("orders.db")
    return conn

def create_table():
    conn = database_connection()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        order_id INTEGER PRIMARY KEY,
        order_name TEXT NOT NULL,
        quantity INTEGER NOT NULL
    )
    """)
    conn.commit()
    conn.close()
create_table()
def save_order(order):
    conn = sqlite3.connect("orders.db")
    conn.execute("""
    INSERT INTO orders(order_id, order_name, quantity)
    VALUES(?, ?, ?)
    """,
    (
        order.order_id,
        order.order_name,
        order.quantity
    )
    )
    conn.commit()
    conn.close()
def get_all_orders():
    conn = database_connection()

    rows = conn.execute("""
        SELECT order_id, order_name, quantity
        FROM orders
    """).fetchall()

    conn.close()

    return [
        {
            "order_id": row[0],
            "order_name": row[1],
            "quantity": row[2]
        }
        for row in rows
    ]
@order.get("/orders")
def get_orders():
    return get_all_orders()


@order.get("/orders/{order_id}")
def get_order_by_id(order_id: int):
    conn = database_connection()

    row = conn.execute("""
        SELECT order_id, order_name, quantity
        FROM orders
        WHERE order_id = ?
    """, (order_id,)).fetchone()

    conn.close()

    if row is None:
        return {"message": "Order not found"}

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
        return {"message": "Order not found"}

    return {
        "message": "Order deleted successfully",
        "order_id": order_id
    }
