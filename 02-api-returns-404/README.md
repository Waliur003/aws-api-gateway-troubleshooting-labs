# Lab 02 — Amazon API Gateway Returns 404 Not Found

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP `404 Not Found` error in an Amazon API Gateway REST API integrated with AWS Lambda.

In production, applications frequently use API Gateway to expose REST endpoints that communicate with Lambda functions and other backend services.

An API may have a correctly configured route and a healthy Lambda integration but still return HTTP 404 because of incorrect application routing, missing resources, or configuration mismatches.

In this lab, we deploy a REST API containing:

```http
GET /dev/orders/{orderId}
```

The API uses a Lambda proxy integration that retrieves order information from a small Python application.

We intentionally configure the Lambda environment variable `EXPECTED_PREFIX` to `/order/`, while the API Gateway resource uses `/orders/{orderId}`.

When a client requests `/dev/orders/1001`, API Gateway successfully invokes Lambda.

However, the Lambda application checks the request path against the incorrect prefix and returns HTTP 404.

We investigate the problem using AWS CLI, curl, API Gateway resource configuration, Lambda environment variables, and CloudWatch Logs.

After identifying the root cause, we correct the Lambda environment variable to `/orders/` and repeat the original request.

The API returns HTTP 200 with the expected order details.

We also compare a genuine backend-generated 404 with the default API Gateway REST API response for an undefined route or HTTP method, which commonly returns HTTP 403 with `Missing Authentication Token`.

Finally, we remove the temporary API Gateway, Lambda, IAM, and CloudWatch resources.

### Troubleshooting Workflow

```text
Create Lambda Execution Role
             |
             v
Create Python Lambda Application
             |
             v
Configure EXPECTED_PREFIX=/order/
             |
             v
Deploy Lambda
             |
             v
Create API Gateway REST API
             |
             v
Create /orders/{orderId}
             |
             v
Configure GET Method
             |
             v
Configure Lambda Proxy Integration
             |
             v
Grant API Gateway Invocation Permission
             |
             v
Deploy dev Stage
             |
             v
GET /dev/orders/1001
             |
             v
API Gateway Route Matches
             |
             v
Lambda Invoked
             |
             v
Incorrect Prefix Comparison
             |
             v
Lambda Returns 404
             |
             v
Investigate CloudWatch Logs
             |
             v
Identify Backend Prefix Mismatch
             |
             v
Correct EXPECTED_PREFIX=/orders/
             |
             v
Repeat Original Request
             |
             v
HTTP 200 OK
             |
             v
Verify Order Response
             |
             v
Compare 403 and 404 Scenarios
             |
             v
Cleanup AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-002 |
| Lab Name | API Returns 404 |
| Difficulty | Beginner to Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | Lambda, IAM, CloudWatch |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab02-404-troubleshooting` |
| API Resource | `/orders/{orderId}` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization Type | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab02-order-handler` |
| Execution Role | `api-lab02-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Broken Environment Variable | `EXPECTED_PREFIX=/order/` |
| Correct Environment Variable | `EXPECTED_PREFIX=/orders/` |
| Test Order | `1001` |
| Expected Failure | HTTP 404 |
| Root Cause | Incorrect backend route prefix |
| Remediation | Correct Lambda environment variable |
| Recovery Response | HTTP 200 |
| VPC / NAT Gateway | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand API Gateway REST API routing.
- Understand HTTP 404 Not Found responses.
- Create nested API Gateway resources.
- Configure path parameters.
- Create a Lambda proxy integration.
- Understand Lambda proxy request and response formats.
- Reproduce a backend-generated 404.
- Investigate Lambda environment variables.
- Use CloudWatch Logs to identify incorrect routing.
- Distinguish missing routes from missing application resources.
- Understand API Gateway's default 403 behavior for undefined methods.
- Update Lambda configuration using AWS CLI.
- Verify recovery without unnecessary API redeployment.
- Practice production incident analysis.
- Apply cloud security principles.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application using Amazon API Gateway and AWS Lambda.

Customers retrieve information about individual orders using an API endpoint.

Example:

```http
GET /dev/orders/1001
```

The API Gateway REST API contains the resource:

```text
/orders/{orderId}
```

The backend Lambda function uses Python to retrieve order information.

