# Lab 03 — Amazon API Gateway Returns 500 Internal Server Error

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP **500 Internal Server Error** in an Amazon API Gateway REST API integrated with AWS Lambda.

In production, applications often use API Gateway as an entry point for backend services such as Lambda functions, databases, and internal APIs.

When API Gateway returns HTTP 500, the root cause may be an application exception, unavailable backend dependency, incorrect configuration, or an integration failure.

In this lab, we create a REST API exposing a `GET /orders` endpoint backed by a Python Lambda function.

The Lambda function simulates retrieving orders from an internal order-processing service.

We first verify that the API returns HTTP 200.

Next, we intentionally change the Lambda environment variable `ORDER_BACKEND_MODE` from `healthy` to `unavailable`.

When the API is invoked, the Lambda application raises a `RuntimeError`, catches the exception, records the failure in CloudWatch Logs, and returns a correctly formatted Lambda proxy response with `statusCode: 500`.

API Gateway forwards the application-generated HTTP 500 to the client.

We investigate the incident using AWS CLI, curl, API Gateway resources and integrations, Lambda environment variables, CloudWatch Logs, and CloudWatch metrics.

After identifying the incorrect backend configuration as the root cause, we restore the Lambda environment variable to `healthy`.

We repeat the original API request and verify HTTP 200 without modifying the application code or redeploying API Gateway.

We also examine the important difference between an application-generated HTTP 500 and an unhandled Lambda exception that typically results in HTTP 502.

Finally, we remove all temporary AWS resources.

### Troubleshooting Workflow

```text
Create IAM Execution Role
           |
           v
Create Python Lambda Backend
           |
           v
Configure Healthy Backend
           |
           v
Deploy Lambda Function
           |
           v
Create API Gateway REST API
           |
           v
Create GET /orders Method
           |
           v
Configure Lambda Proxy Integration
           |
           v
Grant Lambda Invoke Permission
           |
           v
Deploy API to dev Stage
           |
           v
Verify Healthy Baseline — HTTP 200
           |
           v
Change ORDER_BACKEND_MODE=unavailable
           |
           v
Send GET /orders Request
           |
           v
Lambda Raises RuntimeError
           |
           v
Lambda Catches Exception
           |
           v
CloudWatch Records Backend Error
           |
           v
Lambda Returns statusCode: 500
           |
           v
API Gateway Returns HTTP 500
           |
           v
Investigate API and Lambda Metrics
           |
           v
Identify Backend Configuration Failure
           |
           v
Restore ORDER_BACKEND_MODE=healthy
           |
           v
Repeat Original Request
           |
           v
Verify HTTP 200
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-003 |
| Lab Name | API Returns 500 |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab03-500-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab03-order-handler` |
| Lambda Execution Role | `api-lab03-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Healthy Configuration | `ORDER_BACKEND_MODE=healthy` |
| Broken Configuration | `ORDER_BACKEND_MODE=unavailable` |
| Application Exception | `RuntimeError` |
| Broken HTTP Response | 500 |
| Recovered HTTP Response | 200 |
| CloudWatch Metric | `5XXError` |
| CloudWatch Log Marker | `LAB03_BACKEND_ERROR` |
| Root Cause | Incorrect backend configuration |
| Remediation | Restore Lambda environment variable |
| API Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand HTTP 500 Internal Server Error.
- Configure a REST API with Lambda proxy integration.
- Reproduce a backend-generated HTTP 500.
- Understand handled and unhandled Lambda exceptions.
- Distinguish HTTP 500 from HTTP 502.
- Investigate Lambda environment variables.
- Use CloudWatch Logs to identify application failures.
- Understand structured Lambda proxy responses.
- Inspect API Gateway methods, integrations, and deployments.
- Analyze API Gateway `5XXError` metrics.
- Compare API Gateway errors with Lambda `Errors`.
- Apply targeted remediation.
- Verify recovery without unnecessary API redeployment.
- Practice production root cause analysis.
- Apply secure error-handling practices.
- Clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-processing application using Amazon API Gateway and AWS Lambda.

Its API exposes:

```http
GET /dev/orders
```

The Lambda backend retrieves order information from an internal service.

Under normal conditions, the endpoint returns HTTP 200 with order records.

During a production configuration deployment, an environment variable is incorrectly changed.

The backend mode changes from:

```text
ORDER_BACKEND_MODE=healthy
```

to:

```text
ORDER_BACKEND_MODE=unavailable
```

After this change, users begin receiving:

```http
HTTP/2 500
```

The response body contains:

```json
{
  "message": "Internal server error",
  "error_code": "ORDER_SERVICE_FAILURE"
}
```

The Cloud Engineering team investigates.

The engineer verifies that:

- The API Gateway REST API exists.
- The `/orders` resource is correctly deployed.
- The GET method exists.
- Lambda integration is configured correctly.
- API Gateway has permission to invoke Lambda.
- The Lambda function is Active.
- The request reaches Lambda.
- The application logs a backend exception.
- The Lambda environment variable has an incorrect value.

The engineer determines that the API Gateway infrastructure is healthy.

The failure originates from the backend application's environment configuration.

After restoring the environment variable, the API returns HTTP 200.

### Incident Symptoms

- API Gateway returns HTTP 500.
- The GET method and deployment are correct.
- Lambda is invoked successfully.
- CloudWatch Logs show a Python `RuntimeError`.
- The application returns a structured HTTP 500 response.
- Lambda runtime `Errors` may remain at zero.
- API Gateway `5XXError` increases.
- Restoring backend configuration resolves the incident.

### Business Impact

An unavailable order-processing service may cause:

- Failed customer requests.
- Inaccessible order information.
- Interrupted business workflows.
- Increased API error rates.
- Customer-facing application failures.
- Increased operational alerts.
- Reduced service reliability.
- Delayed order-processing operations.

### Objective

Identify the true source of the HTTP 500, correct the backend configuration, and verify that the original API request works without weakening API security or making unnecessary infrastructure changes.

---

## 3. AWS Architecture

### Healthy Baseline Architecture

```text
                  API Client
                      |
                      v
                 GET /orders
                      |
                      v
               Amazon API Gateway
                      |
                      v
               Lambda Proxy Integration
                      |
                      v
                  AWS Lambda
                      |
                      v
           ORDER_BACKEND_MODE=healthy
                      |
                      v
                 load_orders()
                      |
                      v
                Orders Retrieved
                      |
                      v
             Lambda Returns statusCode 200
                      |
                      v
                 HTTP 200 OK
