import json
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    start = time.monotonic()

    delay = float(
        os.environ.get("DELAY_SECONDS", "0")
    )

    logger.info(
        "LAB09_REQUEST_STARTED delay=%s",
        delay
    )

    if delay > 0:
        time.sleep(delay)

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

    duration_ms = round(
        (time.monotonic() - start) * 1000,
        2
    )

    logger.info(
        "LAB09_REQUEST_COMPLETED duration_ms=%s",
        duration_ms
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "processing_time_ms": duration_ms,
            "orders": orders
        })
    }
