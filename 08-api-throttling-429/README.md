# Lab 08 — Amazon API Gateway Throttling: HTTP 429 Too Many Requests

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP **429 Too Many Requests** error caused by restrictive throttling settings in Amazon API Gateway.

In production, applications use API Gateway to receive requests from frontend applications, mobile clients, internal services, and business partners.

API Gateway provides throttling controls to help manage incoming traffic and protect backend infrastructure from excessive requests.

When request traffic exceeds the available throttling capacity, API Gateway can reject requests with:

```http
HTTP/2 429 Too Many Requests
```

Example response:

```json
{
  "message": "Too Many Requests"
}
```

In this lab, we create an Amazon API Gateway REST API exposing a `GET /orders` endpoint integrated with a Python AWS Lambda function.

We first deploy a working backend and verify that the endpoint returns HTTP 200.

Next, we intentionally misconfigure the API Gateway `dev` stage with highly restrictive throttling settings:

```text
Rate Limit  = 1 request/second
Burst Limit = 1 request
```

We then generate a small, bounded burst of requests using Python and curl.

Because the request volume exceeds the available throttling capacity, API Gateway begins returning HTTP 429 for some requests.

We investigate the incident using AWS CLI, curl, Python, API Gateway stage configuration, Lambda function health, CloudWatch Logs, and CloudWatch metrics.

After identifying the overly restrictive throttling settings as the root cause, we restore a more suitable example configuration:

```text
Rate Limit  = 20 requests/second
Burst Limit = 40 requests
```

We repeat the original tests, compare the results, and verify that the API returns HTTP 200 under normal request conditions.

We also implement a Python client using exponential backoff and jitter to demonstrate how applications should respond to temporary throttling.

Finally, we review production throttling, Cloud Security Engineering considerations, cost management, and resource cleanup.

### Troubleshooting Workflow

```text
Create IAM Execution Role
           |
           v
Create Python Lambda Backend
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
Grant Lambda Invocation Permission
           |
           v
Deploy API to dev Stage
           |
           v
Verify Healthy Baseline — HTTP 200
           |
           v
Inspect Stage Method Settings
           |
           v
Configure Restrictive Throttling
           |
           v
Rate Limit = 1 Request/Second
           |
           v
Burst Limit = 1
           |
           v
Generate Rapid Client Requests
           |
           v
API Gateway Applies Token Bucket
           |
           v
Some Requests Accepted
           |
           v
Some Requests Throttled
           |
           v
HTTP 429 Too Many Requests
           |
           v
Investigate API Gateway Stage
           |
           v
Verify Lambda Function Health
           |
           v
Inspect CloudWatch Logs and Metrics
           |
           v
Identify Restrictive Throttling
           |
           v
Restore Appropriate Stage Limits
           |
           v
Rate Limit = 20 Requests/Second
           |
           v
Burst Limit = 40
           |
           v
Repeat Original Request
           |
           v
Verify HTTP 200
           |
           v
Compare Bounded Burst Results
           |
           v
Implement Client Retry With Backoff
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-008 |
| Lab Name | API Throttling — HTTP 429 |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab08-throttling-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab08-order-handler` |
| Lambda Execution Role | `api-lab08-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Healthy HTTP Response | 200 |
| Broken HTTP Response | 429 |
| Broken Rate Limit | 1 request/second |
| Broken Burst Limit | 1 |
| Recovered Rate Limit | 20 requests/second |
| Recovered Burst Limit | 40 |
| Burst Test Size | 30 requests |
| Maximum Test Workers | 10 |
| API Gateway Metric | `4XXError` |
| Lambda Metric | `Invocations` |
| CloudWatch Log Marker | `LAB08_ORDER_SUCCESS` |
| Root Cause | Restrictive API Gateway stage throttling |
| Remediation | Adjust stage throttling settings |
| Client Improvement | Exponential backoff with jitter |
| API Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand HTTP 429 Too Many Requests.
- Understand API Gateway throttling.
- Understand token-bucket rate limiting.
- Distinguish request rate from burst capacity.
- Configure REST API stage throttling.
- Deploy a Python Lambda backend.
- Reproduce HTTP 429 errors.
- Generate bounded test traffic.
- Investigate API Gateway stage method settings.
- Inspect Lambda function health.
- Understand why throttled requests may not reach Lambda.
- Analyze CloudWatch API metrics.
- Compare API Gateway errors with Lambda invocations.
- Understand the difference between throttling and quotas.
- Apply targeted throttling remediation.
- Verify recovery without unnecessary API redeployment.
- Implement exponential backoff.
- Understand retry jitter.
- Avoid retry storms.
- Apply Cloud Security Engineering best practices.
- Control AWS lab costs.
- Clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application using Amazon API Gateway and AWS Lambda.

The application exposes:

```http
GET /dev/orders
```

The endpoint processes order retrieval requests from frontend applications and internal services.

Under normal conditions, the backend responds successfully:

```http
HTTP/2 200
```

Example response:

```json
{
  "message": "Orders retrieved successfully",
  "orders": [
    {
      "order_id": "1001",
      "status": "processing"
    },
    {
      "order_id": "1002",
      "status": "shipped"
    }
  ]
}
```

During an infrastructure configuration deployment, an engineer accidentally applies restrictive throttling settings to the API Gateway `dev` stage.

The configured rate is reduced to:

```text
1 request per second
```

The burst capacity is also reduced to:

```text
1 request
```

When multiple clients send requests at approximately the same time, API Gateway cannot accept all incoming requests within the configured throttling capacity.

Some requests succeed.

Other requests receive:

```http
HTTP/2 429 Too Many Requests
```

Response:

```json
{
  "message": "Too Many Requests"
}
```

The development team initially suspects that Lambda is overloaded.

However, the Cloud Engineering team investigates and discovers:

- The REST API is deployed.
- The GET method exists.
- Lambda proxy integration is correct.
- The Lambda function is Active.
- Individual requests can succeed.
- API Gateway stage throttling is extremely restrictive.
- HTTP 429 errors increase during request bursts.
- Requests throttled by API Gateway do not execute the Lambda handler.
- Changing stage throttling settings reduces the problem.

The engineer identifies the throttling configuration as the root cause.

After remediation, the API can handle a greater amount of test traffic.

### Incident Symptoms

- Some API requests return HTTP 200.
- Other requests return HTTP 429.
- Failures become more frequent during bursts.
- The Lambda function remains Active.
- Lambda logs show successful processing for accepted requests.
- Rejected requests may not appear in Lambda logs.
- API Gateway stage rate and burst limits are low.
- Increasing the limits reduces throttling under the test workload.

### Business Impact

Excessive API throttling may cause:

- Failed customer requests.
- Delayed order retrieval.
- Interrupted application workflows.
- Increased frontend errors.
- Failed service-to-service communication.
- Increased retry traffic.
- Customer-facing application failures.
- Reduced service reliability.
- Increased operational alerts.
- Potential retry storms.

### Objective

Identify whether HTTP 429 results from API Gateway throttling, usage plan limits, or excessive client traffic.

Apply an appropriate remediation and verify improved API availability without changing healthy backend application code.

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
                 REST API
                     |
                     v
                  dev Stage
                     |
                     v
               GET /orders
                     |
                     v
           Lambda Proxy Integration
                     |
                     v
                 AWS Lambda
                     |
                     v
              Python Order Handler
                     |
                     v
             LAB08_ORDER_SUCCESS
                     |
                     v
                 HTTP 200
```

