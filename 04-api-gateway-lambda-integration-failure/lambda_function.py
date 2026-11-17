import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    method = event.get("httpMethod", "unknown")
    path = event.get("path", "unknown")

    logger.info(
        "LAB04_BACKEND_INVOKED method=%s path=%s",
        method,
        path
    )

    orders = [
        {
            "order_id": "1001",
            "status": "processing"
        },
        {
            "order_id": "1002",
            "status": "shipped"
        }
    ]

    logger.info(
        "LAB04_ORDER_SUCCESS count=%s",
        len(orders)
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store"
        },
        "isBase64Encoded": False,
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "orders": orders
        })
    }