However, after a configuration change, customers begin receiving:

```http
HTTP/2 404
```

With a response similar to:

```json
{
  "message": "Order endpoint not found",
  "requested_path": "/orders/1001"
}
```

The operations team initially suspects that the API Gateway resource is missing.

The Cloud Engineer investigates the incident.

The engineer confirms that:

- The REST API exists.
- The `/orders/{orderId}` resource exists.
- The GET method is configured.
- The `dev` deployment stage exists.
- The Lambda proxy integration points to the correct function.
- API Gateway has permission to invoke Lambda.
- Lambda successfully receives the request.

CloudWatch Logs show:

```text
LAB02_ROUTE_NOT_FOUND path=/orders/1001 expected=/order/
```

The engineer identifies the incorrect Lambda environment variable as the root cause.

The API Gateway path is `/orders/1001`, but the Lambda application expects the prefix `/order/`.

The engineer updates the environment variable to `/orders/`.

After remediation, the original API request returns HTTP 200 with the requested order information.

### Incident Symptoms

- API Gateway endpoint is accessible.
- The API returns HTTP 404.
- API resource and HTTP method exist.
- Lambda is successfully invoked.
- CloudWatch Logs show a route mismatch.
- Lambda expects an incorrect path prefix.
- Correcting the environment variable restores successful processing.

### Business Impact

Incorrect API routing can cause:

- Failed order lookups.
- Customer-facing errors.
- Interrupted application workflows.
- Inconsistent API behavior.
- Failed frontend integrations.
- Increased support requests.
- Unnecessary API Gateway reconfiguration.
- Increased incident response time.

### Objective

Identify whether the HTTP 404 originates from API Gateway or the Lambda application, correct the backend routing configuration, and verify recovery using the original request.

---

## 3. AWS Architecture

### Broken Architecture

```text
                  API Client
                      |
                      v
             GET /dev/orders/1001
                      |
                      v
               Amazon API Gateway
                      |
                      v
             /orders/{orderId}
                      |
                      v
                 Route Matched
                      |
                      v
             Lambda Proxy Integration
                      |
                      v
                  AWS Lambda
                      |
                      v
              Path = /orders/1001
                      |
                      v
          EXPECTED_PREFIX = /order/
                      |
                      v
             Prefix Comparison Fails
                      |
                      v
           Lambda Returns statusCode 404
                      |
                      v
                 HTTP 404 Not Found
```

### Recovered Architecture

```text
                  API Client
                      |
                      v
             GET /dev/orders/1001
                      |
                      v
               Amazon API Gateway
                      |
                      v
             /orders/{orderId}
                      |
                      v
                 Route Matched
                      |
                      v
             Lambda Proxy Integration
                      |
                      v
                  AWS Lambda
                      |
                      v
              Path = /orders/1001
                      |
                      v
         EXPECTED_PREFIX = /orders/
                      |
                      v
              Prefix Comparison Passes
                      |
                      v
                 Order ID = 1001
                      |
                      v
                Order Record Found
                      |
                      v
           Lambda Returns statusCode 200
                      |
                      v
                    HTTP 200
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Hosts the REST endpoint |
| API Resource | Matches `/orders/{orderId}` |
| GET Method | Handles order retrieval |
| Path Parameter | Passes `orderId` to Lambda |
| Lambda Proxy Integration | Forwards requests to Lambda |
| AWS Lambda | Processes API requests |
| Lambda Environment Variable | Controls expected path prefix |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource-Based Policy | Allows API Gateway invocation |
| CloudWatch Logs | Records request routing results |
| AWS CLI | Deploys and inspects resources |
| curl | Reproduces HTTP errors |

---

## 4. Understanding API Gateway 404 Errors

### What Does HTTP 404 Mean?

HTTP 404 indicates that the requested resource was not found.

The response may originate from a backend application or from API Gateway configuration.

### Does API Gateway Always Return HTTP 404 for an Invalid Route?

No.

For REST APIs, an undefined resource or unsupported HTTP method commonly results in HTTP 403 with:

```json
{
  "message": "Missing Authentication Token"
}
```

This is an important distinction during troubleshooting.

### What Is a Backend-Generated 404?

A backend-generated 404 occurs when API Gateway invokes the integration and the backend returns an HTTP 404 response.

For Lambda proxy integrations:

```python
return {
    "statusCode": 404,
    "body": json.dumps({
        "message": "Order endpoint not found"
    })
}
```

API Gateway normally forwards that status code to the client when the Lambda response format is valid.

### What Is a Path Parameter?

A variable segment of an API resource.

Example:

```text
/orders/{orderId}
```

For:

```text
/orders/1001
```

API Gateway passes:

```json
{
  "pathParameters": {
    "orderId": "1001"
  }
}
```

### What Is a Route Prefix?

A path segment used by the backend to determine whether a request matches a supported endpoint.

In this lab:

```text
Expected prefix: /order/
Actual path:     /orders/1001
```

These values do not match.

### What Is a Lambda Proxy Integration?

A Lambda proxy integration forwards request details to Lambda and expects a structured response containing fields such as:

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"message\":\"Success\"}"
}
```