### Broken Architecture

```text
                 API Clients
                     |
                     v
             Rapid Request Burst
                     |
                     v
              Amazon API Gateway
                     |
                     v
                  dev Stage
                     |
                     v
              Throttling Policy
                     |
             Rate Limit = 1/s
             Burst Limit = 1
                     |
              +------+------+
              |             |
              v             v
         Accepted       Throttled
              |             |
              v             v
          AWS Lambda     HTTP 429
              |             |
              v             v
          HTTP 200       Client Error
```

### Recovered Architecture

```text
                API Client
                    |
                    v
             Controlled Requests
                    |
                    v
             Amazon API Gateway
                    |
                    v
               dev Stage
                    |
                    v
           Corrected Throttling
                    |
             Rate Limit = 20/s
             Burst Limit = 40
                    |
                    v
          Lambda Proxy Integration
                    |
                    v
                AWS Lambda
                    |
                    v
             Orders Retrieved
                    |
                    v
                HTTP 200
```

### Client Retry Architecture

```text
               API Client
                   |
                   v
             Send GET Request
                   |
                   v
              API Gateway
                   |
             +-----+------+
             |            |
             v            v
          HTTP 200      HTTP 429
             |            |
             v            v
          Success     Calculate Backoff
                          |
                          v
                      Add Jitter
                          |
                          v
                       Wait
                          |
                          v
                 Retry Within Limit
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives API requests |
| REST API | Exposes order endpoint |
| GET /orders | Processes order retrieval |
| API Stage | Contains method settings |
| Throttling Rate | Controls target request rate |
| Burst Limit | Controls short-term capacity |
| Lambda Proxy Integration | Invokes Lambda |
| AWS Lambda | Processes accepted requests |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Allows API Gateway invocation |
| CloudWatch Logs | Records backend executions |
| API Gateway 4XXError | Tracks client-side errors |
| Lambda Invocations | Tracks Lambda executions |
| curl | Sends test requests |
| Python | Generates bounded traffic and implements retries |
| AWS CLI | Configures and investigates resources |

---

## 4. Understanding API Gateway Throttling

### What Is HTTP 429?

HTTP 429 Too Many Requests indicates that the client has sent more requests than the service is willing to accept within a period.

API Gateway can return this status when applicable throttling or usage limits are exceeded.

### What Is API Throttling?

Throttling limits the rate at which requests can access an API.

It helps protect backend services and manage available capacity.

API Gateway supports throttling at different levels, including account-level limits, stage or method settings, and usage plan limits where applicable.

### Understanding Rate Limits

The rate limit defines the target steady rate of requests.

Example:

```text
Rate Limit = 5 requests/second
```

This means the configured rate target is approximately five requests per second.

It is not a guarantee that every one-second interval will contain exactly five accepted requests.

### Understanding Burst Limits

The burst limit controls how much short-term request capacity may be available.

Example:

```text
Burst Limit = 10
```

A short burst can use available capacity before subsequent requests are throttled.

### Token-Bucket Model

API Gateway uses token-bucket-style throttling.

Conceptually:

```text
Incoming Requests
       |
       v
Available Tokens?
       |
   +---+---+
   |       |
   v       v
  Yes      No
   |       |
   v       v
Consume   HTTP 429
Token
   |
   v
Process Request
```

Tokens replenish according to the configured request rate.

The burst setting influences available short-term capacity.

### Rate Limit vs. Burst Limit

| Setting | Purpose |
|---|---|
| Rate limit | Controls sustained request rate |
| Burst limit | Allows short-term request spikes |
| HTTP 429 | Indicates throttling or applicable usage limit rejection |
| Lambda Invocations | Counts function invocations that reached Lambda |

### Important Production Distinction

API Gateway throttling settings are best-effort controls.

They are not hard guarantees about the exact number of requests accepted or rejected.

For this reason, the precise number of HTTP 429 responses may differ between test runs.

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
lambda:AddPermission
lambda:GetPolicy
lambda:ListTags
lambda:DeleteFunction

apigateway:POST
apigateway:GET
apigateway:PATCH
apigateway:DELETE

logs:DescribeLogGroups
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

### Safety Rules

- Use a dedicated REST API.
- Do not run the test against production APIs.
- Do not run unlimited request loops.
- Keep burst tests small and bounded.
- Avoid testing against unrelated endpoints.
- Do not modify account-wide throttling quotas.
- Do not modify production Lambda functions.
- Use fabricated order information.
- Avoid exposing AWS credentials.
- Verify project tags before cleanup.
- Delete temporary AWS resources after testing.

### Traffic Testing Limit

This lab uses:

```text
Total Requests = 30