```

### Broken Architecture

```text
                  API Client
                      |
                      v
                 GET /orders
                      |
                      v
               Amazon API Gateway
                      |
                      v
               Lambda Proxy Integration
                      |
                      v
                  AWS Lambda
                      |
                      v
         ORDER_BACKEND_MODE=unavailable
                      |
                      v
                 load_orders()
                      |
                      v
                  RuntimeError
                      |
                      v
              Exception Handler
                      |
             +--------+--------+
             |                 |
             v                 v
       CloudWatch Logs    Proxy Response
             |                 |
             v                 v
      LAB03_BACKEND_ERROR   statusCode=500
                               |
                               v
                          API Gateway
                               |
                               v
                          HTTP 500
```

### Recovered Architecture

```text
                   API Client
                       |
                       v
                  GET /orders
                       |
                       v
                 API Gateway
                       |
                       v
                   Lambda
                       |
                       v
          ORDER_BACKEND_MODE=healthy
                       |
                       v
               Orders Retrieved
                       |
                       v
           LAB03_ORDER_SUCCESS
                       |
                       v
                 HTTP 200 OK
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives API requests |
| GET /orders | Exposes order retrieval |
| REST API Stage | Hosts deployed API configuration |
| Lambda Proxy Integration | Invokes Lambda and forwards responses |
| AWS Lambda | Processes requests |
| ORDER_BACKEND_MODE | Simulates backend availability |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Allows API Gateway invocation |
| CloudWatch Logs | Records application exceptions |
| API Gateway 5XXError | Measures server-side API responses |
| Lambda Errors | Measures function execution failures |
| curl | Reproduces HTTP errors |
| AWS CLI | Configures and investigates resources |

---

## 4. Understanding HTTP 500 and HTTP 502

### HTTP 500 Internal Server Error

HTTP 500 indicates that a server experienced a problem while processing a request.

A Lambda application can deliberately return HTTP 500 when it detects a backend failure.

Example:

```python
return {
    "statusCode": 500,
    "headers": {
        "Content-Type": "application/json"
    },
    "body": '{"message":"Internal server error"}'
}
```

With a valid Lambda proxy integration response, API Gateway forwards this status to the client.

### HTTP 502 Bad Gateway

HTTP 502 commonly occurs when an API Gateway Lambda proxy integration receives an unhandled function error or invalid proxy response.

Example:

```python
def lambda_handler(event, context):
    raise RuntimeError("Unhandled backend failure")
```

The function fails without returning a valid proxy response.

### Comparison

| Scenario | Typical API response |
|---|---|
| Lambda returns `statusCode: 200` | 200 |
| Lambda returns `statusCode: 404` | 404 |
| Lambda returns `statusCode: 500` | 500 |
| Lambda raises an unhandled exception | 502 |
| Lambda returns malformed proxy data | 502 |
| Lambda invocation rejected by Lambda service | 500 |

### Why Is This Important?

A developer may see HTTP 500 and immediately assume API Gateway itself is broken.

However, the backend may be deliberately returning the error.

Always inspect the integration, application logs, and actual Lambda response behavior.

### Handled Exceptions and CloudWatch Metrics

If Lambda catches an application exception and returns normally, Lambda considers the runtime invocation successful.