### Why Is CloudWatch Important?

CloudWatch shows whether Lambda received a request and which application branch executed.

It helps distinguish API Gateway routing failures from backend application errors.

---

## 5. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Python 3.
- curl.
- ZIP and unzip.
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

- Use a dedicated temporary REST API.
- Do not modify production API routes.
- Do not deploy real customer data.
- Use fabricated order records.
- Keep IAM permissions minimal.
- Verify resource ownership before cleanup.
- Avoid exposing internal application information unnecessarily.
- Delete the public test endpoint after completing the lab.

### API Authorization Notice

This lab uses:

```text
Authorization = NONE
```

The API is publicly callable while deployed.

This is acceptable only for a dedicated, temporary learning environment using fabricated data.

Production order APIs should implement appropriate authentication and authorization.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create the Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 02-api-returns-404

cd 02-api-returns-404
```

### Step 2 — Verify Tools

```bash
aws --version
python3 --version
curl --version
zip -v

aws sts get-caller-identity
```

Install missing utilities:

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

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab02"

export REST_API_NAME="api-lab02-404-troubleshooting"

export FUNCTION_NAME="api-lab02-order-handler"

export ROLE_NAME="api-lab02-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab02"

export BROKEN_PREFIX="/order/"

export CORRECT_PREFIX="/orders/"
```

### Step 4 — Save Variables

```bash
cat > lab02-resources.env <<EOF
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
export BROKEN_PREFIX="$BROKEN_PREFIX"
export CORRECT_PREFIX="$CORRECT_PREFIX"
EOF

chmod 600 lab02-resources.env
```

Restore later:

```bash
source lab02-resources.env
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

A fresh lab should not already contain these named resources.

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
  --description "API Gateway Lab 02 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Permissions

```bash
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 4 — Verify Role

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
```

### Understanding the Application

The Lambda function supports three response scenarios.

| Scenario | Condition | Result |
|---|---|---|
| Incorrect route prefix | Path does not match EXPECTED_PREFIX | 404 |
| Missing order | Valid route, unknown orderId | 404 |
| Valid order | Valid route and known orderId | 200 |

### Step 2 — Validate Syntax

```bash
python3 - <<'PY'
import ast
from pathlib import Path

ast.parse(Path("lambda_function.py").read_text())

print("SUCCESS: Python syntax valid")
PY
```

### Step 3 — Package Lambda

```bash
zip function.zip lambda_function.py
```

Verify:

```bash
unzip -l function.zip
```

---

## 9. Deploy Lambda with the Incorrect Prefix

### Step 1 — Create the Function

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
  --environment "Variables={EXPECTED_PREFIX=$BROKEN_PREFIX}" \
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

The intentional misconfiguration is:

```text
EXPECTED_PREFIX=/order/
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

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab02-resources.env
```

### Step 4 — Verify Environment Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Environment:Environment.Variables}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Environment": {
    "EXPECTED_PREFIX": "/order/"
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

### Step 2 — Set Retention

```bash
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days 7 \
  --region "$AWS_REGION"
```

### Step 3 — Verify Log Group

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].{Name:logGroupName,Retention:retentionInDays}" \
  --output table \
  --region "$AWS_REGION"
```

---

## 11. Create the API Gateway REST API

### Step 1 — Create Regional API

