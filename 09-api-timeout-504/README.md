# Lab 09 — Amazon API Gateway Timeout: HTTP 504 Gateway Timeout

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP **504 Gateway Timeout** error caused by an Amazon API Gateway integration timeout.

In production, API Gateway often serves as the entry point for applications that communicate with AWS Lambda, databases, and other backend services.

When a backend takes longer than the configured integration timeout, API Gateway can stop waiting for the response and return:

```http
HTTP/2 504 Gateway Timeout
```

Example response:

```json
{
  "message": "Endpoint request timed out"
}
```

A timeout does not necessarily mean the backend application has crashed or that the Lambda function has reached its own execution timeout.

An API Gateway integration timeout and a Lambda function timeout are separate configurations.

In this lab, we create an Amazon API Gateway REST API exposing a `GET /orders` endpoint integrated with a Python Lambda function.

We first deploy a healthy backend with an artificial processing delay of zero seconds and verify HTTP 200.

Next, we deliberately configure the Lambda function to wait four seconds before returning its response.

With the original 10-second API Gateway integration timeout, the slow backend can still complete successfully.

We then reduce the API Gateway integration timeout to 1,500 milliseconds.

Because the backend requires approximately four seconds, API Gateway stops waiting and returns HTTP 504.

We investigate the failure using AWS CLI, curl response timing, API Gateway integration settings, Lambda configuration, CloudWatch Logs, and CloudWatch metrics.

The investigation reveals that Lambda may complete successfully even after API Gateway has returned HTTP 504 to the client.

We remediate the incident by removing the unnecessary backend delay and restoring a suitable API Gateway integration timeout.

After redeployment, the endpoint returns HTTP 200.

Finally, we review timeout boundaries, asynchronous architecture, production security considerations, cost management, and cleanup.

### Troubleshooting Workflow

```text
Create IAM Execution Role
           |
           v
Create Python Lambda Backend
           |
           v
Configure DELAY_SECONDS=0
           |
           v
Deploy Lambda Function
           |
           v
Configure Lambda Timeout = 15 Seconds
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
Set Integration Timeout = 10 Seconds
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
Introduce Slow Backend
           |
           v
Set DELAY_SECONDS=4
           |
           v
Verify Slow Backend Still Returns HTTP 200
           |
           v
Reduce Integration Timeout to 1.5 Seconds
           |
           v
Redeploy REST API
           |
           v
Send GET /dev/orders
           |
           v
Lambda Processes for 4 Seconds
           |
           v
API Gateway Waits Only 1.5 Seconds
           |
           v
HTTP 504 Gateway Timeout
           |
           v
Investigate API Gateway Integration
           |
           v
Inspect Lambda Configuration
           |
           v
Inspect CloudWatch Logs and Metrics
           |
           v
Compare Gateway Timeout and Backend Duration
           |
           v
Identify Root Cause
           |
           v
Remove Artificial Backend Delay
           |
           v
Restore Integration Timeout to 10 Seconds
           |
           v
Redeploy REST API
           |
           v
Verify HTTP 200
           |
           v
Confirm Lambda Recovery
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-009 |
| Lab Name | API Gateway Timeout — HTTP 504 |
| Difficulty | Intermediate–Advanced |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab09-timeout-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration Type | AWS_PROXY |
| Lambda Function | `api-lab09-order-handler` |
| Lambda Execution Role | `api-lab09-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Execution Timeout | 15 seconds |
| Initial Lambda Delay | 0 seconds |
| Broken Lambda Delay | 4 seconds |
| Initial Integration Timeout | 10,000 milliseconds |
| Broken Integration Timeout | 1,500 milliseconds |
| Recovered Integration Timeout | 10,000 milliseconds |
| Healthy HTTP Response | 200 |
| Broken HTTP Response | 504 |
| CloudWatch API Metric | `5XXError` |
| CloudWatch Latency Metric | `IntegrationLatency` |
| Lambda Metrics | `Duration`, `Errors`, `Invocations` |
| Lambda Log Marker | `LAB09_REQUEST_COMPLETED` |
| Root Cause | Backend processing exceeds integration timeout |
| Primary Remediation | Optimize backend processing |
| Additional Remediation | Restore integration timeout |
| Lambda Code Changes | Not required |
| Lambda Configuration Changes | Required |
| API Gateway Redeployment | Required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand HTTP 504 Gateway Timeout.
- Understand API Gateway integration timeouts.
- Understand Lambda execution timeouts.
- Distinguish API Gateway and Lambda timeout behavior.
- Deploy an API Gateway REST API.
- Configure Lambda proxy integration.
- Configure the `timeoutInMillis` property.
- Use Lambda environment variables.
- Simulate slow backend processing.
- Reproduce HTTP 504.
- Measure client response latency.
- Investigate API Gateway integration settings.
- Inspect Lambda function configuration.
- Investigate CloudWatch Logs.
- Analyze IntegrationLatency and Lambda Duration.
- Understand why Lambda may finish after a gateway timeout.
- Perform root cause analysis.
- Remediate backend latency.
- Restore appropriate integration timeouts.
- Understand when API redeployment is required.
- Design safer asynchronous workflows.
- Apply Cloud Security Engineering practices.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management platform that uses Amazon API Gateway and AWS Lambda.

The application exposes:

```http
GET /dev/orders
```

The Lambda function retrieves order information and returns JSON.

Under normal conditions, the application responds quickly:

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

During a backend deployment, a new processing operation causes Lambda execution to take approximately four seconds.

The API Gateway integration is also configured with a timeout of only 1.5 seconds.

Customers begin receiving:

```http
HTTP/2 504 Gateway Timeout
```

The application reports that requests are failing even though Lambda is still processing them.

The Cloud Engineering team investigates.

The engineer verifies:

- The REST API exists.
- The `dev` stage is deployed.
- The GET method is correctly configured.
- Lambda proxy integration is correct.
- API Gateway has permission to invoke Lambda.
- Lambda remains Active.
- The Lambda timeout is 15 seconds.
- The Lambda function requires approximately four seconds.
- The API Gateway integration timeout is only 1.5 seconds.
- API Gateway returns HTTP 504 before Lambda finishes.