Maximum Workers = 10
```

The Python test does not continuously generate traffic.

Production performance testing should follow approved load-testing procedures and appropriate traffic limits.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 08-api-throttling-429

cd 08-api-throttling-429
```

### Step 2 — Verify Tools

```bash
aws --version

python3 --version

curl --version

zip -v

jq --version

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

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab08"

export API_NAME="api-lab08-throttling-troubleshooting"

export FUNCTION_NAME="api-lab08-order-handler"

export ROLE_NAME="api-lab08-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab08"

export BROKEN_RATE="1"

export BROKEN_BURST="1"

export HEALTHY_RATE="20"

export HEALTHY_BURST="40"
```

### Step 4 — Create Local `.gitignore`

```bash
cat > .gitignore <<'EOF'
function.zip
lab08-resources.env
lab08-*.json
lab08-*.txt
*-headers.txt
*-response.json

__pycache__/
*.pyc

.env
.env.*
*.pem
*.key
EOF
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
  --query "items[?name=='${API_NAME}'].{Id:id,Name:name}" \
  --output table \
  --region "$AWS_REGION"
```

Do not overwrite unrelated resources.

---

## 7. Create Lambda Execution Role

### Step 1 — Create `lambda-trust-policy.json`

```bash
cat > lambda-trust-policy.json <<'EOF'
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
EOF
```

### Step 2 — Create IAM Role

```bash
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://lambda-trust-policy.json \
  --description "API Gateway Lab08 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach CloudWatch Logging Permissions

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

The Lambda execution role allows the function to write CloudWatch Logs.

It does not determine the API Gateway throttling limits.

---

## 8. Create Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ORDERS = [
    {
        "order_id": "1001",
        "status": "processing"
    },
    {
        "order_id": "1002",
        "status": "shipped"
    }
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
EOF
```

### Understanding the Application

The Lambda function returns fabricated order records.

It does not contain any intentional errors or delays.

When invoked successfully, it logs:

```text
LAB08_REQUEST method=GET path=/orders

LAB08_ORDER_SUCCESS count=2
```

The function returns a valid Lambda proxy response containing:

```text
statusCode = 200
```

This allows us to isolate the throttling problem at API Gateway rather than within the Lambda application.

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

## 9. Deploy Lambda Function

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
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

If Lambda cannot assume the newly created execution role immediately, retry after IAM role propagation.

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
```

### Step 4 — Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    State:State,
    Runtime:Runtime,
    Timeout:Timeout,
    MemorySize:MemorySize
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Timeout": 10,
  "MemorySize": 128
}
```

---

## 10. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab08 API Gateway throttling troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_ID"
```

### Step 2 — Retrieve Root Resource

```bash
export ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_ID"
```

### Step 3 — Create `/orders`

```bash
export RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id "$API_ID" \
  --parent-id "$ROOT_ID" \
  --path-part orders \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$RESOURCE_ID"
```

### Step 4 — Create GET Method

```bash
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --authorization-type NONE \
  --region "$AWS_REGION"
```

### Step 5 — Verify Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
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

## 11. Configure Lambda Proxy Integration

### Step 1 — Generate Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Create Lambda Proxy Integration

```bash
aws apigateway put-integration \
  --rest-api-id "$API_ID" \
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
  --rest-api-id "$API_ID" \
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
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/${STAGE_NAME}/GET/orders" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Lambda Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Confirm that API Gateway can invoke the intended Lambda function.

---

## 12. Deploy REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab08 initial healthy API deployment" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Generate API URL

```bash
export API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/orders"

echo "$API_URL"
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

### Step 4 — Save Resource Variables

```bash
cat > lab08-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export API_NAME="$API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export FUNCTION_ARN="$FUNCTION_ARN"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STAGE_NAME="$STAGE_NAME"
export PERMISSION_SID="$PERMISSION_SID"
export API_ID="$API_ID"
export ROOT_ID="$ROOT_ID"
export RESOURCE_ID="$RESOURCE_ID"
export API_URL="$API_URL"
export BROKEN_RATE="$BROKEN_RATE"
export BROKEN_BURST="$BROKEN_BURST"
export HEALTHY_RATE="$HEALTHY_RATE"
export HEALTHY_BURST="$HEALTHY_BURST"
EOF

chmod 600 lab08-resources.env
```

Restore variables when needed:

```bash
source lab08-resources.env
```

---

## 13. Verify Healthy Baseline

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
      "status": "processing"
    },
    {
      "order_id": "1002",
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

### Step 4 — Validate Response

```bash
python3 - <<'PY'
import json

with open("baseline-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: Healthy API baseline confirmed")
PY
```

### Step 5 — Verify Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected:

```text
LAB08_REQUEST method=GET path=/orders

LAB08_ORDER_SUCCESS count=2
```

The baseline confirms that the REST API, Lambda integration, and backend application are functional before the throttling incident is introduced.

---

## 14. Inspect API Gateway Stage Settings

### Step 1 — Inspect Current Stage Configuration

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --query '{
    Stage:stageName,
    DeploymentId:deploymentId,
    MethodSettings:methodSettings
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Method Settings

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --query 'methodSettings' \
  --output json \
  --region "$AWS_REGION"
```

Before explicit throttling configuration, the method settings may be empty or contain other defaults.

Example:

```json
{}
```

### Step 3 — Save Initial Stage Configuration

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --output json \
  --region "$AWS_REGION" \
  > lab08-initial-stage.json
```

### Understanding Stage Method Settings

API Gateway REST API stages support method-level configuration, including throttling.

A wildcard method setting can apply to methods within the selected stage.

The relevant settings are:

```text
throttlingRateLimit

throttlingBurstLimit
```

These values control the target throttling behavior for the stage.

---

## 15. Fault Injection — Configure Restrictive Throttling

### Step 1 — Configure Broken Stage Throttling

```bash
aws apigateway update-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --patch-operations \
    'op=replace,path=/*/*/throttling/rateLimit,value=1' \
    'op=replace,path=/*/*/throttling/burstLimit,value=1' \
  --region "$AWS_REGION"
```

This configures:

```text
Rate Limit = 1 request/second