```bash
export REST_API_ID=$(aws apigateway create-rest-api \
  --name "$REST_API_NAME" \
  --description "Lab 02 HTTP 404 troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$REST_API_ID"

echo "export REST_API_ID='$REST_API_ID'" >> lab02-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_RESOURCE_ID"

echo "export ROOT_RESOURCE_ID='$ROOT_RESOURCE_ID'" >> lab02-resources.env
```

### Step 3 — Create `/orders`

```bash
export ORDERS_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id "$REST_API_ID" \
  --parent-id "$ROOT_RESOURCE_ID" \
  --path-part orders \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$ORDERS_RESOURCE_ID"

echo "export ORDERS_RESOURCE_ID='$ORDERS_RESOURCE_ID'" >> lab02-resources.env
```

### Step 4 — Create `/{orderId}`

```bash
export ORDER_ID_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id "$REST_API_ID" \
  --parent-id "$ORDERS_RESOURCE_ID" \
  --path-part '{orderId}' \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$ORDER_ID_RESOURCE_ID"

echo "export ORDER_ID_RESOURCE_ID='$ORDER_ID_RESOURCE_ID'" >> lab02-resources.env
```

### Step 5 — Verify Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query 'items[].{Path:path,Id:id}' \
  --output table \
  --region "$AWS_REGION"
```

Expected:

```text
/
/orders
/orders/{orderId}
```

### Step 6 — Create GET Method

```bash
aws apigateway put-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$ORDER_ID_RESOURCE_ID" \
  --http-method GET \
  --authorization-type NONE \
  --region "$AWS_REGION"
```

### Step 7 — Verify Method

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$ORDER_ID_RESOURCE_ID" \
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

### Step 1 — Define Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Create Lambda Proxy Integration

```bash
aws apigateway put-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$ORDER_ID_RESOURCE_ID" \
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
  --resource-id "$ORDER_ID_RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

Expected relevant fields:

```text
type = AWS_PROXY
httpMethod = POST
```

### Step 4 — Grant Lambda Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${REST_API_ID}/*/GET/orders/*" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Invocation Permission

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

This permission allows API Gateway to invoke the backend function.

---

## 13. Deploy the API Gateway REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab02 initial backend routing misconfiguration" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Build API URL

```bash
export API_BASE_URL="https://${REST_API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"

export API_URL="${API_BASE_URL}/orders/1001"

echo "$API_URL"
```

### Step 4 — Save URL

```bash
cat >> lab02-resources.env <<EOF
export API_BASE_URL='$API_BASE_URL'
export API_URL='$API_URL'
EOF
```

The REST API is deployed with a valid route and intentionally misconfigured Lambda backend.

---

## 14. Fault Injection — Reproduce HTTP 404

### Step 1 — Send GET Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 404
content-type: application/json
```

```json
{
  "message": "Order endpoint not found",
  "requested_path": "/orders/1001"
}
```

### Step 2 — Save Response Evidence

```bash
curl -sS \
  -D broken-headers.txt \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 404
```

### Step 3 — Inspect Response

```bash
python3 -m json.tool broken-response.json
```

### Step 4 — Verify Error Payload

```bash
python3 - <<'PY'
import json

with open("broken-response.json") as file:
    response = json.load(file)

assert response["message"] == "Order endpoint not found"
assert response["requested_path"] == "/orders/1001"

print("SUCCESS: Backend route mismatch reproduced")
PY
```

### Step 5 — Verify HTTP Status

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "404" ]; then
  echo "SUCCESS: HTTP 404 reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 6 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected:

```text
LAB02_REQUEST method=GET path=/orders/1001 expected_prefix=/order/
LAB02_ROUTE_NOT_FOUND path=/orders/1001 expected=/order/
```

### Step 7 — Save Failure Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB02_ROUTE_NOT_FOUND"' \
  --output json \
  --region "$AWS_REGION" \
  > lab02-broken-cloudwatch-evidence.json
```

### Broken-State Findings

| Investigation | Expected Result |
|---|---|
| API resource | Exists |
| GET method | Exists |
| Deployment stage | Exists |
| Lambda integration | Correct |
| Lambda invocation | Successful |
| Actual request path | `/orders/1001` |
| Lambda expected prefix | `/order/` |
| HTTP response | 404 |
| Root cause | Backend routing mismatch |

---