The team identifies a mismatch between backend processing duration and integration timeout.

After optimizing the backend and correcting the timeout configuration, the API returns HTTP 200.

### Incident Symptoms

- API Gateway returns HTTP 504.
- Requests take approximately 1.5 seconds before failing.
- Lambda remains Active.
- Lambda may finish its execution successfully.
- Lambda Duration is approximately four seconds.
- API Gateway integration timeout is 1.5 seconds.
- API Gateway 5XXError increases.
- Backend execution continues beyond the client-facing timeout.
- Correcting latency and timeout settings restores the endpoint.

### Business Impact

Integration timeouts may cause:

- Failed customer requests.
- Interrupted order-management workflows.
- Delayed API responses.
- Failed frontend operations.
- Increased 5XX error rates.
- Unnecessary client retries.
- Duplicate processing risks.
- Increased Lambda execution costs.
- Reduced service reliability.
- Customer-facing application outages.

### Objective

Identify which timeout boundary is responsible for HTTP 504 and determine whether the backend or API Gateway configuration should be changed.

Restore successful API responses while maintaining appropriate performance, reliability, and security controls.

---

## 3. AWS Architecture

### Healthy Baseline Architecture

```text
                   API Client
                       |
                       v
                 GET /dev/orders
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
               AWS_PROXY Integration
                       |
             Timeout = 10 Seconds
                       |
                       v
                    Lambda
                       |
              DELAY_SECONDS=0
                       |
                       v
               Python Order Handler
                       |
                       v
                JSON Order Response
                       |
                       v
                    HTTP 200
```

### Broken Architecture

```text
                   API Client
                       |
                       v
                 GET /dev/orders
                       |
                       v
                Amazon API Gateway
                       |
                       v
                Lambda Integration
                       |
               Timeout = 1.5 Seconds
                       |
                       v
                    Lambda
                       |
                DELAY_SECONDS=4
                       |
                       v
                Slow Processing
                       |
                       |
             +---------+----------+
             |                    |
             v                    v
      API Gateway Stops      Lambda Continues
           Waiting              Processing
             |                    |
             v                    v
          HTTP 504           Completes Around
                              4 Seconds
```

### Recovered Architecture

```text
                   API Client
                       |
                       v
                 GET /dev/orders
                       |
                       v
                Amazon API Gateway
                       |
                       v
                GET /orders
                       |
                       v
                Lambda Integration
                       |
              Timeout = 10 Seconds
                       |
                       v
                    Lambda
                       |
              DELAY_SECONDS=0
                       |
                       v
              Immediate Processing
                       |
                       v
                JSON Response
                       |
                       v
                  HTTP 200 OK
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives HTTP requests |
| REST API | Defines the API endpoint |
| GET /orders | Retrieves order information |
| API Stage | Hosts deployed API configuration |
| Lambda Proxy Integration | Invokes the backend |
| Integration Timeout | Limits how long API Gateway waits |
| AWS Lambda | Processes requests |
| Lambda Timeout | Limits function execution duration |
| Lambda Environment Variable | Controls artificial delay |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Authorizes API Gateway invocation |
| CloudWatch Logs | Records backend execution |
| CloudWatch Metrics | Measures errors and latency |
| curl | Measures HTTP status and response time |
| AWS CLI | Configures and investigates AWS services |

---

## 4. Understanding HTTP 504 and Timeouts

### What Is HTTP 504?

HTTP 504 Gateway Timeout indicates that a gateway or proxy did not receive a timely response from its upstream server.

For this lab, API Gateway cannot obtain the Lambda integration response before the configured integration timeout expires.

### What Is an API Gateway Integration Timeout?

The integration timeout controls how long API Gateway waits for the backend integration to respond.

Example:

```text
timeoutInMillis = 1500
```

This represents 1,500 milliseconds, or 1.5 seconds.

If the integration does not respond in time, API Gateway can return HTTP 504.

### What Is a Lambda Function Timeout?

The Lambda function timeout controls the maximum duration of a Lambda invocation.

Example:

```text
Lambda Timeout = 15 Seconds
```

This allows the function to execute for up to 15 seconds before Lambda terminates it for reaching the configured limit.

### Timeout Comparison

| Timeout | Purpose |
|---|---|
| API Gateway Integration Timeout | Maximum time API Gateway waits for backend integration |
| Lambda Function Timeout | Maximum time Lambda permits function execution |
| Client Timeout | Maximum time the calling client waits |
| Downstream Service Timeout | Maximum wait for database or external dependency |

### Example

```text
API Gateway Timeout = 1.5 Seconds

Lambda Processing = 4 Seconds

Lambda Timeout = 15 Seconds
```

Result:

```text
API Gateway Returns HTTP 504

Lambda May Continue Processing
```

### Why This Matters

A backend operation may complete after the client has already received a timeout response.

For operations such as payments, order creation, and database writes, this can create duplicate-processing risks if the client retries without idempotency protection.

### HTTP 500 vs. 502 vs. 504

| Status | Typical Meaning |
|---|---|
| 500 | Internal server or integration configuration error |
| 502 | Bad gateway or invalid backend response |
| 504 | Gateway waited too long for the integration |
| 429 | Request rate or usage limit exceeded |

The actual status depends on the integration and failure conditions.

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
apigateway:PATCH
apigateway:DELETE

logs:DescribeLogGroups
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

### Safety Rules

- Use a dedicated REST API.
- Do not modify production integrations.
- Do not introduce delays into production Lambda functions.
- Do not connect this lab to production databases.
- Use fabricated order information.
- Keep testing limited to a few requests.
- Avoid unnecessary long-running Lambda execution.
- Do not expose AWS credentials.
- Review troubleshooting evidence before publishing.
- Verify project tags before cleanup.
- Delete temporary resources after testing.

### Lab Timeout Safety

The configured Lambda timeout is:

```text
15 Seconds
```

The artificial delay is:

```text
4 Seconds
```

This allows the function to complete without intentionally reaching its own execution timeout.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 09-api-timeout-504

cd 09-api-timeout-504
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

Install missing dependencies:

```bash
sudo apt update