Therefore, the Lambda `Errors` metric does not necessarily increase even though API Gateway returns HTTP 500.

This is why production monitoring should include API-level and application-level error indicators.

---

## 5. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- Python 3.
- curl.
- ZIP and unzip.
- jq.
- IAM management permissions.
- Lambda management permissions.
- API Gateway management permissions.
- CloudWatch access.

### Relevant AWS Permissions

```text
sts:GetCallerIdentity

iam:CreateRole
iam:GetRole
iam:ListRoleTags
iam:AttachRolePolicy
iam:ListAttachedRolePolicies
iam:DetachRolePolicy
iam:DeleteRole
iam:PassRole

lambda:CreateFunction
lambda:GetFunction
lambda:GetFunctionConfiguration
lambda:UpdateFunctionConfiguration
lambda:AddPermission
lambda:GetPolicy
lambda:ListTags
lambda:DeleteFunction

apigateway:POST
apigateway:GET
apigateway:DELETE

logs:CreateLogGroup
logs:PutRetentionPolicy
logs:DescribeLogGroups
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

### Safety Rules

- Use a dedicated REST API.
- Do not modify production Lambda functions.
- Do not connect to real payment or order databases.
- Use fabricated order data.
- Avoid exposing credentials or secrets.
- Do not publish raw CloudWatch logs without review.
- Limit unnecessary API requests.
- Verify project tags before cleanup.
- Delete temporary AWS resources after testing.

### API Authorization

The lab uses authorization type `NONE`.

This is suitable only for this temporary API with fabricated data.

Production order APIs should implement appropriate authentication and authorization.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 03-api-returns-500

cd 03-api-returns-500
```

### Step 2 — Verify Tools

```bash
aws --version
python3 --version
curl --version
zip -v

aws sts get-caller-identity
```

Install missing packages:

```bash
sudo apt update

sudo apt install -y curl zip unzip jq
```

### Step 3 — Configure Variables

```bash
export AWS_REGION="us-east-1"
export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab03"

export REST_API_NAME="api-lab03-500-troubleshooting"

export FUNCTION_NAME="api-lab03-order-handler"

export ROLE_NAME="api-lab03-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab03"

export HEALTHY_MODE="healthy"
export BROKEN_MODE="unavailable"
```

### Step 4 — Save Environment Variables

```bash
cat > lab03-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export REST_API_NAME="$REST_API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STAGE_NAME="$STAGE_NAME"
export PERMISSION_SID="$PERMISSION_SID"
export HEALTHY_MODE="$HEALTHY_MODE"
export BROKEN_MODE="$BROKEN_MODE"
EOF

chmod 600 lab03-resources.env
```

Restore variables when needed:

```bash
source lab03-resources.env
```

### Step 5 — Check Existing Resources

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

```bash
aws apigateway get-rest-apis \
  --query "items[?name=='${REST_API_NAME}'].{Id:id,Name:name}" \
  --output table \
  --region "$AWS_REGION"
```

Do not overwrite existing unrelated resources.

---

## 7. Create Lambda Execution Role

### Step 1 — Create `lambda-trust-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Step 2 — Create IAM Role

```bash
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --description "API Gateway Lab 03 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Policy

```bash
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 4 — Verify

```bash
aws iam list-attached-role-policies \
  --role-name "$ROLE_NAME" \
  --output table
```

Expected:

```text
AWSLambdaBasicExecutionRole
```

---

## 8. Create the Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```python
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
```

### Understanding the Application

The function uses an environment variable to simulate backend availability.

Healthy state:

```text
ORDER_BACKEND_MODE=healthy
```

Broken state:

```text
ORDER_BACKEND_MODE=unavailable
```

When the backend is unavailable, `load_orders()` raises a `RuntimeError`.

The handler catches the exception using:

```python
except Exception:
```

It records diagnostic information through:

```python
logger.exception(...)
```

Then returns a structured HTTP 500 response.

This gives us a genuine backend-generated 500 without requiring a real database failure.

### Step 2 — Validate Python Syntax

```bash
python3 - <<'PY'
import ast
from pathlib import Path

ast.parse(Path("lambda_function.py").read_text())

print("SUCCESS: Python syntax valid")
PY
```

### Step 3 — Create Deployment Package

```bash
zip function.zip lambda_function.py
```

Verify:

```bash
unzip -l function.zip
```

---

## 9. Deploy Lambda in Healthy Mode

### Step 1 — Create Lambda

```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.13 \
  --role "$ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --memory-size 128 \
  --timeout 10 \
  --architectures x86_64 \
  --environment "Variables={ORDER_BACKEND_MODE=$HEALTHY_MODE}" \
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for Activation

```bash
aws lambda wait function-active-v2 \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Retrieve Function ARN

```bash
export FUNCTION_ARN=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --query Configuration.FunctionArn \
  --output text \
  --region "$AWS_REGION")