## 15. Investigate the 404 Using AWS CLI

### Step 1 — Inspect API Gateway Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$ORDER_ID_RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$ORDER_ID_RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Lambda Environment Variables

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
  "EXPECTED_PREFIX": "/order/"
}
```

### Step 5 — Save Broken Lambda Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab02-broken-function-config.json
```

### Step 6 — Inspect Source Code

```bash
grep -n 'EXPECTED_PREFIX' lambda_function.py
```

```bash
grep -n 'path.startswith' lambda_function.py
```

### Investigation Findings

| Component | Finding |
|---|---|
| API Gateway resource | Correct |
| HTTP method | Correct |
| Stage deployment | Correct |
| Lambda integration | Correct |
| Path parameter | Available |
| Lambda route validation | Incorrect |
| Environment variable | `/order/` |
| Expected prefix | `/orders/` |
| Root cause | Prefix mismatch |

---

## 16. Root Cause Analysis

### Root Cause

The Lambda backend was configured to expect the route prefix `/order/`.

However, API Gateway forwarded the actual path `/orders/1001`.

The application performed a prefix comparison that failed.

Consequently, the Lambda function returned HTTP 404 even though the requested order existed in the application's test data.

### Root Cause Diagram

```text
GET /dev/orders/1001
          |
          v
API Gateway Route Matches
          |
          v
Lambda Invoked
          |
          v
Path = /orders/1001
          |
          v
Expected Prefix = /order/
          |
          v
Prefix Comparison Fails
          |
          v
Lambda Returns 404
          |
          v
API Gateway Forwards 404
          |
          v
Client Receives Not Found
```

### Five Whys

**Why 1 — Why did the API return 404?**

The Lambda application returned statusCode 404.

**Why 2 — Why did Lambda return 404?**

Its route-prefix validation rejected the request.

**Why 3 — Why did the route-prefix validation fail?**

The configured prefix was `/order/`, but the actual API path was `/orders/1001`.

**Why 4 — Why was the wrong prefix configured?**

The Lambda environment configuration did not match the API Gateway route.

**Why 5 — How can the issue be prevented?**

Keep route definitions consistent through Infrastructure as Code, integration testing, and configuration validation.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-002 |
| HTTP Error | 404 Not Found |
| API Route | `/orders/{orderId}` |
| Actual Path | `/orders/1001` |
| Incorrect Prefix | `/order/` |
| Expected Prefix | `/orders/` |
| Root Cause | Lambda route configuration mismatch |
| Remediation | Update Lambda environment variable |
| Python Code Change | Not required |
| API Redeployment | Not required |

---

## 17. Remediation — Correct Lambda Route Configuration

### Step 1 — Update Environment Variable

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "Variables={EXPECTED_PREFIX=$CORRECT_PREFIX}" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for Update

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Updated Configuration

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
    "EXPECTED_PREFIX": "/orders/"
  }
}
```

### Step 4 — Save Recovery Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab02-recovered-function-config.json
```

### Before and After

| Configuration | Broken | Recovered |
|---|---|---|
| API route | `/orders/{orderId}` | Unchanged |
| HTTP method | GET | GET |
| Lambda expected prefix | `/order/` | `/orders/` |
| Lambda source code | Unchanged | Unchanged |
| API deployment | Unchanged | Unchanged |
| Expected HTTP response | 404 | 200 |

### Why API Redeployment Is Not Required

The API Gateway REST API configuration has not changed.

Only the Lambda environment variable is updated.

Therefore, a new API Gateway deployment is unnecessary for this remediation.

---

## 18. Verify Successful Recovery

### Step 1 — Repeat Original Request

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
  "message": "Order retrieved successfully",
  "order": {
    "order_id": "1001",
    "customer": "Test Customer",
    "status": "processing",
    "total": 149.99
  }
}
```

### Step 3 — Save Recovery Evidence

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

### Step 4 — Verify Response

```bash
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Order retrieved successfully"
assert response["order"]["order_id"] == "1001"
assert response["order"]["status"] == "processing"

print("SUCCESS: Original API request recovered")
PY
```

### Step 5 — Verify Lambda Processing Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB02_ORDER_FOUND"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
LAB02_ORDER_FOUND order_id=1001
```