Burst Limit = 1
```

The wildcard method-setting path applies to this REST API stage.

### Step 2 — Verify Broken Throttling Configuration

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --query 'methodSettings' \
  --output json \
  --region "$AWS_REGION"
```

Expected relevant configuration:

```json
{
  "*/*": {
    "throttlingBurstLimit": 1,
    "throttlingRateLimit": 1.0
  }
}
```

Additional properties may appear in the actual response.

### Step 3 — Save Broken Stage Evidence

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --output json \
  --region "$AWS_REGION" \
  > lab08-broken-stage.json
```

### Step 4 — Verify API Integration Is Unchanged

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Fault Injection Summary

| Component | State |
|---|---|
| REST API | Healthy |
| GET Method | Correct |
| Lambda Integration | Correct |
| Lambda Function | Active |
| Stage Rate Limit | 1 request/second |
| Stage Burst Limit | 1 |
| Expected Failure | HTTP 429 under bursts |
| Root Cause | Restrictive stage throttling |

---

## 16. Reproduce HTTP 429 Using curl

### Step 1 — Send Repeated Requests

Run:

```bash
for i in {1..10}; do
  echo -n "Request $i: "

  curl -sS \
    -o /dev/null \
    -w '%{http_code}\n' \
    "$API_URL"
done
```

Possible output:

```text
Request 1: 200
Request 2: 429
Request 3: 429
Request 4: 429
Request 5: 429
Request 6: 429
Request 7: 429
Request 8: 429
Request 9: 429
Request 10: 429
```

This output is illustrative.

The exact number of successful and throttled requests depends on request timing and API Gateway enforcement.

### Step 2 — Inspect an HTTP 429 Response

```bash
curl -i "$API_URL"
```

If the request is throttled:

```http
HTTP/2 429
```

Typical response:

```json
{
  "message": "Too Many Requests"
}
```

A single request may return HTTP 200 if sufficient throttling capacity is available.

### Step 3 — Save an Individual Response

```bash
curl -sS \
  -D broken-headers.txt \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

If it returns HTTP 429, the body may contain:

```json
{
  "message": "Too Many Requests"
}
```

### Step 4 — Inspect HTTP Headers

```bash
cat broken-headers.txt
```

Look for:

```text
HTTP Status

Content-Type

API Gateway request identifiers
```

Do not assume an HTTP 429 response will always include a `Retry-After` header.

---

## 17. Reproduce HTTP 429 Using Python

### Step 1 — Create `burst_test.py`

```bash
cat > burst_test.py <<'EOF'
import collections
import concurrent.futures
import os
import urllib.error
import urllib.request

API_URL = os.environ["API_URL"]

TOTAL_REQUESTS = 30
MAX_WORKERS = 10


def send_request(number):

    request = urllib.request.Request(
        API_URL,
        method="GET"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            return number, response.status

    except urllib.error.HTTPError as error:

        return number, error.code

    except Exception as error:

        return number, str(error)


with concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:

    results = list(
        executor.map(
            send_request,
            range(1, TOTAL_REQUESTS + 1)
        )
    )


counts = collections.Counter()

for number, status in results:

    print(
        f"Request {number:02d}: {status}"
    )

    counts[str(status)] += 1


print("\nSummary:")

for status, count in sorted(counts.items()):

    print(
        f"HTTP {status}: {count}"
    )
EOF
```

### Step 2 — Understand the Test Script

The script uses:

```text
TOTAL_REQUESTS = 30
```

and:

```text
MAX_WORKERS = 10
```

It sends a bounded number of requests with limited concurrency.

The test is intended to reproduce the throttling behavior.

It is not an unlimited load generator.

### Step 3 — Validate Script Syntax

```bash
python3 -m py_compile burst_test.py
```

### Step 4 — Run Burst Test

```bash
python3 burst_test.py
```

Possible summary:

```text
Summary:
HTTP 200: 3
HTTP 429: 27
```

The counts are examples rather than guaranteed outcomes.

### Step 5 — Save Broken Burst Results

To save the output during the test:

```bash
python3 burst_test.py | tee lab08-broken-burst-results.txt
```

If you already ran the test and captured sufficient evidence, there is no need to generate unnecessary additional requests.

### Step 6 — Inspect Results

```bash
cat lab08-broken-burst-results.txt
```

The key evidence is a combination of:

- HTTP 429 responses.
- Restrictive API Gateway stage settings.
- Healthy Lambda configuration.
- Successful HTTP 200 responses when requests are accepted.

---

## 18. Investigate API Gateway and Lambda

### Step 1 — Inspect REST API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].{Path:path,ID:id}' \
  --output table \
  --region "$AWS_REGION"
```

### Step 2 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 3 — Inspect Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

Expected:

```text
Type = AWS_PROXY

IntegrationMethod = POST
```

### Step 4 — Inspect Stage Throttling

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --query 'methodSettings' \
  --output json \
  --region "$AWS_REGION"
```

Expected broken values:

```text
throttlingRateLimit = 1

throttlingBurstLimit = 1
```

### Step 5 — Verify Lambda Function

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    State:State,
    Runtime:Runtime,
    LastUpdateStatus:LastUpdateStatus,
    Timeout:Timeout
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
State = Active

LastUpdateStatus = Successful
```

### Step 6 — Verify Lambda Invocation Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Investigation Summary

| Component | Finding |
|---|---|
| REST API | Exists |
| GET /orders | Correct |
| API Stage | Deployed |
| Lambda Integration | Correct |
| Lambda Permission | Correct |
| Lambda State | Active |
| Stage Rate Limit | Restrictive |
| Stage Burst Limit | Restrictive |
| HTTP Response Under Bursts | 429 |
| Root Cause | Stage throttling configuration |

---

## 19. Investigate CloudWatch Logs and Metrics

### Step 1 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected logs from accepted requests:

```text
LAB08_REQUEST method=GET path=/orders

LAB08_ORDER_SUCCESS count=2
```

Requests rejected at the API Gateway throttling layer do not execute the Lambda handler.

Therefore, an HTTP 429 response may not have a matching Lambda application log.

### Step 2 — Search for Successful Executions

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB08_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 3 — Save Lambda Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab08-cloudwatch-log-evidence.json
```