sudo apt install -y curl zip unzip jq
```

### Step 3 — Configure Environment Variables

```bash
export AWS_REGION="us-east-1"

export AWS_DEFAULT_REGION="$AWS_REGION"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab09"

export API_NAME="api-lab09-timeout-troubleshooting"

export FUNCTION_NAME="api-lab09-order-handler"

export ROLE_NAME="api-lab09-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab09"

export HEALTHY_TIMEOUT_MS=10000

export BROKEN_TIMEOUT_MS=1500

export SLOW_DELAY_SECONDS=4
```

### Step 4 — Create `.gitignore`

```bash
cat > .gitignore <<'EOF'
function.zip
lab09-resources.env
lab09-*.json
lab09-*.txt
*-headers.txt
*-response.json
slow-but-working-response.json
optimized-response.json

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
  --description "API Gateway Lab09 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Permissions

```bash
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 4 — Verify Execution Role

```bash
aws iam list-attached-role-policies \
  --role-name "$ROLE_NAME" \
  --output table
```

Expected:

```text
AWSLambdaBasicExecutionRole
```

### Understanding the Role

The execution role permits Lambda to write logs to CloudWatch.

It does not control the API Gateway integration timeout.

---

## 8. Create Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
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
EOF
```

### Understanding the Application

The Lambda function reads:

```text
DELAY_SECONDS
```

from its environment.

When configured with:

```text
DELAY_SECONDS=0
```

the function returns without an intentional delay.

When configured with:

```text
DELAY_SECONDS=4
```

the function pauses for approximately four seconds.

The application records two log markers:

```text
LAB09_REQUEST_STARTED
```

and:

```text
LAB09_REQUEST_COMPLETED
```

The completion log includes the handler's processing duration.

This allows us to compare actual Lambda processing with the API Gateway integration timeout.

### Step 2 — Validate Python Syntax

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

## 9. Deploy Lambda Function

### Step 1 — Create Lambda

```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.13 \
  --role "$ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 15 \
  --memory-size 128 \
  --environment "Variables={DELAY_SECONDS=0}" \
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

If Lambda cannot assume the newly created IAM role immediately, retry after the role becomes available.

### Step 2 — Wait for Activation

```bash
aws lambda wait function-active-v2 \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Retrieve Lambda ARN

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
    Environment:Environment.Variables
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Timeout": 15,
  "Environment": {
    "DELAY_SECONDS": "0"
  }
}
```

### Important Observation

Lambda is allowed to run for up to 15 seconds.

This does not mean API Gateway automatically waits 15 seconds.

The API Gateway integration timeout is configured separately.

---

## 10. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab09 API Gateway 504 timeout troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_ID"
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_ID"
```

### Step 3 — Create `/orders` Resource

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

The method has no authorizer because this is a temporary troubleshooting API using fabricated data.

---

## 11. Configure Lambda Proxy Integration

### Step 1 — Generate Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Create Integration

```bash
aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "$INTEGRATION_URI" \
  --timeout-in-millis "$HEALTHY_TIMEOUT_MS" \
  --region "$AWS_REGION"
```

This configures:

```text
Integration Type = AWS_PROXY

Integration Timeout = 10000 ms
```

### Step 3 — Verify Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Type:type,Timeout:timeoutInMillis}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Type": "AWS_PROXY",
  "Timeout": 10000
}
```

### Step 4 — Grant Lambda Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/${STAGE_NAME}/GET/orders" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Lambda Resource Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Verify that API Gateway is permitted to invoke the Lambda function.

---

## 12. Deploy REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab09 healthy API deployment" \
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
cat > lab09-resources.env <<EOF
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
export HEALTHY_TIMEOUT_MS="$HEALTHY_TIMEOUT_MS"
export BROKEN_TIMEOUT_MS="$BROKEN_TIMEOUT_MS"
export SLOW_DELAY_SECONDS="$SLOW_DELAY_SECONDS"
EOF

chmod 600 lab09-resources.env
```

Restore variables in another terminal:

```bash
source lab09-resources.env
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

### Step 2 — Measure Response Time

```bash
curl -sS \
  -o baseline-response.json \
  -w 'HTTP Status: %{http_code}\nTotal Time: %{time_total}s\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 200
```

The total request time depends on network latency and Lambda initialization overhead.

### Step 3 — Inspect Response

```bash
cat baseline-response.json | jq .
```

Example:

```json
{
  "message": "Orders retrieved successfully",
  "processing_time_ms": 0.15,
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

The processing time shown is illustrative.

### Step 4 — Save Baseline Headers

```bash
curl -sS \
  -D baseline-headers.txt \
  -o baseline-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

### Step 5 — Verify Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected markers:

```text
LAB09_REQUEST_STARTED delay=0.0

LAB09_REQUEST_COMPLETED duration_ms=...
```

### Healthy Baseline Findings

| Component | Result |
|---|---|
| REST API | Deployed |
| Lambda Function | Active |
| Lambda Delay | 0 seconds |
| Lambda Timeout | 15 seconds |
| Integration Timeout | 10 seconds |
| API Response | HTTP 200 |
| Backend Processing | Successful |

---

## 14. Fault Injection — Introduce Slow Backend Processing

### Step 1 — Update Lambda Delay

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "Variables={DELAY_SECONDS=4}" \
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
  --query '{
    Timeout:Timeout,
    Environment:Environment.Variables,
    LastUpdateStatus:LastUpdateStatus
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Timeout": 15,
  "Environment": {
    "DELAY_SECONDS": "4"
  },
  "LastUpdateStatus": "Successful"
}
```

### Step 4 — Test With Original Integration Timeout

```bash
curl -sS \
  -o slow-but-working-response.json \
  -w 'HTTP Status: %{http_code}\nTotal Time: %{time_total}s\n' \
  "$API_URL"
```

Expected under normal conditions:

```text
HTTP Status: 200

Total Time: Approximately 4 Seconds
```

### Step 5 — Inspect Response

```bash
cat slow-but-working-response.json | jq .
```

Look for:

```text
processing_time_ms
```

with a value close to:

```text
4000
```

### Important Finding

Lambda processing has become slower.

However, API Gateway still waits up to 10 seconds.

Therefore, the four-second backend response can complete successfully.

This separates the backend latency problem from the integration timeout problem.

---

## 15. Fault Injection — Reduce API Gateway Integration Timeout

### Step 1 — Configure Broken Timeout

```bash
aws apigateway update-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --patch-operations \
    "op=replace,path=/timeoutInMillis,value=$BROKEN_TIMEOUT_MS" \
  --region "$AWS_REGION"
```

This changes the integration timeout to:

```text
1500 milliseconds
```

### Step 2 — Verify Broken Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Type:type,Timeout:timeoutInMillis}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Type": "AWS_PROXY",
  "Timeout": 1500
}
```

### Step 3 — Save Broken Configuration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --output json \
  --region "$AWS_REGION" \
  > lab09-broken-integration.json
```