### Step 6 — Save CloudWatch Recovery Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB02_ORDER_FOUND"' \
  --output json \
  --region "$AWS_REGION" \
  > lab02-recovered-cloudwatch-evidence.json
```

### Recovery Verification

| Check | Broken | Recovered |
|---|---|---|
| REST API | Active | Active |
| Lambda integration | Working | Working |
| Lambda invoked | Yes | Yes |
| Expected prefix | `/order/` | `/orders/` |
| Order lookup | Not reached | Successful |
| HTTP status | 404 | 200 |
| CloudWatch log | ROUTE_NOT_FOUND | ORDER_FOUND |
| Code changes | None | None |

**Recovery is confirmed when the original URL returns HTTP 200 and Lambda logs show that order 1001 was found.**

---

## 19. Compare Different 404 and 403 Scenarios

Understanding the origin of an HTTP error is essential for production troubleshooting.

### Test A — Existing Order

```bash
curl -i "${API_BASE_URL}/orders/1001"
```

Expected:

```http
HTTP/2 200
```

### Test B — Missing Order Record

```bash
curl -i "${API_BASE_URL}/orders/9999"
```

Expected:

```http
HTTP/2 404
```

```json
{
  "message": "Order not found",
  "order_id": "9999"
}
```

The API route exists, but the requested order does not.

### Test C — Incorrect API Gateway Route

```bash
curl -i "${API_BASE_URL}/order/1001"
```

For the default REST API behavior, expect:

```http
HTTP/2 403
```

```json
{
  "message": "Missing Authentication Token"
}
```

### Test D — Unsupported HTTP Method

```bash
curl -i -X POST "${API_BASE_URL}/orders/1001"
```

Expected: HTTP 403 with a gateway-generated missing-method response under the default REST API configuration.

### Response Comparison

| Request | HTTP Status | Source |
|---|---|---|
| GET `/orders/1001` | 200 | Lambda success |
| GET `/orders/9999` | 404 | Lambda order lookup |
| GET `/order/1001` | 403 | API Gateway undefined path |
| POST `/orders/1001` | 403 | API Gateway undefined method |

### Key Lesson

A backend-generated 404 and a gateway-generated 403 can both indicate that an API request did not find its intended resource.

However, they represent different failure points and require different investigations.

---

## 20. CloudWatch Monitoring

### Step 1 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 30m \
  --region "$AWS_REGION"
```

Important log markers:

```text
LAB02_REQUEST
LAB02_ROUTE_NOT_FOUND
LAB02_ORDER_NOT_FOUND
LAB02_ORDER_FOUND
```

### Step 2 — Define Metrics Window

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 3 — Inspect API Gateway 4XX Errors

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value="$REST_API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

Metric delivery may be delayed.

### Monitoring Notes

The `4XXError` metric does not independently identify the exact cause of a 4XX response.

Production systems should combine:

- API access logs.
- HTTP status and path information.
- Request IDs.
- Lambda execution logs.
- Application-specific error messages.

---

## 21. Production Troubleshooting Best Practices

### Investigation Checklist

1. Verify the failing API URL.
2. Record the HTTP status and response body.
3. Check the REST API ID and Region.
4. Inspect the deployment stage.
5. Confirm the resource path exists.
6. Verify the HTTP method.
7. Inspect API Gateway integration.
8. Verify Lambda invocation permissions.
9. Determine whether the request reached Lambda.
10. Inspect Lambda environment variables.
11. Review backend routing logic.
12. Identify whether the requested order exists.
13. Determine the exact source of the 404.
14. Apply targeted remediation.
15. Repeat the original request.
16. Verify the expected response.
17. Review CloudWatch evidence.
18. Document the incident.
19. Clean up AWS resources.

### Common HTTP 404 Causes

| Problem | Possible Cause | Investigation |
|---|---|---|
| Backend route mismatch | Wrong expected path | Lambda configuration |
| Missing order | Order ID not found | Application data |
| Incorrect path parameter | Wrong parameter name | API event and code |
| Custom domain mapping error | Incorrect base path | Domain API mapping |
| Outdated API deployment | Stage references old configuration | Deployments |
| Missing backend route | Handler has no matching route | Lambda logs |
| Wrong HTTP method | Unsupported operation | API Gateway method |
| Incorrect URL | Path or stage mistake | curl and resource inspection |