echo "$FUNCTION_ARN"

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab03-resources.env
```

### Step 4 — Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime,Backend:Environment.Variables}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Backend": {
    "ORDER_BACKEND_MODE": "healthy"
  }
}
```

---

## 10. Configure CloudWatch Logs

### Step 1 — Create Log Group

```bash
aws logs create-log-group \
  --log-group-name "$LOG_GROUP" \
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Configure Retention

```bash
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days 7 \
  --region "$AWS_REGION"
```

### Step 3 — Verify

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].{Name:logGroupName,Retention:retentionInDays}" \
  --output table \
  --region "$AWS_REGION"
```

---

## 11. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export REST_API_ID=$(aws apigateway create-rest-api \
  --name "$REST_API_NAME" \
  --description "Lab 03 API Gateway HTTP 500 troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$REST_API_ID"

echo "export REST_API_ID='$REST_API_ID'" >> lab03-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_RESOURCE_ID"

echo "export ROOT_RESOURCE_ID='$ROOT_RESOURCE_ID'" >> lab03-resources.env
```

### Step 3 — Create `/orders`

```bash
export RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id "$REST_API_ID" \
  --parent-id "$ROOT_RESOURCE_ID" \
  --path-part orders \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$RESOURCE_ID"

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab03-resources.env
```

### Step 4 — Configure GET

```bash
aws apigateway put-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --authorization-type NONE \
  --region "$AWS_REGION"
```

### Step 5 — Verify Method

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Method:httpMethod,Authorization:authorizationType}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Method": "GET",
  "Authorization": "NONE"
}
```

---

## 12. Configure API Gateway–Lambda Integration

### Step 1 — Generate Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Create Lambda Proxy Integration

```bash
aws apigateway put-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "$INTEGRATION_URI" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Type:type,IntegrationMethod:httpMethod,URI:uri}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
Type = AWS_PROXY
IntegrationMethod = POST
```

### Step 4 — Grant API Gateway Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${REST_API_ID}/*/GET/orders" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

The API Gateway principal should be permitted to invoke the function through the intended route.

---

## 13. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab03 healthy orders API deployment" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Generate API URL

```bash
export API_URL="https://${REST_API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/orders"

echo "$API_URL"

echo "export API_URL='$API_URL'" >> lab03-resources.env
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

---

## 14. Verify Healthy Baseline

### Step 1 — Send GET Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
content-type: application/json
```

### Step 2 — Expected Response

```json
{
  "message": "Orders retrieved successfully",
  "orders": [
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
}
```

### Step 3 — Save Baseline Response

```bash
curl -sS \
  -D baseline-headers.txt \
  -o baseline-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 200
```

### Step 4 — Validate Baseline

```bash
python3 - <<'PY'
import json

with open("baseline-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: Healthy baseline confirmed")
PY
```

### Step 5 — Check Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected application log:

```text
LAB03_ORDER_SUCCESS count=2
```

The baseline proves the API Gateway route and Lambda integration are working before the failure is introduced.

---

## 15. Fault Injection — Simulate Backend Failure

### Step 1 — Change Backend Mode

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "Variables={ORDER_BACKEND_MODE=$BROKEN_MODE}" \
  --region "$AWS_REGION"
```

The intentional misconfiguration is:

```text
ORDER_BACKEND_MODE=unavailable
```

### Step 2 — Wait for Lambda Update

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Broken Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,UpdateStatus:LastUpdateStatus,Environment:Environment.Variables}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "UpdateStatus": "Successful",
  "Environment": {
    "ORDER_BACKEND_MODE": "unavailable"
  }
}
```

### Step 4 — Save Broken Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab03-broken-function-config.json
```

### Fault Injection Summary

| Component | State |
|---|---|
| API Gateway | Healthy |
| Lambda integration | Correct |
| Lambda function | Active |
| Backend environment variable | Unavailable |
| Application exception | RuntimeError |
| Error handling | Catches exception |
| Expected response | HTTP 500 |

---

## 16. Reproduce HTTP 500

### Step 1 — Send Failing Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 500
content-type: application/json
```

Response:

```json
{
  "message": "Internal server error",
  "error_code": "ORDER_SERVICE_FAILURE"
}
```

### Step 2 — Save Broken Response

```bash
curl -sS \
  -D broken-headers.txt \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 500
```

### Step 3 — Inspect Response

```bash
python3 -m json.tool broken-response.json
```

### Step 4 — Verify HTTP Status

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "500" ]; then
  echo "SUCCESS: HTTP 500 reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 5 — Verify Error Payload

```bash
python3 - <<'PY'
import json

with open("broken-response.json") as file:
    response = json.load(file)

assert response["message"] == "Internal server error"
assert response["error_code"] == "ORDER_SERVICE_FAILURE"

print("SUCCESS: Application-generated 500 confirmed")
PY
```