### Step 4 — Redeploy REST API

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab09 intentionally broken integration timeout" \
  --region "$AWS_REGION"
```

### Why Redeployment Is Required

The API Gateway REST API integration configuration has changed.

The new timeout must be deployed to the `dev` stage before testing through the stage's invoke URL.

### Fault Injection Summary

| Component | Value |
|---|---:|
| Lambda Delay | 4 seconds |
| API Gateway Timeout | 1.5 seconds |
| Lambda Timeout | 15 seconds |
| Expected API Response | HTTP 504 |
| Expected Backend Outcome | Lambda may complete |
| Intentional Fault | Integration timeout mismatch |

---

## 16. Reproduce HTTP 504 Gateway Timeout

### Step 1 — Invoke API

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 504
```

Possible response:

```json
{
  "message": "Endpoint request timed out"
}
```

### Step 2 — Measure Response Time

```bash
curl -sS \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\nTotal Time: %{time_total}s\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 504

Total Time: Approximately 1.5 Seconds
```

The client-observed time may be slightly longer because of network and connection overhead.

### Step 3 — Save Broken Headers

```bash
curl -sS \
  -D broken-headers.txt \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

### Step 4 — Inspect Error

```bash
cat broken-response.json | jq .
```

### Step 5 — Validate HTTP 504

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "504" ]; then
  echo "SUCCESS: API Gateway timeout reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 6 — Repeat With Limited Requests

```bash
for i in {1..3}; do

  echo "Request $i"

  curl -sS \
    -o /dev/null \
    -w 'Status: %{http_code} | Time: %{time_total}s\n' \
    "$API_URL"

done
```

Expected: HTTP 504 during the intentionally broken configuration.

The test is bounded to avoid generating unnecessary traffic.

### Broken-State Findings

| Check | Result |
|---|---|
| GET Method | Exists |
| Lambda Integration | Correct |
| Lambda Function | Active |
| Lambda Processing | Approximately 4 seconds |
| Integration Timeout | 1.5 seconds |
| API Response | 504 |
| Root Cause | Backend exceeds gateway wait time |

---

## 17. Investigate API Gateway Integration

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

### Step 3 — Inspect Integration Configuration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Timeout Value

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query 'timeoutInMillis' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
1500
```

### Step 5 — Inspect API Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
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
| GET Method | Correct |
| API Stage | Deployed |
| Integration Type | AWS_PROXY |
| Lambda Permission | Correct |
| Integration Timeout | 1,500 ms |
| Backend Processing | Approximately 4,000 ms |
| Failure | Integration timeout exceeded |

---

## 18. Investigate Lambda Function Configuration

### Step 1 — Inspect Lambda State

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    State:State,
    Runtime:Runtime,
    Timeout:Timeout,
    Environment:Environment.Variables
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Timeout": 15,
  "Environment": {
    "DELAY_SECONDS": "4"
  }
}
```

### Step 2 — Compare Timeout Values

| Parameter | Value |
|---|---:|
| Lambda Environment Delay | 4,000 ms |
| Lambda Execution Timeout | 15,000 ms |
| API Gateway Integration Timeout | 1,500 ms |

### Step 3 — Analyze the Mismatch

Lambda requires approximately four seconds.

API Gateway waits approximately 1.5 seconds.

The backend response cannot arrive within the configured integration timeout.

### Step 4 — Verify Lambda Deployment Health

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}' \
  --output json \
  --region "$AWS_REGION"
```

### Important Finding

The Lambda function is not necessarily failing.

The client-facing failure occurs because API Gateway's integration timeout expires first.

---

## 19. Investigate CloudWatch Logs

### Step 1 — Inspect Recent Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected application markers:

```text
LAB09_REQUEST_STARTED delay=4.0

LAB09_REQUEST_COMPLETED duration_ms=4000...
```

### Step 2 — Inspect Lambda REPORT Logs

Lambda logs normally include a REPORT entry containing execution duration.

Example:

```text
REPORT RequestId: ...
Duration: 4005.12 ms
Billed Duration: ...
Memory Size: 128 MB
```

The exact duration will vary.

### Step 3 — Search Completion Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB09_REQUEST_COMPLETED"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Save Broken Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab09-broken-cloudwatch-evidence.json
```

### Important Observation

API Gateway may return HTTP 504 while Lambda continues executing.

A successful Lambda completion log after the client timeout demonstrates that the backend invocation continued.

This does not mean the client received the Lambda response.

### Production Implication

If a Lambda function updates a database after the API Gateway timeout, the client may not know whether the operation succeeded.

If the client retries, the operation could run again unless the application uses appropriate idempotency controls.

---

## 20. Investigate CloudWatch Metrics

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
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION"
```

Expected: API Gateway 5XX errors increase following HTTP 504 responses, subject to metric publication delay.