---

## 22. Cloud Security Engineering Considerations

### Authorization

The lab uses an unauthenticated temporary API.

Production order APIs should require appropriate authentication and authorization.

### Object-Level Authorization

A production application must verify that the requesting user is authorized to access the requested order.

A valid order ID alone should not grant access to another customer's information.

### Input Validation

Validate route parameters and reject malformed or unexpected inputs.

### Error Handling

Avoid returning stack traces, internal configuration, secrets, or database details in public API responses.

### Logging

Log useful diagnostic information while minimizing sensitive customer data.

### IAM Least Privilege

Grant API Gateway only the Lambda invocation permission required for the intended route.

### Configuration Management

Use Terraform or CloudFormation to keep API route definitions and backend configuration consistent.

---

## 23. Cost Management

### Potential AWS Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Requests |
| AWS Lambda | Invocations and duration |
| CloudWatch Logs | Ingestion and storage |
| CloudWatch Metrics | Applicable usage charges |
| IAM | No separate standard role charge |

### Cost Optimization

- Keep test requests limited.
- Use a small Lambda memory configuration.
- Set CloudWatch log retention.
- Avoid unnecessary infrastructure.
- Delete the REST API immediately after testing.

---

## 24. AWS Resource Cleanup

**Warning: Delete only resources created for Lab 02.**

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
Project = API-Gateway-Troubleshooting-Lab02
```

### Step 4 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Step 5 — Delete Lambda

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 6 — Detach IAM Policy

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

### Step 9 — Verify REST API Deletion

```bash
aws apigateway get-rest-api \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

Expected: `NotFoundException`.

### Step 10 — Verify Lambda Deletion

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected: `ResourceNotFoundException`.

### Step 11 — Verify IAM Role Deletion

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected: `NoSuchEntity`.

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
| API Gateway REST API | Deleted |
| API resources and methods | Deleted |
| API stage and deployment | Deleted |
| Lambda function | Deleted |
| Lambda invocation permission | Removed with Lambda |
| IAM execution role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |
| VPC | Not created |

---

## 25. Interview Questions and Answers

### Q1. What does HTTP 404 mean?

It means the requested resource was not found.

### Q2. What caused the HTTP 404 in this lab?

The Lambda application expected `/order/`, but API Gateway forwarded `/orders/1001`.

### Q3. Was API Gateway configured incorrectly?

No. The API resource, method, stage, and Lambda integration were correct.

### Q4. How did you identify the root cause?

By checking Lambda environment variables, API Gateway resources, and CloudWatch Logs.

### Q5. Does API Gateway always return 404 for an invalid path?

No. REST APIs commonly return 403 with `Missing Authentication Token` for undefined paths or methods.

### Q6. What is a Lambda proxy integration?

It forwards HTTP request details to Lambda and uses the function's structured response to produce the API response.

### Q7. What is a path parameter?

A variable part of an API resource path, such as `{orderId}`.

### Q8. What is the difference between a missing order and an invalid API path?

A missing order is a backend data problem. An invalid API path is a routing or configuration problem.

### Q9. Why didn't you redeploy API Gateway to fix the error?

The API configuration did not change. Only the Lambda environment variable was corrected.

### Q10. How can you prevent backend route mismatches?

Use consistent route definitions, automated tests, configuration validation, and Infrastructure as Code.

### Q11. What CloudWatch logs helped identify the issue?

`LAB02_ROUTE_NOT_FOUND` showed the actual request path and expected prefix.

### Q12. What was the recovery verification?

The same GET request returned HTTP 200 and the expected order information.

### Q13. What security risk exists in an order lookup API?

Without object-level authorization, users may access order information belonging to other customers.

### Q14. How would you explain this lab in an interview?

I created an API Gateway REST API with a GET /orders/{orderId} endpoint connected to AWS Lambda.

I intentionally configured the Lambda function to expect the wrong route prefix.

When I requested an existing order, the API returned HTTP 404 even though the API Gateway route was correct.

I investigated the REST API resource, HTTP method, Lambda integration, environment variables, and CloudWatch Logs.

I identified a mismatch between the actual request path `/orders/1001` and the Lambda configuration `/order/`.

I corrected the environment variable to `/orders/` and tested the original request again.

