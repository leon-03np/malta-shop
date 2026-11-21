
# Malta Shop - Microservices Project

## Project Description
Malta Shop is a simple microservices-based application
developed using Python, FastAPI, and SQLite.

The project contains two independent services:

1. Order Service
2. Notification Service

## Technologies Used
- Python
- FastAPI
- SQLite
- Pydantic
- Requests
- Uvicorn

## Project Structure

Malta-Shop/
- order_service/
  - main.py
- notification_service/
  - main.py
- README.md
- requirements.txt

## Order Service

Port: 8000

Endpoints:
- GET /
- GET /status
- POST /order
- GET /orders
- GET /orders/{order_id}
- DELETE /orders/{order_id}

## Notification Service

Port: 8001

Endpoints:
- GET /
- GET /status
- POST /notify
- GET /notifications
- GET /notifications/{notification_id}
- DELETE /notifications/{notification_id}

## Installation

Install dependencies:

pip install fastapi uvicorn requests

## Run Order Service

cd order_service

uvicorn main:order --reload --port 8000

## Run Notification Service

cd notification_service

uvicorn main:notification --reload --port 8001

## Swagger Documentation

Order Service:
http://127.0.0.1:8000/docs

Notification Service:
http://127.0.0.1:8001/docs

## Database

Order Service uses orders.db.

Notification Service uses notifications.db.

## Service Communication

When a new order is created, Order Service sends
an HTTP POST request to Notification Service.

Notification Service stores the notification
in its SQLite database.
