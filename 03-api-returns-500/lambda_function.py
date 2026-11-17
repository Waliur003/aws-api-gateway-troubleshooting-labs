import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORDERS = [
    {
        "order_id": "1001",
        "customer": "Test Customer",
        "status": "processing"
    },
    {
        "order_id": "1002",
        "customer": "Example Customer",
        "status": "shipped"
    }
]


def make_response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store"
        },
        "isBase64Encoded": False,
        "body": json.dumps(payload)
    }


def load_orders():
    backend_mode = os.environ.get(
        "ORDER_BACKEND_MODE",
        "unavailable"
    )

    if backend_mode != "healthy":
        raise RuntimeError(
            "Order backend is unavailable: "
            f"mode={backend_mode}"
        )

    return ORDERS


def lambda_handler(event, context):
    logger.info(
        "LAB03_REQUEST method=%s path=%s",
        event.get("httpMethod"),
        event.get("path")
    )

    try:
        orders = load_orders()

        logger.info(
            "LAB03_ORDER_SUCCESS count=%s",
            len(orders)
        )

        return make_response(200, {
            "message": "Orders retrieved successfully",
            "orders": orders
        })

    except Exception:
        logger.exception(
            "LAB03_BACKEND_ERROR: order processing failed"
        )

        return make_response(500, {
            "message": "Internal server error",
            "error_code": "ORDER_SERVICE_FAILURE"
        })