### Broken-State Findings

| Check | Expected Result |
|---|---|
| GET /orders | Exists |
| API deployment | Exists |
| Lambda invocation | Successful |
| Lambda runtime | Active |
| Backend mode | unavailable |
| Internal exception | RuntimeError |
| Exception handling | Caught |
| API response | HTTP 500 |
| Root cause | Backend environment configuration |

---

## 17. Investigate CloudWatch Logs

### Step 1 — Inspect Recent Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected messages:

```text
LAB03_REQUEST method=GET path=/orders
LAB03_BACKEND_ERROR: order processing failed
RuntimeError: Order backend is unavailable: mode=unavailable
```

### Step 2 — Search for Backend Errors

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB03_BACKEND_ERROR"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 3 — Search for RuntimeError

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"RuntimeError"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Save Failure Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB03_BACKEND_ERROR"' \
  --output json \
  --region "$AWS_REGION" \
  > lab03-broken-cloudwatch-evidence.json
```

### Findings

CloudWatch confirms that:

1. The request reached Lambda.
2. Lambda attempted order retrieval.
3. The backend configuration caused a RuntimeError.
4. The exception was caught and logged.
5. The handler returned a structured HTTP 500 response.

The failure is an application-level problem, not an API Gateway routing failure.

---

## 18. Investigate API Gateway and Lambda

### Step 1 — Inspect REST API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query 'items[].{Path:path,ID:id}' \
  --output table \
  --region "$AWS_REGION"
```

### Step 2 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

Expected:

```text
Type = AWS_PROXY
IntegrationMethod = POST
```

### Step 4 — Verify Lambda Invocation Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 5 — Inspect Lambda Environment

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query 'Environment.Variables' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "ORDER_BACKEND_MODE": "unavailable"
}
```

### Step 6 — Inspect Source Code

```bash
grep -n 'ORDER_BACKEND_MODE' lambda_function.py
```

```bash
grep -n 'raise RuntimeError' lambda_function.py
```

```bash
grep -n 'LAB03_BACKEND_ERROR' lambda_function.py
```

### Investigation Summary

| Component | Finding |
|---|---|
| API resource | Correct |
| HTTP method | Correct |
| Deployment stage | Correct |
| Lambda proxy integration | Correct |
| Lambda invoke permission | Correct |
| Lambda execution | Reached handler |
| Backend configuration | Incorrect |
| Application error | RuntimeError |
| HTTP 500 source | Lambda application |

---

## 19. Investigate CloudWatch Metrics

### Step 1 — Define Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect API Gateway 5XXError

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value="$REST_API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

Expected: a nonzero datapoint after CloudWatch publishes the results.

### Step 3 — Inspect Lambda Errors

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

Because the application catches the exception and returns normally, Lambda does not treat the handled exception as a runtime failure.

Therefore, the Lambda Errors metric does not increase because of this specific handled exception.

### Step 4 — Save API Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value="$REST_API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab03-api-5xx-metric.json
```

### Step 5 — Save Lambda Error Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab03-lambda-errors-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 5XXError | Increases |
| Lambda Invocations | Increases |
| Lambda Errors | No increase caused by handled exception |
| Lambda Logs | Contains backend exception |
| HTTP response | 500 |

CloudWatch metrics may be delayed. An empty datapoint list immediately after testing is not proof that no errors occurred.

---

## 20. Root Cause Analysis

### Root Cause

The Lambda application's backend configuration was changed to an unavailable state.

The application then raised a RuntimeError while retrieving orders.

The handler caught the exception, recorded it in CloudWatch Logs, and returned an HTTP 500 proxy response.

API Gateway correctly forwarded this response to the client.

### Root Cause Diagram

```text
GET /dev/orders
       |
       v
API Gateway
       |
       v
Lambda Proxy Integration
       |
       v
Lambda Handler
       |
       v
load_orders()
       |
       v
ORDER_BACKEND_MODE=unavailable
       |
       v
RuntimeError
       |
       v
Exception Caught
       |
       v
CloudWatch Error Log
       |
       v
statusCode: 500
       |
       v
API Gateway Returns 500
```

### Five Whys

**Why 1 — Why did the API return HTTP 500?**

Lambda returned an application-generated HTTP 500 response.

**Why 2 — Why did Lambda return HTTP 500?**

The order-processing operation raised an exception.

**Why 3 — Why did order processing fail?**

The backend was configured as unavailable.

**Why 4 — Why was the backend unavailable?**

The Lambda environment variable was changed incorrectly.

**Why 5 — How can this incident be prevented?**

Use configuration validation, automated integration tests, deployment reviews, and production monitoring.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-003 |
| HTTP Error | 500 |
| API Resource | /orders |
| Method | GET |
| Backend Exception | RuntimeError |
| Broken Environment | unavailable |
| Root Cause | Incorrect backend configuration |
| Remediation | Restore healthy mode |
| Code Changes | None |
| API Redeployment | Not required |