### Step 3 — Inspect IntegrationLatency

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name IntegrationLatency \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --output json \
  --region "$AWS_REGION"
```

IntegrationLatency measures time spent waiting for the backend integration.

For timed-out requests, it can help identify delays approaching the configured integration timeout.

### Step 4 — Inspect Lambda Duration

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --output json \
  --region "$AWS_REGION"
```

Expected: backend processing duration around four seconds for slow invocations.

### Step 5 — Inspect Lambda Errors

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

Lambda Errors may remain zero because the function itself can complete successfully.

### Step 6 — Inspect Lambda Invocations

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

### Step 7 — Save API Gateway Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab09-api-5xx-metric.json
```

### Step 8 — Save Integration Latency Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name IntegrationLatency \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --output json \
  --region "$AWS_REGION" \
  > lab09-integration-latency-metric.json
```

### Step 9 — Save Lambda Duration Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Average Maximum \
  --output json \
  --region "$AWS_REGION" \
  > lab09-lambda-duration-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 5XXError | Increases |
| API Gateway IntegrationLatency | Elevated near timeout |
| Lambda Duration | Approximately 4,000 ms |
| Lambda Invocations | Requests reach Lambda |
| Lambda Errors | May remain zero |
| Client HTTP Status | 504 |

CloudWatch metrics may be delayed and aggregated.

Compare them with curl timings, Lambda logs, and API Gateway integration configuration rather than relying on one metric alone.

---

## 21. Root Cause Analysis

### Root Cause

The API Gateway REST API integration timeout was shorter than the time required by the Lambda backend to process a request.

The Lambda function required approximately four seconds.

The API Gateway integration timeout was configured to 1.5 seconds.

API Gateway stopped waiting before the Lambda response arrived.

The client received HTTP 504.

### Root Cause Diagram

```text
GET /dev/orders
       |
       v
Amazon API Gateway
       |
       v
Lambda Integration
       |
       v
Timeout = 1.5 Seconds
       |
       v
Invoke AWS Lambda
       |
       v
Processing = 4 Seconds
       |
       v
Gateway Timeout Expires
       |
       v
HTTP 504 Returned to Client
       |
       v
Lambda May Continue Executing
       |
       v
Backend Completes After Client Timeout
```

### Five Whys

**Why 1 — Why did the API return HTTP 504?**

API Gateway did not receive the backend response before the integration timeout expired.

**Why 2 — Why did the backend response arrive too late?**

The Lambda function required approximately four seconds to process the request.

**Why 3 — Why was four seconds too slow?**

The integration timeout was configured to only 1.5 seconds.

**Why 4 — Why did the configurations conflict?**

The backend processing duration and gateway timeout were not aligned with the intended latency requirements.

**Why 5 — How can the incident be prevented?**

Use latency monitoring, backend performance testing, reviewed timeout configurations, and automated integration tests.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-009 |
| HTTP Error | 504 |
| Error Message | Endpoint request timed out |
| API Resource | /orders |
| Method | GET |
| Lambda State | Active |
| Lambda Delay | 4 seconds |
| Lambda Timeout | 15 seconds |
| Integration Timeout | 1.5 seconds |
| Root Cause | Slow backend exceeds integration timeout |
| Primary Remediation | Remove unnecessary backend delay |
| Additional Remediation | Restore integration timeout |
| REST API Redeployment | Required for integration changes |

---

## 22. Remediation — Optimize Backend Processing

### Step 1 — Remove Artificial Delay

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --environment "Variables={DELAY_SECONDS=0}" \
  --region "$AWS_REGION"
```

### Step 2 — Wait for Update

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Lambda Environment

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
  "DELAY_SECONDS": "0"
}
```

### Step 4 — Test Optimized Backend

```bash
curl -sS \
  -o optimized-response.json \
  -w 'HTTP Status: %{http_code}\nTotal Time: %{time_total}s\n' \
  "$API_URL"
```

Expected under normal conditions:

```text
HTTP Status: 200
```

### Step 5 — Verify Response

```bash
cat optimized-response.json | jq .
```

The processing time should be much lower than the original four-second delay.

### Production Considerations

Removing an artificial delay simulates optimizing slow backend operations.

In production, common remediation steps include:

- Optimizing SQL queries.
- Reducing unnecessary API calls.
- Reusing connections.
- Investigating slow downstream dependencies.
- Reviewing network configuration.
- Improving caching.
- Reducing unnecessary synchronous work.
- Moving long-running operations to asynchronous workflows.

A very low integration timeout should not be considered safe merely because one warm Lambda invocation completes quickly.

---

## 23. Remediation — Restore Integration Timeout

### Step 1 — Restore 10-Second Timeout

```bash
aws apigateway update-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --patch-operations \
    "op=replace,path=/timeoutInMillis,value=$HEALTHY_TIMEOUT_MS" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Configuration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Type:type,Timeout:timeoutInMillis}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Type": "AWS_PROXY",
  "Timeout": 10000
}
```

### Step 3 — Redeploy REST API

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab09 timeout remediation" \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovered Integration Configuration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --output json \
  --region "$AWS_REGION" \
  > lab09-recovered-integration.json
```

### Why Redeployment Is Required

The REST API integration timeout is part of the API integration configuration.

Changes to the integration must be included in a new deployment for the stage to use them.

The Lambda environment variable is separate and does not require an API Gateway redeployment.

### Configuration Comparison

| Setting | Broken | Recovered |
|---|---|---|
| Lambda Artificial Delay | 4 seconds | 0 seconds |
| API Gateway Timeout | 1.5 seconds | 10 seconds |
| Lambda Execution Timeout | 15 seconds | 15 seconds |
| API Gateway Redeployment | Required | Required |

---

## 24. Verify Successful Recovery

### Step 1 — Send Original GET Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
content-type: application/json
```

### Step 2 — Measure Recovered Response

```bash
curl -sS \
  -D recovered-headers.txt \
  -o recovered-response.json \
  -w 'HTTP Status: %{http_code}\nTotal Time: %{time_total}s\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 200
```

