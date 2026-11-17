import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALLOWED_ORIGIN = "http://localhost:8000"

def lambda_handler(event, context):

    method = event.get("httpMethod")

    cors_headers = {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Lab-Client",
        "Vary": "Origin"
    }

    if method == "OPTIONS":
        logger.info("LAB05_PREFLIGHT_SUCCESS")

        return {
            "statusCode": 204,
            "headers": cors_headers,
            "body": ""
        }

    logger.info("LAB05_ORDER_SUCCESS")

    orders = [
        {"order_id": "1001", "status": "processing"},
        {"order_id": "1002", "status": "shipped"}
    ]

    return {
        "statusCode": 200,
        "headers": {
            **cors_headers,
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "orders": orders
        })
    }
