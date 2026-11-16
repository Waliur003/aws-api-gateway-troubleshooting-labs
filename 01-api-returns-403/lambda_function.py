import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("LAB01_BACKEND_INVOKED")

    method = event.get("httpMethod", "unknown")
    path = event.get("path", "unknown")

    logger.info(
        "Request method=%s path=%s",
        method,
        path
    )

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Orders API working",
            "status": "success",
            "method": method,
            "path": path
        })
    }