---

## 21. Remediation — Restore Backend Configuration

### Step 1 — Restore Healthy Mode

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "Variables={ORDER_BACKEND_MODE=$HEALTHY_MODE}" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for Update

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,UpdateStatus:LastUpdateStatus,Environment:Environment.Variables}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "UpdateStatus": "Successful",
  "Environment": {
    "ORDER_BACKEND_MODE": "healthy"
  }
}
```

### Step 4 — Save Recovery Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab03-recovered-function-config.json
```

### Why API Gateway Redeployment Is Not Required

The API resource, method, integration, and stage are unchanged.

Only the Lambda environment configuration is updated.

Therefore, API Gateway does not need a new deployment.

---

## 22. Verify Successful Recovery

### Step 1 — Repeat Original Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
content-type: application/json
```

### Step 2 — Save Recovered Response

```bash
curl -sS \
  -D recovered-headers.txt \
  -o recovered-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 200
```

### Step 3 — Validate Response

```bash
python3 -m json.tool recovered-response.json
```

```bash
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2
assert response["orders"][0]["order_id"] == "1001"

print("SUCCESS: API Gateway HTTP 500 resolved")
PY
```

### Step 4 — Verify CloudWatch Recovery Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB03_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
LAB03_ORDER_SUCCESS count=2
```

### Step 5 — Save Recovery Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB03_ORDER_SUCCESS"' \
  --output json \
  --region "$AWS_REGION" \
  > lab03-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Healthy | Healthy |
| GET method | Correct | Correct |
| Lambda integration | Correct | Correct |
| Backend mode | unavailable | healthy |
| Application log | BACKEND_ERROR | ORDER_SUCCESS |
| HTTP status | 500 | 200 |
| Application code | Unchanged | Unchanged |
| API deployment | Unchanged | Unchanged |

**Recovery is verified when the original GET request returns HTTP 200 and CloudWatch confirms successful order retrieval.**

---

## 23. Additional Diagnostic — HTTP 500 vs. HTTP 502

### Handled Application Exception

```python
try:
    raise RuntimeError("Backend failure")

except Exception:
    return {
        "statusCode": 500,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": '{"message":"Internal server error"}'
    }
```

Expected HTTP response:

```http
HTTP/2 500
```

### Unhandled Lambda Exception

```python
def lambda_handler(event, context):
    raise RuntimeError("Unhandled backend failure")
```

Typical API Gateway Lambda proxy response:

```http
HTTP/2 502
```

### Invalid Lambda Proxy Response

```python
def lambda_handler(event, context):
    return {
        "message": "This is not a valid proxy response"
    }
```

Typical result:

```http
HTTP/2 502
```

### Lambda Service Invocation Failure

If Lambda itself rejects the invocation request, API Gateway can return HTTP 500.

The appropriate investigation depends on the actual failure source.

### Key Difference

| Failure Type | HTTP Response | Lambda Errors Metric |
|---|---|---|
| Caught exception, returns valid 500 | 500 | No increment from handled exception |
| Unhandled Lambda exception | 502 | Usually increments |
| Invalid Lambda proxy format | 502 | May not increment if handler returns normally |
| Lambda service rejects invocation | 500 | Depends on rejection and invocation behavior |

---

## 24. Production Troubleshooting Best Practices

### Investigation Checklist

1. Record the failing API URL and HTTP method.
2. Reproduce the error using curl.
3. Inspect response headers and body.
4. Verify API Gateway resource configuration.
5. Inspect the deployed API stage.
6. Confirm the HTTP method exists.
7. Inspect backend integration.
8. Verify Lambda invocation permission.
9. Check Lambda function state.
10. Inspect application logs.
11. Identify any exceptions.
12. Check Lambda environment variables.
13. Compare API Gateway and Lambda metrics.
14. Determine whether the failure is handled or unhandled.
15. Identify the root cause.
16. Apply targeted remediation.
17. Repeat the original request.
18. Verify successful recovery.
19. Document the incident.
20. Clean up AWS resources.

### Common 5XX Causes

| Symptom | Possible Cause | Investigation |
|---|---|---|
| HTTP 500 with application error code | Backend-generated response | Lambda code and logs |
| HTTP 500 with generic gateway error | Invocation/service failure | API Gateway integration |
| HTTP 502 | Unhandled Lambda exception | Lambda Errors and logs |
| HTTP 502 | Malformed proxy response | Response structure |
| HTTP 504 | Backend or integration timeout | Duration, latency, timeout configuration |
| Repeated 5XX after deployment | Incorrect configuration | Environment variables and revisions |
| 5XX increases but Lambda Errors stays low | Application returns handled errors | Application logs and API metrics |

---

## 25. Cloud Security Engineering Considerations

### Protect Sensitive Error Details

Do not return raw Python tracebacks, database credentials, internal hostnames, or secrets to API clients.