The API returned HTTP 200 with the expected order information.

I also compared this backend-generated 404 with the default 403 response from an undefined API Gateway REST API route.

Finally, I deleted all temporary AWS resources.

---

## 26. Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-api-returns-403/
│
├── 02-api-returns-404/
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab02-resources.env
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab02-broken-function-config.json
│   ├── lab02-recovered-function-config.json
│   ├── lab02-broken-cloudwatch-evidence.json
│   └── lab02-recovered-cloudwatch-evidence.json
│
├── 03-api-returns-500/
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
| README.md | Production incident and remediation documentation |
| lambda_function.py | Python order API backend |
| lambda-trust-policy.json | IAM role trust policy |
| function.zip | Generated Lambda deployment package |
| lab02-resources.env | Local AWS resource variables |
| broken-headers.txt | Initial HTTP response headers |
| broken-response.json | HTTP 404 response |
| recovered-headers.txt | Recovered HTTP headers |
| recovered-response.json | Successful order response |
| lab02-broken-function-config.json | Broken Lambda configuration evidence |
| lab02-recovered-function-config.json | Corrected Lambda configuration evidence |
| lab02-broken-cloudwatch-evidence.json | Route mismatch logs |
| lab02-recovered-cloudwatch-evidence.json | Successful order lookup logs |

### Recommended Public GitHub Files

```text
02-api-returns-404/
├── README.md
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root .gitignore

Add:

```gitignore
# API Gateway Lab 02
02-api-returns-404/function.zip
02-api-returns-404/lab02-resources.env
02-api-returns-404/lab02-*.json
02-api-returns-404/*-headers.txt
02-api-returns-404/*-response.json

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

Avoid publishing raw account-specific troubleshooting evidence without review.

---

## 27. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how an incorrect backend route configuration can cause API Gateway to return HTTP 404 even when the REST API itself is correctly configured.

We created an API Gateway REST API and connected it to a Python Lambda function.

We intentionally configured the Lambda environment variable with an incorrect route prefix.

When we requested an existing order, API Gateway invoked Lambda, but the application returned HTTP 404.

We inspected API Gateway resources, HTTP methods, Lambda integration settings, environment variables, and CloudWatch Logs.

The investigation identified the route-prefix mismatch as the root cause.

We corrected the Lambda environment variable without changing the application code or redeploying API Gateway.

After remediation, the original request returned HTTP 200 and the expected order information.

We also compared application-level 404 responses with default API Gateway REST API behavior for missing routes and unsupported HTTP methods.

Finally, we cleaned up all temporary AWS resources.

**Key Lesson:** HTTP status codes must be investigated in context. A 404 can come from the backend, while a missing API Gateway REST API route may produce a different error response.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 404 troubleshooting
- API resources and path parameters
- REST API deployments and stages
- AWS Lambda
- Python 3.13
- Lambda environment variables
- Lambda proxy integrations
- IAM execution roles
- Lambda resource-based permissions
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch API metrics
- Root cause analysis
- Configuration remediation
- Recovery verification
- API security considerations
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-002 |
| Scenario | API Returns 404 |
| API Name | api-lab02-404-troubleshooting |
| Resource | /orders/{orderId} |
| HTTP Method | GET |
| Stage | dev |
| Lambda Function | api-lab02-order-handler |
| Incorrect Prefix | /order/ |
| Correct Prefix | /orders/ |
| Broken Response | HTTP 404 |
| Root Cause | Backend route mismatch |
| Remediation | Correct Lambda environment variable |
| Recovery Response | HTTP 200 |
| Order Retrieved | 1001 |
| Lambda Code Changes | None |
| API Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved after recovery verification |

**Key Takeaway:** Effective API Gateway troubleshooting requires identifying whether failures originate in API routing, backend processing, application data, or authorization. Correcting the actual source avoids unnecessary infrastructure changes.

---

## Official AWS Documentation

- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [API Gateway Gateway Response Types](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)
- [API Gateway Lambda Proxy Integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [API Gateway Lambda Proxy Integration Using AWS CLI](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integration-using-cli.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [AWS CLI — Update Lambda Function Configuration](https://docs.aws.amazon.com/cli/latest/reference/lambda/update-function-configuration.html)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)