### Step 3 — Validate JSON Response

```bash
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: API Gateway timeout issue resolved")
PY
```

### Step 4 — Verify Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected recovery markers:

```text
LAB09_REQUEST_STARTED delay=0.0

LAB09_REQUEST_COMPLETED duration_ms=...
```

### Step 5 — Save Recovered Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB09_REQUEST_COMPLETED"' \
  --output json \
  --region "$AWS_REGION" \
  > lab09-recovered-cloudwatch-evidence.json
```

### Step 6 — Verify Integration Timeout

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query 'timeoutInMillis' \
  --output text \
  --region "$AWS_REGION"
```

Expected:

```text
10000
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Deployed | Deployed |
| GET Method | Correct | Correct |
| Lambda Integration | Correct | Correct |
| Lambda Delay | 4 seconds | 0 seconds |
| Integration Timeout | 1.5 seconds | 10 seconds |
| Lambda Timeout | 15 seconds | 15 seconds |
| API Response | 504 | 200 |
| Lambda Code | Unchanged | Unchanged |
| Lambda Configuration | Slow | Optimized |
| API Deployment | Broken configuration | Recovered configuration |

**Recovery is confirmed when the corrected endpoint returns HTTP 200, the integration timeout is restored, and Lambda logs show successful processing without the artificial delay.**

---

## 25. Additional Production Troubleshooting Scenarios

### Scenario 1 — Slow Database Query

**Symptom:** API Gateway returns HTTP 504 during database operations.

**Possible Cause:** RDS queries exceed the configured integration timeout.

**Investigation:** Compare API Gateway IntegrationLatency, Lambda Duration, database query latency, and database performance metrics.

**Remediation:** Optimize queries, indexes, connection management, or application logic.

### Scenario 2 — Lambda Function Timeout

**Symptom:** Lambda execution reaches its configured function timeout.

**Investigation:** Search Lambda CloudWatch Logs for timeout indicators and inspect the REPORT entries.

**Remediation:** Identify slow operations and configure appropriate function execution limits.

### Scenario 3 — Downstream Service Timeout

**Symptom:** Lambda waits too long for a downstream HTTP service.

**Investigation:** Inspect dependency latency, DNS, network configuration, client connection timeouts, and application logs.

**Remediation:** Use bounded downstream timeouts, retries, circuit breakers, and asynchronous processing where appropriate.

### Scenario 4 — Incorrect Integration Timeout

**Symptom:** API Gateway returns HTTP 504 even though Lambda completes successfully.

**Investigation:**

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query 'timeoutInMillis'
```

**Remediation:** Align integration timeout with the expected backend response-time budget.

### Scenario 5 — Cold Start Latency

**Symptom:** First requests are slower than subsequent requests.

**Possible Cause:** Lambda initialization overhead.

**Investigation:** Review Lambda initialization and execution logs, duration metrics, and runtime startup behavior.

**Remediation:** Optimize initialization and consider appropriate concurrency strategies for latency-sensitive workloads.

### Scenario 6 — Incorrect Client Timeout

**Symptom:** The client times out before API Gateway returns a response.

**Investigation:** Compare the client's timeout with API Gateway integration timeout and backend duration.

**Remediation:** Configure a consistent end-to-end timeout budget.

### Scenario 7 — Long-Running Backend Workflow

**Symptom:** The business operation requires more time than is practical for a synchronous API request.

**Possible Solution:** Use asynchronous processing.

Example:

```text
Client
   |
   v
API Gateway
   |
   v
Lambda
   |
   v
SQS / Step Functions
   |
   v
Background Processing
   |
   v
Status Stored
   |
   v
Client Polls Status Endpoint
```

A common pattern is to return HTTP 202 Accepted with a job ID instead of holding the original request open.

### Troubleshooting Comparison

| Symptom | Possible Cause | Investigation |
|---|---|---|
| HTTP 504 around configured timeout | Integration timeout | API Gateway integration settings |
| Lambda timeout in logs | Lambda execution exceeded limit | Lambda logs |
| High Lambda Duration | Slow application processing | Lambda metrics |
| High database latency | Slow query | RDS metrics and query analysis |
| Intermittent high latency | Cold starts or dependency delays | Logs and metrics |
| Client fails before gateway timeout | Client timeout | HTTP client configuration |
| Retry creates duplicate operations | Missing idempotency | Application design |

---

## 26. Cloud Security Engineering Considerations

### Timeouts Are Reliability Controls

Timeouts prevent applications from waiting indefinitely for unresponsive dependencies.

However, an excessively short timeout can reject legitimate work, while an excessively long timeout can increase resource consumption.

### Apply Least Privilege

Restrict IAM permissions for changing:

- API Gateway integration configuration.
- Lambda environment variables.
- Lambda timeout settings.
- API deployments.
- CloudWatch logging configuration.

### Monitor Configuration Changes

Unexpected changes to API Gateway timeouts can cause outages.

Use Infrastructure as Code, CloudTrail, and reviewed CI/CD workflows to track changes.

### Protect Against Duplicate Processing

A client receiving HTTP 504 cannot assume the backend operation failed.

For operations that create or modify data, use idempotency keys, transaction safeguards, and appropriate retry policies.

### Avoid Unbounded Retries

Repeatedly retrying timeouts without backoff can increase traffic and worsen an outage.

Use:

```text
Bounded Retries

Exponential Backoff

Jitter

Idempotency Protection
```

### Secure Downstream Connections

For backend calls to databases and external services:

- Use TLS where appropriate.
- Protect credentials.
- Restrict outbound access.
- Apply explicit connection and read timeouts.
- Use Secrets Manager for applicable secrets.
- Monitor dependency failures.

### Monitor API Performance

Important metrics include:

```text
API Gateway 5XXError

API Gateway Latency

API Gateway IntegrationLatency

Lambda Duration

Lambda Errors

Lambda Invocations

Lambda ConcurrentExecutions

Lambda Throttles
```

### Use Asynchronous Processing When Appropriate