Use generic messages in HTTP responses and retain diagnostic details in protected logs.

### IAM Least Privilege

Grant API Gateway permission to invoke only the intended Lambda function and API route.

### Authentication and Authorization

The lab's unauthenticated API is temporary.

Production order APIs should use suitable authorization, such as IAM, Cognito, or an appropriate authorizer.

### Configuration Management

Manage backend configuration through Terraform, CloudFormation, or reviewed deployment pipelines.

Avoid unreviewed manual changes to production environment variables.

### Monitoring

Track:

```text
API Gateway 5XXError
Lambda Errors
Lambda Invocations
Lambda Duration
Application error logs
```

### Auditability

Use CloudTrail to investigate configuration changes and identify who changed Lambda environment settings.

---

## 26. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | API request charges |
| AWS Lambda | Request and execution charges |
| CloudWatch Logs | Log ingestion and retention |
| CloudWatch Metrics | Applicable monitoring charges |
| IAM | No separate standard role charge |

### Cost Optimization

- Use temporary lab resources.
- Keep Lambda memory low.
- Limit repeated API calls.
- Set CloudWatch log retention.
- Delete unused resources after testing.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only resources created for Lab 03.

### Step 1 — Verify API Gateway Tags

```bash
aws apigateway get-tags \
  --resource-arn "arn:aws:apigateway:${AWS_REGION}::/restapis/${REST_API_ID}" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Lambda Tags

```bash
aws lambda list-tags \
  --resource "$FUNCTION_ARN" \
  --region "$AWS_REGION"
```

### Step 3 — Verify IAM Role Tags

```bash
aws iam list-role-tags \
  --role-name "$ROLE_NAME"
```

Confirm:

```text
Project = API-Gateway-Troubleshooting-Lab03
```

### Step 4 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Step 5 — Delete Lambda Function

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 6 — Detach Logging Policy

```bash
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 7 — Delete IAM Role

```bash
aws iam delete-role \
  --role-name "$ROLE_NAME"
```

### Step 8 — Delete CloudWatch Log Group

```bash
aws logs delete-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

### Step 9 — Verify API Deletion

```bash
aws apigateway get-rest-api \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 10 — Verify Lambda Deletion

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Step 11 — Verify IAM Role Deletion

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected:

```text
NoSuchEntity
```