### Step 4 — Define Metric Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 5 — Inspect API Gateway 4XXError

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

Expected: API Gateway 4XX errors may increase because HTTP 429 responses are included in the 4XX category.

The `4XXError` metric does not distinguish throttling from every other possible 4XX response.

### Step 6 — Inspect API Gateway Request Count

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics SampleCount \
  --output json \
  --region "$AWS_REGION"
```

API Gateway's `Count` metric uses the `SampleCount` statistic to report request counts.

### Step 7 — Inspect Lambda Invocations

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

### Step 8 — Inspect Lambda Errors

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

### Step 9 — Save API Error Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab08-api-4xx-metric.json
```

### Step 10 — Save Lambda Invocation Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab08-lambda-invocations-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 4XXError | Increases with 429 responses |
| API Gateway Count | Records API traffic |
| Lambda Invocations | Reflects requests reaching Lambda |
| Lambda Errors | No runtime failure caused by API Gateway throttling |
| Lambda Logs | Successful requests appear |
| HTTP 429 | Generated before Lambda execution |

CloudWatch metrics may be delayed and aggregated.

Use HTTP response evidence and API Gateway configuration together with CloudWatch metrics.

---

## 20. Root Cause Analysis

### Root Cause

The API Gateway `dev` stage was configured with throttling limits too restrictive for the intended request pattern.

The rate limit was reduced to one request per second.

The burst limit was also reduced to one.

When multiple clients sent requests rapidly, API Gateway could not accept all requests under the configured throttle.

Some requests returned HTTP 429 before reaching Lambda.

The Lambda function remained healthy.

### Root Cause Diagram

```text
API Clients
      |
      v
Rapid GET Requests
      |
      v
Amazon API Gateway
      |
      v
dev Stage
      |
      v
Restrictive Throttling
      |
      v
Rate Limit = 1/s
Burst Limit = 1
      |
      v
Available Capacity Exceeded
      |
      v
Request Rejected
      |
      v
HTTP 429 Too Many Requests
      |
      v
Lambda Handler Not Executed
```

### Five Whys

**Why 1 — Why did the API return HTTP 429?**

API Gateway throttled incoming requests.

**Why 2 — Why were requests throttled?**

The request rate exceeded the available throttling capacity.

**Why 3 — Why was the throttling capacity insufficient?**

The rate and burst limits were configured too restrictively for the test workload.

**Why 4 — Why were the limits configured incorrectly?**

The simulated infrastructure configuration applied values that did not match expected traffic requirements.

**Why 5 — How can the incident be prevented?**

Use reviewed Infrastructure as Code, traffic baseline measurements, bounded load tests, CloudWatch monitoring, and approved capacity planning.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-008 |
| HTTP Error | 429 |
| Error Message | Too Many Requests |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Broken Rate | 1 request/second |
| Broken Burst | 1 |
| Lambda State | Active |
| Lambda Integration | Correct |
| Root Cause | Restrictive stage throttling |
| Remediation | Adjust rate and burst settings |
| Lambda Code Changes | None |
| API Redeployment | Not required |

---

## 21. Remediation — Restore Throttling Configuration

### Step 1 — Restore Example Rate and Burst Limits

```bash
aws apigateway update-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --patch-operations \
    'op=replace,path=/*/*/throttling/rateLimit,value=20' \
    'op=replace,path=/*/*/throttling/burstLimit,value=40' \
  --region "$AWS_REGION"
```

This changes the stage settings to:

```text
Rate Limit = 20 requests/second

Burst Limit = 40
```

These values are suitable for demonstrating a recovery, not automatic production recommendations.

### Step 2 — Verify Recovered Configuration

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --query 'methodSettings' \
  --output json \
  --region "$AWS_REGION"
```

Expected relevant configuration:

```json
{
  "*/*": {
    "throttlingBurstLimit": 40,
    "throttlingRateLimit": 20.0
  }
}
```

### Step 3 — Save Recovered Stage Configuration

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --output json \
  --region "$AWS_REGION" \
  > lab08-recovered-stage.json
```

### Step 4 — Verify Lambda Remains Unchanged

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime}' \
  --output json \
  --region "$AWS_REGION"
```

### Why API Gateway Redeployment Is Not Required

The following configurations remain unchanged:

```text
REST API
GET /orders
Lambda Integration
Lambda Function
Deployment Stage
```

Only stage method throttling settings are updated.

The `update-stage` operation changes the relevant stage configuration directly.

A new API Gateway deployment is not normally required for this change.

---

## 22. Verify Successful Recovery

### Step 1 — Repeat Original GET Request

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
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: API response verified")
PY
```

### Step 4 — Repeat Bounded Burst Test

```bash
python3 burst_test.py | tee lab08-recovered-burst-results.txt
```

Expected: under the restored configuration, fewer requests should be throttled than under the restrictive configuration, although exact results depend on timing and service behavior.

### Step 5 — Compare Results

```bash
cat lab08-broken-burst-results.txt
```

```bash
cat lab08-recovered-burst-results.txt
```

Example comparison:

| Status | Broken Example | Recovered Example |
|---|---:|---:|
| HTTP 200 | 3 | 30 |
| HTTP 429 | 27 | 0 |
| Total | 30 | 30 |

These numbers illustrate the expected improvement; they are not guaranteed or measured results from your AWS account.

### Step 6 — Verify CloudWatch Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected successful application marker:

```text
LAB08_ORDER_SUCCESS count=2
```

### Step 7 — Save Recovery Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB08_ORDER_SUCCESS"' \
  --output json \
  --region "$AWS_REGION" \
  > lab08-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Healthy | Healthy |
| Lambda Function | Healthy | Healthy |
| Lambda Integration | Correct | Correct |
| Stage Rate | 1 req/s | 20 req/s |
| Stage Burst | 1 | 40 |
| Rapid Requests | High throttling likelihood | Lower throttling likelihood |
| API Response | HTTP 429 under bursts | HTTP 200 expected for normal requests |
| Lambda Code | Unchanged | Unchanged |
| API Deployment | Unchanged | Unchanged |

