import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

EXPECTED_PREFIX = os.environ.get(
    "EXPECTED_PREFIX",
    "/orders/"
)

ORDERS = {
    "1001": {
        "order_id": "1001",
        "customer": "Test Customer",
        "status": "processing",
        "total": 149.99
    },
    "1002": {
        "order_id": "1002",
        "customer": "Example Customer",
        "status": "shipped",
        "total": 79.50
    }
}


def response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(payload)
    }


def lambda_handler(event, context):
    method = event.get("httpMethod", "unknown")
    path = event.get("path", "unknown")

    logger.info(
        "LAB02_REQUEST method=%s path=%s expected_prefix=%s",
        method,
        path,
        EXPECTED_PREFIX
    )

    # Intentional routing mismatch when the
    # environment variable is set to /order/.
    if not path.startswith(EXPECTED_PREFIX):
        logger.warning(
            "LAB02_ROUTE_NOT_FOUND path=%s expected=%s",
            path,
            EXPECTED_PREFIX
        )

        return response(404, {
            "message": "Order endpoint not found",
            "requested_path": path
        })

    path_parameters = event.get("pathParameters") or {}
    order_id = path_parameters.get("orderId")

    if not order_id:
        return response(400, {
            "message": "Order ID is required"
        })

    order = ORDERS.get(order_id)

    if not order:
        logger.warning(
            "LAB02_ORDER_NOT_FOUND order_id=%s",
            order_id
        )

        return response(404, {
            "message": "Order not found",
            "order_id": order_id
        })

    logger.info(
        "LAB02_ORDER_FOUND order_id=%s",
        order_id
    )

    return response(200, {
        "message": "Order retrieved successfully",
        "order": order
    })