### Step 12 — Verify CloudWatch Cleanup

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].logGroupName" \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[]
```

### Cleanup Summary

| Resource | Expected State |
|---|---|
| REST API | Deleted |
| API stage and deployments | Deleted |
| API resources and integrations | Deleted |
| Lambda function | Deleted |
| Lambda invoke permission | Removed with function |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |
| VPC | Not created |

---

## 28. Interview Questions and Answers

### Q1. What does HTTP 500 mean?

An internal server error occurred while processing the request.

### Q2. What caused HTTP 500 in this lab?

The Lambda application's backend configuration was set to `unavailable`, causing a handled RuntimeError.

### Q3. Why did API Gateway return HTTP 500 rather than 502?

Lambda caught the exception and returned a valid proxy response containing `statusCode: 500`.

### Q4. What happens if Lambda raises an unhandled exception?

API Gateway typically returns HTTP 502 for Lambda proxy integration function errors.

### Q5. Why might Lambda Errors remain zero while API Gateway 5XXError increases?

Because Lambda can catch an exception and return a valid 500 application response without failing at the runtime level.

### Q6. Which CloudWatch metric tracks API Gateway server errors?

`5XXError`.

### Q7. How do you investigate an API Gateway 500?

Check the HTTP response, API configuration, Lambda integration, application logs, environment settings, and CloudWatch metrics.

### Q8. Why didn't we redeploy API Gateway after remediation?

We changed only the Lambda environment variable; the deployed REST API configuration was already correct.

### Q9. What is the correct Lambda proxy response format?

A structured response containing an HTTP status code and a string body, with optional headers and binary-encoding settings.

### Q10. Why should internal exception messages not be returned to clients?

They may expose information about internal infrastructure, application implementation, or sensitive configuration.

### Q11. How do you prevent configuration-based API failures?

Use reviewed Infrastructure as Code, automated tests, environment validation, and deployment monitoring.

### Q12. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

I first verified that the orders endpoint returned HTTP 200.

I then intentionally changed a Lambda environment variable to simulate an unavailable order-processing dependency.

The Lambda application raised a RuntimeError, caught the exception, wrote diagnostic details to CloudWatch Logs, and returned a structured HTTP 500 response.

I investigated the API Gateway resource, GET method, Lambda proxy integration, invocation permissions, backend configuration, and CloudWatch metrics.

I confirmed the error originated in the Lambda application rather than API Gateway routing.

I restored the correct Lambda environment setting and repeated the original request.

The API returned HTTP 200 and successfully retrieved the order records.

I also compared handled application-generated 500 responses with unhandled Lambda errors that typically return HTTP 502.

Finally, I deleted the temporary API Gateway, Lambda, IAM, and CloudWatch resources.

---

## 29. Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
├── 01-api-returns-403/
├── 02-api-returns-404/
│
├── 03-api-returns-500/
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab03-resources.env
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab03-broken-function-config.json
│   ├── lab03-recovered-function-config.json
│   ├── lab03-broken-cloudwatch-evidence.json
│   ├── lab03-recovered-cloudwatch-evidence.json
│   ├── lab03-api-5xx-metric.json
│   └── lab03-lambda-errors-metric.json
│
├── 04-api-gateway-lambda-integration-failure/
├── 05-cors-error/
├── 06-missing-authorization-token/
├── 07-api-key-usage-plan-misconfiguration/
├── 08-api-throttling-429/
├── 09-api-timeout-504/
└── 10-custom-domain-certificate-failure/
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Incident documentation and remediation |
| lambda_function.py | Python orders API backend |
| lambda-trust-policy.json | Lambda IAM trust policy |
| function.zip | Generated deployment package |
| lab03-resources.env | Local AWS resource variables |
| baseline-headers.txt | Healthy HTTP headers |
| baseline-response.json | Healthy HTTP response |
| broken-headers.txt | HTTP 500 headers |
| broken-response.json | Application error response |
| recovered-headers.txt | HTTP 200 headers after recovery |
| recovered-response.json | Recovered application response |
| lab03-broken-function-config.json | Broken Lambda configuration |
| lab03-recovered-function-config.json | Recovered Lambda configuration |
| lab03-broken-cloudwatch-evidence.json | Backend failure logs |
| lab03-recovered-cloudwatch-evidence.json | Successful processing logs |
| lab03-api-5xx-metric.json | API Gateway 5XX metrics |
| lab03-lambda-errors-metric.json | Lambda Errors metrics |

### Recommended Public GitHub Files

```text
03-api-returns-500/
├── README.md
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 03
03-api-returns-500/function.zip
03-api-returns-500/lab03-resources.env
03-api-returns-500/lab03-*.json
03-api-returns-500/*-headers.txt
03-api-returns-500/*-response.json

# Python
__pycache__/
*.pyc
.venv/

# Credentials
.env
.env.*
*.pem
*.key
```

Do not publish credentials or raw account-specific troubleshooting evidence without review.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how an API Gateway REST API can return HTTP 500 when a Lambda backend encounters an application-level problem.

We created a REST API integrated with a Python Lambda function.

We first verified that the backend returned HTTP 200 with order information.

We then intentionally changed the Lambda environment variable to simulate an unavailable backend.

The application raised a RuntimeError, caught the exception, logged the failure, and returned HTTP 500.

We investigated the API Gateway configuration, Lambda integration, environment variables, CloudWatch Logs, and metrics.

The investigation identified the incorrect backend configuration as the root cause.

We restored the environment variable to healthy mode without changing the Lambda code or redeploying API Gateway.

The original request returned HTTP 200 after remediation.

We also learned why a handled application exception can return HTTP 500 without increasing Lambda's runtime Errors metric.

Finally, we cleaned up the temporary AWS infrastructure.

**Key Lesson:** An API Gateway HTTP 500 does not automatically mean API Gateway itself is misconfigured. Engineers must trace the request through the API integration and backend application to identify the actual source of the failure.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 500 troubleshooting
- HTTP 500 versus HTTP 502
- Lambda proxy integration
- Python 3.13
- Lambda exception handling
- Lambda environment variables
- AWS IAM execution roles
- Lambda resource-based permissions
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch API metrics
- CloudWatch Lambda metrics
- Application error handling
- Root cause analysis
- Backend remediation
- Recovery verification
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-003 |
| Scenario | API Returns 500 |
| REST API | api-lab03-500-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab03-order-handler |
| Broken Backend Mode | unavailable |
| Healthy Backend Mode | healthy |
| Application Error | RuntimeError |
| Broken API Response | HTTP 500 |
| Root Cause | Incorrect Lambda configuration |
| Remediation | Restore backend mode |
| Recovery Response | HTTP 200 |
| Code Changes | None |
| API Gateway Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Effective API Gateway troubleshooting requires distinguishing application-level errors from integration errors, reading CloudWatch Logs, comparing service metrics, and making focused configuration changes.

---

## Official AWS Documentation

- [AWS Lambda — Handling API Gateway Errors](https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway-errors.html)
- [API Gateway — Handle Lambda Errors](https://docs.aws.amazon.com/apigateway/latest/developerguide/handle-errors-in-lambda-integration.html)
- [API Gateway — Lambda Proxy Integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [AWS CLI — Update Lambda Function Configuration](https://docs.aws.amazon.com/cli/latest/reference/lambda/update-function-configuration.html)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)