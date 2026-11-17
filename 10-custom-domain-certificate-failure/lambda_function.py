import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info("LAB10_ORDER_REQUEST")

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

    logger.info("LAB10_ORDER_SUCCESS")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "orders": orders
        })
    }