Long-running operations should not always remain inside synchronous HTTP requests.

Consider SQS, Step Functions, EventBridge, or other asynchronous approaches based on the workload.

### Security Principle

**Choose timeout settings based on measured backend behavior and business requirements, while protecting against excessive resource usage and unsafe retries.**

---

## 27. Cost Management and AWS Resource Cleanup

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Request charges |
| AWS Lambda | Invocations and execution duration |
| CloudWatch Logs | Log ingestion and retention |
| CloudWatch Metrics | Applicable monitoring charges |
| IAM | No separate standard IAM role charge |

### Cost Optimization

- Use a temporary API.
- Keep the artificial delay limited to four seconds.
- Avoid unlimited request loops.
- Remove the delay after testing.
- Use limited CloudWatch log retention in longer-lived lab environments.
- Delete temporary resources when finished.

### Step 1 — Verify Resource Tags

```bash
aws apigateway get-tags \
  --resource-arn "arn:aws:apigateway:${AWS_REGION}::/restapis/${API_ID}" \
  --region "$AWS_REGION"

aws lambda list-tags \
  --resource "$FUNCTION_ARN" \
  --region "$AWS_REGION"

aws iam list-role-tags \
  --role-name "$ROLE_NAME"
```

Confirm:

```text
Project = API-Gateway-Troubleshooting-Lab09
```

### Step 2 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

### Step 3 — Delete Lambda Function

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 4 — Detach IAM Logging Policy

```bash
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 5 — Delete IAM Role

```bash
aws iam delete-role \
  --role-name "$ROLE_NAME"
```

### Step 6 — Delete CloudWatch Log Group

```bash
aws logs delete-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

If the log group was never created, AWS may return `ResourceNotFoundException`.

### Step 7 — Verify API Deletion

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 8 — Verify Lambda Deletion

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Step 9 — Verify IAM Role Deletion

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected:

```text
NoSuchEntity
```

### Step 10 — Verify CloudWatch Cleanup

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
| GET method and resource | Deleted |
| Lambda integration | Deleted |
| Lambda function | Deleted |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |

Preserve sanitized local source code and incident evidence for your GitHub documentation.

---

## 28. Interview Questions and Answers

### Q1. What does HTTP 504 Gateway Timeout mean?

It means a gateway or proxy did not receive a timely response from its upstream integration.

### Q2. What caused HTTP 504 in this lab?

The Lambda backend required approximately four seconds, while API Gateway was configured to wait only 1.5 seconds.

### Q3. What is API Gateway integration timeout?

It is the configured maximum time that API Gateway waits for a backend integration response.

### Q4. What is Lambda function timeout?

It is the maximum time AWS Lambda allows an invocation to execute before terminating it.

### Q5. Can API Gateway return HTTP 504 while Lambda completes successfully?

Yes. API Gateway can stop waiting for the response while Lambda continues processing.

### Q6. Why is that dangerous for write operations?

The client may retry after HTTP 504 even though the original backend operation completed, potentially causing duplicate actions.

### Q7. How do you inspect API Gateway integration timeout?

```bash
aws apigateway get-integration \
  --rest-api-id REST_API_ID \
  --resource-id RESOURCE_ID \
  --http-method GET \
  --query timeoutInMillis
```

### Q8. How do you update the integration timeout?

Use `aws apigateway update-integration` with a patch operation targeting `/timeoutInMillis`.

### Q9. Why did this lab require API Gateway redeployment?

The integration configuration changed, so the updated configuration had to be deployed to the `dev` stage.

### Q10. Does updating a Lambda environment variable require API Gateway redeployment?

No. It changes the Lambda configuration rather than the API Gateway REST API integration.

### Q11. Which CloudWatch metric helps investigate integration response time?

The API Gateway `IntegrationLatency` metric.

### Q12. Which metric shows Lambda processing duration?

The Lambda `Duration` metric.

### Q13. Can Lambda Errors remain zero during an API Gateway 504 incident?

Yes. Lambda may execute successfully even though API Gateway has already timed out.

### Q14. Should engineers always increase API Gateway integration timeout?

No. They should first investigate backend performance, downstream dependencies, and application design.

### Q15. How can long-running operations avoid API Gateway timeout problems?

Use asynchronous workflows, for example SQS or Step Functions, and return a job ID for later status checks.

### Q16. What is the difference between HTTP 502 and HTTP 504?

HTTP 502 generally indicates an invalid or failed upstream response. HTTP 504 indicates that the upstream response did not arrive within the timeout.

### Q17. How do you prevent duplicate processing after timeouts?

Use idempotency keys, deduplication, safe retry policies, and suitable transactional controls.

### Q18. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

The API exposed a GET endpoint that retrieved order information.

I initially configured the Lambda function with no artificial delay and the API Gateway integration timeout to 10 seconds.

The endpoint returned HTTP 200.

Next, I intentionally introduced a four-second delay into the Lambda function using an environment variable.

With the original 10-second integration timeout, the slow backend still completed successfully.

I then reduced the API Gateway integration timeout to 1.5 seconds and redeployed the REST API.

The endpoint started returning HTTP 504 Gateway Timeout.

I investigated the API Gateway integration configuration, Lambda function settings, response time using curl, CloudWatch Logs, and CloudWatch latency metrics.

The investigation showed that Lambda was taking approximately four seconds while API Gateway waited only 1.5 seconds.

I also observed that Lambda could complete successfully even after API Gateway returned HTTP 504.

I removed the artificial backend delay and restored the 10-second integration timeout.

After redeploying the REST API, the endpoint returned HTTP 200.