**Recovery is verified when the stage settings are corrected, ordinary requests return HTTP 200, and the bounded test shows improved acceptance under the target workload.**

---

## 23. Production Client Retry — Exponential Backoff With Jitter

### Why Client Retries Matter

A temporary HTTP 429 response may occur during a legitimate traffic spike.

Clients should not immediately retry requests repeatedly without delay.

Uncontrolled retries can make throttling worse.

A safer strategy uses:

```text
Bounded Attempts
        |
        v
Exponential Backoff
        |
        v
Random Jitter
        |
        v
Retry Only Appropriate Errors
```

### Step 1 — Create `retry_client.py`

```bash
cat > retry_client.py <<'EOF'
import json
import os
import random
import time
import urllib.error
import urllib.request

API_URL = os.environ["API_URL"]

MAX_ATTEMPTS = 5
BASE_DELAY = 0.5
MAX_DELAY = 8.0


for attempt in range(MAX_ATTEMPTS):

    try:

        request = urllib.request.Request(
            API_URL,
            method="GET"
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            body = json.loads(
                response.read()
            )

            print(
                "HTTP Status:",
                response.status
            )

            print(
                json.dumps(
                    body,
                    indent=2
                )
            )

            break

    except urllib.error.HTTPError as error:

        print(
            "HTTP Status:",
            error.code
        )

        if error.code != 429:
            raise

        if attempt == MAX_ATTEMPTS - 1:

            print(
                "Maximum retries reached"
            )

            break

        delay_cap = min(
            MAX_DELAY,
            BASE_DELAY * (2 ** attempt)
        )

        delay = random.uniform(
            0,
            delay_cap
        )

        print(
            f"Retrying after {delay:.2f} seconds"
        )

        time.sleep(delay)
EOF
```

### Step 2 — Validate Script

```bash
python3 -m py_compile retry_client.py
```

### Step 3 — Run Retry Client

```bash
python3 retry_client.py
```

Expected normal result:

```text
HTTP Status: 200
```

If a temporary HTTP 429 occurs, the client delays the retry.

### Step 4 — Understand Exponential Backoff

The upper delay bound increases with each retry.

Example:

```text
Attempt 1: Up to 0.5 seconds

Attempt 2: Up to 1 second

Attempt 3: Up to 2 seconds

Attempt 4: Up to 4 seconds
```

The script randomly selects a delay within the allowed range.

### Why Jitter Matters

If many clients retry at exactly the same time, they can create another traffic spike.

Jitter spreads retry attempts over time.

### Production Recommendations

- Limit the total number of retries.
- Use exponential backoff.
- Add jitter.
- Honor `Retry-After` when provided and appropriate.
- Apply client-side rate limiting.
- Use idempotency safeguards for operations that modify data.
- Monitor retry attempts and failures.
- Avoid unlimited retries.

---

## 24. Additional Production Troubleshooting Scenarios

### Scenario 1 — API Gateway Account-Level Throttling

API Gateway applies service-level throttling limits at the AWS account and Region level.

A client may receive HTTP 429 even when stage settings appear reasonable.

**Investigation:** Review account-level limits and other traffic sharing those limits.

### Scenario 2 — Usage Plan Throttling

An API method requiring an API key can be subject to usage plan throttling.

Inspect:

```bash
aws apigateway get-usage-plan \
  --usage-plan-id USAGE_PLAN_ID
```

A usage plan rate or burst limit may be more restrictive than expected.

This lab uses stage throttling rather than a usage plan.

### Scenario 3 — Usage Plan Quota Exceeded

An API key may exceed an applicable usage plan quota.

Possible result:

```http
HTTP/2 429
```

**Investigation:** Inspect usage plan quotas and consumption.

### Scenario 4 — Excessive Client Retries

Clients may retry failed requests too aggressively.

This can increase traffic and cause additional throttling.

**Remediation:** Implement bounded exponential backoff with jitter.

### Scenario 5 — Unexpected Traffic Spike

Traffic may increase suddenly due to:

- Marketing campaigns.
- Application releases.
- Batch jobs.
- Scheduled integrations.
- Misconfigured polling.
- Abuse or automated traffic.

**Investigation:** Compare request rates, API Gateway metrics, client logs, and traffic patterns.

### Scenario 6 — Lambda Concurrency Throttling

Lambda has its own concurrency controls.

Lambda concurrency throttling is different from API Gateway stage throttling.

**Investigation:**

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

Do not assume every API Gateway HTTP 429 originates from Lambda concurrency limits.

### Scenario 7 — AWS WAF Rate-Based Rules

If AWS WAF is associated with the API, rate-based rules may reject traffic.

The response behavior depends on the configured WAF action and custom responses.

**Investigation:** Inspect the associated web ACL and WAF metrics.

### Common Troubleshooting Comparison

| Symptom | Possible Cause | Investigation |
|---|---|---|
| HTTP 429 during bursts | Stage throttling | Stage method settings |
| HTTP 429 for one API key | Usage plan limits | API key usage plan |
| HTTP 429 after excessive usage | Quota exceeded | Usage plan quota |
| HTTP 429 across multiple APIs | Account-level limits | Account traffic and quotas |
| Lambda Throttles increases | Lambda concurrency limit | Lambda metrics |
| Increasing retries worsen failures | Retry storm | Client retry configuration |
| Traffic spike after deployment | New application behavior | Request metrics and client logs |

---

## 25. Cloud Security Engineering Considerations

### Throttling Is a Reliability and Security Control

Throttling can help limit excessive request traffic and protect backend capacity.

However, it should not be treated as a complete denial-of-service defense.

### Do Not Disable Throttling Without Investigation

Removing throttling entirely may expose a backend to unexpected traffic and higher costs.

Investigate normal traffic patterns and backend capacity before increasing limits.

### IAM Least Privilege

Restrict which AWS identities can modify API Gateway stage settings.

Production engineers should avoid granting broad API Gateway management permissions unnecessarily.

### Monitor Unexpected Configuration Changes

A sudden reduction or increase in throttling limits may be caused by:

- Infrastructure as Code changes.
- Manual configuration.
- CI/CD deployment errors.
- Incorrect environment variables.
- Unauthorized changes.

CloudTrail can help investigate management events.

### Protect Backend Capacity

Monitor:

```text
API Gateway Count

API Gateway 4XXError

API Gateway 5XXError

Lambda Invocations

Lambda Errors

Lambda Duration

Lambda ConcurrentExecutions

Lambda Throttles
```

### AWS WAF

For appropriate public APIs, consider AWS WAF rate-based rules as an additional control against abusive traffic.

### Retry Storm Prevention

Use bounded retries and jitter.

Avoid clients that continually retry HTTP 429 without delay.

### Configuration Management

Manage stage throttling through reviewed Terraform or CloudFormation configuration.

Validate changes before applying them to production.

### Security Principle

**Throttle limits should protect backend resources without unnecessarily rejecting legitimate traffic.**

---

## 26. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Request charges |
| AWS Lambda | Invocation and execution charges |
| CloudWatch Logs | Log ingestion and storage |
| CloudWatch Metrics | Applicable monitoring charges |
| IAM | No separate standard role charge |

### Cost Optimization

- Use temporary lab resources.
- Limit burst tests to 30 requests.
- Avoid unlimited load generation.
- Keep Lambda memory at 128 MB.
- Do not create unnecessary infrastructure.
- Delete all lab resources after testing.
- Monitor API request counts.
- Avoid retry loops that generate excessive API calls.

### Important Cost Consideration

Throttling helps manage traffic, but it should not be considered a guaranteed AWS spending limit.

Use AWS Budgets and appropriate monitoring for financial controls.

### Services Not Required

```text
EC2

RDS

NAT Gateway

Application Load Balancer

VPC Endpoints
```

This lab uses a lightweight serverless architecture.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only resources created for Lab 08.

### Step 1 — Verify API Gateway Tags

```bash
aws apigateway get-tags \
  --resource-arn "arn:aws:apigateway:${AWS_REGION}::/restapis/${API_ID}" \
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
Project = API-Gateway-Troubleshooting-Lab08
```

### Step 4 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

The stage and its throttling configuration are removed with the REST API.

### Step 5 — Delete Lambda Function

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 6 — Detach IAM Logging Policy

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

If the log group does not exist, AWS may return `ResourceNotFoundException`.

### Step 9 — Verify REST API Deletion

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
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
| API stage | Deleted |
| Stage throttling | Removed with stage |
| API resources and methods | Deleted |
| Lambda integration | Deleted |
| Lambda function | Deleted |
| Lambda invocation permission | Removed with function |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |

---

## 28. Interview Questions and Answers

### Q1. What does HTTP 429 mean?

HTTP 429 Too Many Requests indicates that the service is rejecting requests because an applicable request rate or usage limit has been exceeded.

### Q2. What caused HTTP 429 in this lab?

The API Gateway stage was configured with restrictive throttling settings: one request per second and a burst limit of one.

### Q3. What is API Gateway throttling?

It is a mechanism for controlling request rates and protecting API integrations from excessive incoming traffic.

### Q4. What is the difference between rate limit and burst limit?

The rate limit controls the target sustained request rate. The burst limit allows short-term request spikes using available token-bucket capacity.

### Q5. What is the token-bucket algorithm?

It is a rate-limiting approach in which requests consume available tokens, and tokens replenish over time. Requests may be throttled when insufficient capacity remains.

### Q6. Why might Lambda remain healthy while API Gateway returns HTTP 429?

API Gateway can throttle requests before invoking Lambda.

### Q7. How do you inspect API Gateway stage throttling?

Use:

```bash
aws apigateway get-stage \
  --rest-api-id REST_API_ID \
  --stage-name dev \
  --query 'methodSettings'
```

### Q8. How do you change API Gateway throttling settings?

Use the AWS CLI `update-stage` command with the appropriate throttling patch operations.

### Q9. Why didn't this remediation require API redeployment?

We modified stage method settings rather than changing API resources, methods, or integrations.

### Q10. How do you distinguish API Gateway throttling from Lambda throttling?

Inspect the API Gateway throttle configuration, HTTP response status, CloudWatch API metrics, Lambda invocation metrics, and Lambda Throttles metric.

### Q11. Which CloudWatch metric tracks API Gateway client errors?

The `4XXError` metric tracks API Gateway client-side HTTP errors, including HTTP 429.

### Q12. Does the API Gateway 4XXError metric identify HTTP 429 separately?

Not by itself. It aggregates 4XX errors, so additional request-level evidence is needed.

### Q13. What is exponential backoff?

A retry strategy that increases the waiting period after repeated failures.

### Q14. Why is jitter useful?

It adds randomness to retry delays and helps prevent many clients from retrying simultaneously.

### Q15. Should engineers always increase throttling limits when HTTP 429 occurs?

No. The traffic might be excessive or abusive, and the existing limits might be appropriate. Engineers should investigate normal workloads and backend capacity first.

### Q16. Are API Gateway throttling settings guaranteed hard limits?

No. AWS describes these limits as best-effort controls.

### Q17. How can throttling affect AWS costs?

Higher accepted request volumes can increase API Gateway, Lambda, and related service usage charges.

### Q18. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

The API exposed a GET endpoint that returned order information.

I first verified that the endpoint returned HTTP 200.

Next, I intentionally configured restrictive stage throttling with a rate limit of one request per second and a burst limit of one.

I generated a bounded burst of API requests using curl and Python.

Some requests succeeded, while others returned HTTP 429 Too Many Requests.

I investigated the REST API stage configuration, Lambda integration, Lambda function state, CloudWatch Logs, and CloudWatch metrics.

The investigation confirmed that API Gateway was rejecting requests before they reached Lambda.

The root cause was an overly restrictive stage throttling configuration.

I restored example limits of 20 requests per second and a burst limit of 40.

I then repeated the requests and verified that normal requests returned HTTP 200 with improved burst acceptance.

I also implemented a Python retry client using exponential backoff and jitter.

Finally, I reviewed production security practices and removed the temporary AWS resources.

