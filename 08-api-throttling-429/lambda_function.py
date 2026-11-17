import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORDERS = [
    {"order_id": "1001", "status": "processing"},
    {"order_id": "1002", "status": "shipped"}
]


def lambda_handler(event, context):

    logger.info(
        "LAB08_REQUEST method=%s path=%s",
        event.get("httpMethod"),
        event.get("path")
    )

    logger.info(
        "LAB08_ORDER_SUCCESS count=%s",
        len(ORDERS)
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store"
        },
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "orders": ORDERS
        })
    }