Finally, I reviewed timeout boundaries, duplicate-processing risks, asynchronous alternatives, and resource cleanup.

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
│
├── 09-api-timeout-504/
│   ├── README.md
│   ├── .gitignore
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab09-resources.env
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── slow-but-working-response.json
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── optimized-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab09-broken-integration.json
│   ├── lab09-recovered-integration.json
│   ├── lab09-broken-cloudwatch-evidence.json
│   ├── lab09-recovered-cloudwatch-evidence.json
│   ├── lab09-api-5xx-metric.json
│   ├── lab09-integration-latency-metric.json
│   └── lab09-lambda-duration-metric.json
│
└── 10-custom-domain-certificate-failure/
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Incident documentation and remediation |
| .gitignore | Excludes generated files and local evidence |
| lambda_function.py | Lambda backend with configurable artificial delay |
| lambda-trust-policy.json | Lambda IAM trust policy |
| function.zip | Generated Lambda deployment package |
| lab09-resources.env | Local AWS resource variables |
| baseline-headers.txt | Initial healthy HTTP headers |
| baseline-response.json | Healthy baseline response |
| slow-but-working-response.json | Four-second backend response with original timeout |
| broken-headers.txt | HTTP 504 response headers |
| broken-response.json | Gateway timeout response |
| optimized-response.json | Backend response after removing delay |
| recovered-headers.txt | Recovered HTTP headers |
| recovered-response.json | Final HTTP 200 response |
| lab09-broken-integration.json | Timeout misconfiguration evidence |
| lab09-recovered-integration.json | Corrected integration configuration |
| lab09-broken-cloudwatch-evidence.json | Lambda execution evidence during failure |
| lab09-recovered-cloudwatch-evidence.json | Successful backend logs after recovery |
| lab09-api-5xx-metric.json | API Gateway 5XX metrics |
| lab09-integration-latency-metric.json | Integration latency measurements |
| lab09-lambda-duration-metric.json | Lambda execution duration measurements |

### Recommended Public GitHub Files

```text
09-api-timeout-504/
├── README.md
├── .gitignore
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 09
09-api-timeout-504/function.zip
09-api-timeout-504/lab09-resources.env
09-api-timeout-504/lab09-*.json
09-api-timeout-504/lab09-*.txt
09-api-timeout-504/*-headers.txt
09-api-timeout-504/*-response.json
09-api-timeout-504/slow-but-working-response.json
09-api-timeout-504/optimized-response.json

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

Do not publish AWS credentials or account-specific troubleshooting evidence without review.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how Amazon API Gateway can return HTTP 504 even when the integrated Lambda function remains healthy.

We created a REST API integrated with a Python Lambda backend.

The API exposed a GET endpoint that returned order information.

We initially configured the Lambda function without an artificial delay and used a 10-second API Gateway integration timeout.

The endpoint returned HTTP 200.

Next, we introduced a four-second processing delay in Lambda.

The backend remained healthy and still completed successfully under the original integration timeout.

We then reduced the API Gateway integration timeout to 1.5 seconds.

After redeploying the REST API, the endpoint began returning HTTP 504 Gateway Timeout.

We investigated the API Gateway integration settings, Lambda environment variables, curl response timing, CloudWatch Logs, and CloudWatch metrics.

The investigation identified the mismatch between the four-second backend processing time and the 1.5-second integration timeout.

We also examined the important production behavior where Lambda may continue executing after API Gateway has returned a timeout to the client.

We removed the artificial backend delay and restored the 10-second integration timeout.

After redeploying the REST API, the endpoint returned HTTP 200.

Finally, the lab covered timeout boundaries, safer retries, asynchronous processing, security considerations, cost management, and resource cleanup.

**Key Lesson:** HTTP 504 does not automatically mean the Lambda function failed. Engineers must compare API Gateway integration timeout, actual backend processing duration, Lambda execution timeout, and client timeout to identify the correct root cause.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 504 troubleshooting
- API Gateway integration timeout configuration
- Lambda execution timeout
- Lambda environment variables
- AWS Lambda proxy integration
- Python 3.13
- HTTP response timing using curl
- AWS IAM execution roles
- Lambda resource-based permissions
- AWS CLI v2
- Linux Bash
- CloudWatch Logs
- API Gateway IntegrationLatency
- API Gateway 5XXError
- Lambda Duration
- Lambda Errors
- Root cause analysis
- Backend performance troubleshooting
- Integration timeout remediation
- REST API redeployment
- Recovery verification
- Idempotency considerations
- Asynchronous architecture fundamentals
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-009 |
| Scenario | API Gateway Timeout — HTTP 504 |
| REST API | api-lab09-timeout-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab09-order-handler |
| Lambda Timeout | 15 seconds |
| Broken Lambda Delay | 4 seconds |
| Broken Integration Timeout | 1.5 seconds |
| Broken API Response | HTTP 504 |
| Root Cause | Backend response exceeds integration timeout |
| Primary Remediation | Remove unnecessary backend delay |
| Additional Remediation | Restore integration timeout |
| Recovered Lambda Delay | 0 seconds |
| Recovered Integration Timeout | 10 seconds |
| Recovered API Response | HTTP 200 |
| Lambda Code Changes | None |
| Lambda Configuration Changes | Required |
| API Gateway Redeployment | Required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production timeout troubleshooting requires understanding separate timeout boundaries, measuring real application latency, correlating API Gateway metrics with Lambda execution, and implementing safe remediation without introducing duplicate-processing risks.

---

## Official AWS Documentation

- [Amazon API Gateway — Troubleshoot HTTP 504 Errors](https://repost.aws/knowledge-center/api-gateway-rest-api-504-errors)
- [Amazon API Gateway — UpdateIntegration API](https://docs.aws.amazon.com/apigateway/latest/api/API_UpdateIntegration.html)
- [Amazon API Gateway — Patch Operations](https://docs.aws.amazon.com/apigateway/latest/api/patch-operations.html)
- [AWS CLI — Update Integration](https://docs.aws.amazon.com/cli/latest/reference/apigateway/update-integration.html)
- [AWS CLI — Get Integration](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-integration.html)
- [Amazon API Gateway — Integration Timeout Quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)
- [Amazon API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS Lambda — Configure Function Timeout](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html)
- [AWS Lambda — Environment Variables](https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html)
- [AWS Lambda — Monitoring Metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [AWS Builders Library — Timeouts, Retries, and Backoff With Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)