---

## 29. Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-api-returns-403/
│
├── 02-api-returns-404/
│
├── 03-api-returns-500/
│
├── 04-api-gateway-lambda-integration-failure/
│
├── 05-cors-error/
│
├── 06-missing-authorization-token/
│
├── 07-api-key-usage-plan-misconfiguration/
│
├── 08-api-throttling-429/
│   ├── README.md
│   ├── .gitignore
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── burst_test.py
│   ├── retry_client.py
│   ├── function.zip
│   ├── lab08-resources.env
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab08-initial-stage.json
│   ├── lab08-broken-stage.json
│   ├── lab08-recovered-stage.json
│   ├── lab08-broken-burst-results.txt
│   ├── lab08-recovered-burst-results.txt
│   ├── lab08-cloudwatch-log-evidence.json
│   ├── lab08-recovered-cloudwatch-evidence.json
│   ├── lab08-api-4xx-metric.json
│   └── lab08-lambda-invocations-metric.json
│
├── 09-api-timeout-504/
│
└── 10-custom-domain-certificate-failure/
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Incident documentation and remediation |
| .gitignore | Excludes local evidence and generated files |
| lambda_function.py | Python orders API backend |
| lambda-trust-policy.json | Lambda IAM trust policy |
| burst_test.py | Bounded concurrent request generator |
| retry_client.py | Client with exponential backoff and jitter |
| function.zip | Generated Lambda deployment package |
| lab08-resources.env | Local AWS resource variables |
| baseline-headers.txt | Healthy HTTP headers |
| baseline-response.json | Healthy API response |
| broken-headers.txt | HTTP response under restrictive throttling |
| broken-response.json | Response body captured during fault injection |
| recovered-headers.txt | Recovered HTTP headers |
| recovered-response.json | Recovered order response |
| lab08-initial-stage.json | Original stage configuration |
| lab08-broken-stage.json | Restrictive throttle configuration |
| lab08-recovered-stage.json | Corrected throttle configuration |
| lab08-broken-burst-results.txt | Requests accepted and rejected before remediation |
| lab08-recovered-burst-results.txt | Requests accepted and rejected after remediation |
| lab08-cloudwatch-log-evidence.json | Lambda execution evidence |
| lab08-recovered-cloudwatch-evidence.json | Successful backend logs after recovery |
| lab08-api-4xx-metric.json | API Gateway 4XX metrics |
| lab08-lambda-invocations-metric.json | Lambda invocation metrics |

### Recommended Public GitHub Files

```text
08-api-throttling-429/
├── README.md
├── .gitignore
├── lambda_function.py
├── lambda-trust-policy.json
├── burst_test.py
└── retry_client.py
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 08
08-api-throttling-429/function.zip
08-api-throttling-429/lab08-resources.env
08-api-throttling-429/lab08-*.json
08-api-throttling-429/lab08-*.txt
08-api-throttling-429/*-headers.txt
08-api-throttling-429/*-response.json

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

This lab demonstrates how an Amazon API Gateway REST API can return HTTP 429 when throttling settings are too restrictive.

We created a REST API integrated with a Python Lambda backend.

We first verified that the endpoint returned HTTP 200 and retrieved order information.

Next, we intentionally configured a rate limit of one request per second and a burst limit of one.

We generated a bounded burst of requests using curl and Python.

API Gateway rejected some requests with HTTP 429 while accepting others.

We investigated the API Gateway stage configuration, Lambda function state, integration settings, CloudWatch Logs, and CloudWatch metrics.

The investigation showed that the throttling failure originated in API Gateway rather than the Lambda application.

We restored the stage throttling settings to a rate limit of 20 requests per second and a burst limit of 40.

After remediation, normal requests returned HTTP 200, and the bounded request test was used to compare behavior before and after the configuration change.

We also implemented a retry client using exponential backoff and jitter.

The Lambda application code and REST API deployment did not require changes.

Finally, the lab documented security considerations, cost management, and temporary AWS resource cleanup.

**Key Lesson:** HTTP 429 errors may originate from API Gateway throttling before requests reach the Lambda backend. Engineers must inspect the throttle configuration, request patterns, and service metrics before deciding whether to adjust limits or client behavior.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 429 troubleshooting
- API Gateway stage throttling
- Token-bucket rate limiting
- Request rate and burst limits
- AWS Lambda proxy integration
- Python 3.13
- Concurrent API testing
- Bounded request generation
- Exponential backoff
- Retry jitter
- AWS IAM execution roles
- Lambda invocation permissions
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch API metrics
- Lambda invocation metrics
- Root cause analysis
- Stage configuration remediation
- Recovery verification
- Production reliability engineering
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-008 |
| Scenario | API Throttling — HTTP 429 |
| REST API | api-lab08-throttling-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab08-order-handler |
| Broken Rate | 1 req/s |
| Broken Burst | 1 |
| Broken Response | HTTP 429 under burst traffic |
| Root Cause | Restrictive stage throttling |
| Recovered Rate | 20 req/s |
| Recovered Burst | 40 |
| Recovery Response | HTTP 200 for normal requests |
| Client Retry | Exponential backoff with jitter |
| Lambda Code Changes | None |
| API Gateway Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Effective API Gateway throttling troubleshooting requires understanding rate limits, burst capacity, request patterns, Lambda execution behavior, CloudWatch metrics, and safe client retry strategies.

---

## Official AWS Documentation

- [Amazon API Gateway — Throttle Requests to REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [Amazon API Gateway — Patch Operations](https://docs.aws.amazon.com/apigateway/latest/api/patch-operations.html)
- [Amazon API Gateway — Stage Settings](https://docs.aws.amazon.com/apigateway/latest/developerguide/stage-settings.html)
- [Amazon API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [Amazon API Gateway — Usage Plans and API Keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [AWS Lambda — Monitoring Metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [AWS CLI — Update Stage](https://docs.aws.amazon.com/cli/latest/reference/apigateway/update-stage.html)
- [AWS CLI — Get Stage](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-stage.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [AWS Builders Library — Timeouts, Retries, and Backoff With Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)