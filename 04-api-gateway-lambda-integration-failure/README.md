# Lab 04 — Amazon API Gateway–Lambda Integration Failure

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an **Amazon API Gateway–AWS Lambda integration failure** caused by missing Lambda invocation permissions.

In production, API Gateway commonly serves as the entry point for serverless applications. It receives HTTP requests, routes them to backend services, and returns responses to clients.

AWS Lambda is frequently used as the backend compute service for API Gateway REST APIs.

For the integration to work, the Lambda function must have a resource-based policy that permits API Gateway to invoke it.

In this lab, we create a REST API exposing a `GET /orders` endpoint backed by a Python Lambda function.

We first configure the API Gateway–Lambda integration correctly and verify that the API returns HTTP 200.

Next, we intentionally remove the Lambda resource-based permission that authorizes API Gateway to invoke the function.

After removing the permission, API Gateway can no longer invoke Lambda and returns HTTP **500 Internal Server Error**.

The Lambda function itself remains healthy.

We investigate the failure using AWS CLI, curl, API Gateway integration configuration, Lambda resource-based policies, CloudWatch Logs, CloudWatch metrics, and CloudTrail.

We identify the missing invocation permission as the root cause and restore it using a least-privilege Lambda resource policy.

Finally, we repeat the original API request, verify HTTP 200, review the security implications, and clean up the temporary infrastructure.

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
Remove Lambda Invocation Permission
           |
           v
Send GET /orders Request
           |
           v
API Gateway Attempts Lambda Invocation
           |
           v
Lambda Service Denies Invocation
           |
           v
API Gateway Returns HTTP 500
           |
           v
Investigate API Gateway Integration
           |
           v
Verify Lambda Function Health
           |
           v
Inspect Lambda Resource-Based Policy
           |
           v
Investigate CloudWatch Logs and Metrics
           |
           v
Identify Missing lambda:InvokeFunction Permission
           |
           v
Restore Least-Privilege Permission
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
| Incident ID | INC-APIGW-004 |
| Lab Name | API Gateway–Lambda Integration Failure |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch, CloudTrail |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab04-integration-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab04-order-handler` |
| Lambda Execution Role | `api-lab04-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Healthy Configuration | API Gateway invoke permission present |
| Broken Configuration | API Gateway invoke permission removed |
| Fault Injection | `lambda remove-permission` |
| Broken HTTP Response | 500 |
| Recovered HTTP Response | 200 |
| CloudWatch API Metric | `5XXError` |
| CloudWatch Lambda Metric | `Invocations` |
| CloudWatch Log Marker | `LAB04_ORDER_SUCCESS` |
| Root Cause | Missing Lambda resource-based permission |
| Remediation | Restore `lambda:InvokeFunction` permission |
| API Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand API Gateway–Lambda proxy integration.
- Configure a REST API using AWS CLI.
- Deploy a Python Lambda backend.
- Understand Lambda execution roles.
- Understand Lambda resource-based policies.
- Configure service-to-service invocation permissions.
- Reproduce an API Gateway integration failure.
- Investigate HTTP 500 errors.
- Verify Lambda function health independently.
- Inspect API Gateway methods and integrations.
- Understand `lambda:InvokeFunction`.
- Investigate missing invocation permissions.
- Analyze CloudWatch Logs and metrics.
- Use CloudTrail for configuration-change investigations.
- Apply least-privilege remediation.
- Verify successful recovery.
- Understand when API redeployment is necessary.
- Practice production root cause analysis.
- Clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates a serverless order-management application using Amazon API Gateway and AWS Lambda.

Customers retrieve order information through:

```http
GET /dev/orders
```

The application uses API Gateway as the public API entry point.

API Gateway forwards requests to a Python Lambda function responsible for retrieving order information.

Under normal conditions, the endpoint returns:

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

During an infrastructure configuration change, the Lambda resource-based policy is accidentally modified.

The policy statement authorizing API Gateway to invoke Lambda is removed.

After the change, customers begin receiving:

```http
HTTP/2 500
```

Response:

```json
{
  "message": "Internal server error"
}
```

The Cloud Engineering team begins investigating.

The engineer discovers:

- API Gateway exists and is deployed.
- The `/orders` resource exists.
- The GET method is configured correctly.
- Lambda proxy integration is configured.
- The Lambda function is Active.
- The Lambda application works when invoked directly by an authorized identity.
- The failing API Gateway requests do not reach the Lambda handler.
- The Lambda resource-based policy is missing the invocation permission.

The team identifies a service-to-service authorization failure.

After restoring the correct Lambda permission, API Gateway successfully invokes the function again.

### Incident Symptoms

- API Gateway returns HTTP 500.
- API resource and method are correct.
- Lambda integration URI is correct.
- Lambda function remains Active.
- Direct Lambda invocation succeeds.
- API Gateway cannot invoke Lambda.
- No new Lambda application log is generated by the rejected API request.
- Lambda resource-based invocation permission is missing.
- Restoring the permission resolves the incident.

### Business Impact

A failed API Gateway–Lambda integration can cause:

- Failed customer requests.
- Unavailable application endpoints.
- Interrupted business operations.
- Increased API Gateway 5XX errors.
- Service reliability degradation.
- Failed frontend-to-backend communication.
- Increased operational alerts.
- Customer-facing application outages.

### Objective

Identify why API Gateway cannot invoke a healthy Lambda function, restore the correct invocation authorization, and verify successful recovery without making unnecessary changes to application code or API Gateway deployment.

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
               REST API /dev
                     |
                     v
             GET /orders Method
                     |
                     v
          Lambda Proxy Integration
                     |
                     v
          Lambda Resource-Based Policy
                     |
                     v
        lambda:InvokeFunction = ALLOW
                     |
                     v
                AWS Lambda
                     |
                     v
              Python Handler
                     |
                     v
            LAB04_ORDER_SUCCESS
                     |
                     v
             Lambda Returns 200
                     |
                     v
                API Gateway
                     |
                     v
                 HTTP 200
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
               REST API /dev
                     |
                     v
             GET /orders Method
                     |
                     v
          Lambda Proxy Integration
                     |
                     v
          Lambda Resource-Based Policy
                     |
                     v
       lambda:InvokeFunction = MISSING
                     |
                     v
            Invocation Rejected
                     |
             +-------+-------+
             |               |
             v               v
      Lambda Handler    API Gateway Error
       Not Executed           |
                              v
                       HTTP 500 Error
```

### Recovered Architecture

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
         Restore Lambda Permission
                     |
                     v
          Principal: API Gateway
                     |
                     v
       Action: lambda:InvokeFunction
                     |
                     v
          Matching API Source ARN
                     |
                     v
                AWS Lambda
                     |
                     v
             Order Data Returned
                     |
                     v
                HTTP 200 OK
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives API requests |
| REST API | Exposes HTTP endpoints |
| GET /orders | Retrieves order information |
| API Stage | Hosts deployed API |
| Lambda Proxy Integration | Connects API Gateway to Lambda |
| AWS Lambda | Processes backend requests |
| IAM Execution Role | Allows Lambda to write logs |
| Lambda Resource Policy | Authorizes API Gateway invocation |
| CloudWatch Logs | Stores Lambda execution logs |
| CloudWatch Metrics | Tracks errors and invocations |
| CloudTrail | Records supported management events |
| curl | Tests API responses |
| AWS CLI | Configures and investigates AWS resources |

---

## 4. Understanding API Gateway–Lambda Integration

### What Is Lambda Proxy Integration?

Lambda proxy integration allows API Gateway to forward request information directly to a Lambda function.

The Lambda function receives an event containing information such as:

```json
{
  "resource": "/orders",
  "path": "/orders",
  "httpMethod": "GET",
  "headers": {},
  "queryStringParameters": null
}
```

The actual event may include additional request context and headers.

Lambda processes the request and returns a response.

Example:

```python
return {
    "statusCode": 200,
    "headers": {
        "Content-Type": "application/json"
    },
    "body": '{"message":"Success"}'
}
```

API Gateway forwards the response to the client.

### Lambda Execution Role

The execution role determines what the Lambda function can access during execution.

Examples:

```text
CloudWatch Logs
Amazon S3
Amazon DynamoDB
AWS Secrets Manager
Amazon SQS
```

The lab uses:

```text
AWSLambdaBasicExecutionRole
```

This managed policy provides basic CloudWatch logging permissions.

### Lambda Resource-Based Policy

The resource-based policy determines which principals or AWS services are permitted to invoke the Lambda function.

For this integration, the policy requires:

```text
Principal:
apigateway.amazonaws.com

Action:
lambda:InvokeFunction
```

The permission should also include an appropriate source ARN condition.

### Execution Role vs. Resource Policy

| Feature | Execution Role | Resource-Based Policy |
|---|---|---|
| Purpose | Controls Lambda's AWS access | Controls who may invoke Lambda |
| Identity | Assumed by Lambda | Attached to Lambda function |
| API Gateway invocation | Does not automatically authorize it | Can authorize it |
| Example action | `logs:PutLogEvents` | `lambda:InvokeFunction` |
| Main security concern | Excessive backend permissions | Unauthorized invocation |

### Why HTTP 500 Occurs

When API Gateway attempts to invoke Lambda without proper authorization, the Lambda service rejects the integration invocation.

For a REST API Lambda integration, this can produce:

```http
HTTP/2 500
```

The backend application code may never execute.

### Important Difference: HTTP 500 vs. HTTP 502

| Failure | Typical HTTP Response |
|---|---|
| Lambda invocation permission missing | 500 |
| Lambda service rejects invocation | 500 |
| Lambda unhandled exception | 502 |
| Invalid Lambda proxy response | 502 |
| Lambda returns valid `statusCode: 500` | 500 |
| Integration timeout | 504 |

The same HTTP status does not always indicate the same root cause.

---

## 5. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- Python 3.
- curl.
- jq.
- ZIP and unzip.
- IAM management permissions.
- Lambda management permissions.
- API Gateway management permissions.
- CloudWatch access.
- CloudTrail read permissions for optional audit investigation.

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
lambda:InvokeFunction
lambda:AddPermission
lambda:RemovePermission
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

cloudtrail:LookupEvents
```

These are relevant actions rather than a complete executable IAM policy. Resource and condition restrictions should be applied to the lab operator's permissions.

### Safety Rules

- Use a dedicated AWS lab account when possible.
- Create resources with Lab 04 names.
- Never modify production Lambda permissions.
- Do not remove permissions from unrelated functions.
- Use fabricated order data.
- Do not expose AWS credentials.
- Do not publish sensitive CloudWatch logs.
- Limit unnecessary API requests.
- Verify project tags before deleting resources.
- Remove temporary infrastructure after completing the lab.

### API Authorization

The lab uses:

```text
Authorization = NONE
```

This is for a temporary API containing fabricated data.

Production APIs should use suitable authentication and authorization controls.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 04-api-gateway-lambda-integration-failure

cd 04-api-gateway-lambda-integration-failure
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

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab04"

export REST_API_NAME="api-lab04-integration-troubleshooting"

export FUNCTION_NAME="api-lab04-order-handler"

export ROLE_NAME="api-lab04-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab04"
```

### Step 4 — Save Environment Variables

```bash
cat > lab04-resources.env <<EOF
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
EOF

chmod 600 lab04-resources.env
```

Restore the variables after reopening the terminal:

```bash
source lab04-resources.env
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
  --description "API Gateway Lab 04 Lambda execution role" \
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

**Important:** This execution role does not give API Gateway permission to invoke the Lambda function.

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


def lambda_handler(event, context):
    logger.info(
        "LAB04_REQUEST method=%s path=%s",
        event.get("httpMethod"),
        event.get("path")
    )

    logger.info(
        "LAB04_ORDER_SUCCESS count=%s",
        len(ORDERS)
    )

    return make_response(200, {
        "message": "Orders retrieved successfully",
        "orders": ORDERS
    })
EOF
```

### Understanding the Application

The function uses fabricated order data.

When invoked successfully, it logs:

```text
LAB04_ORDER_SUCCESS count=2
```

Then returns a correctly formatted Lambda proxy response containing:

```text
statusCode = 200
```

The function has no intentional application exception.

This allows us to isolate the API Gateway–Lambda invocation permission failure.

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

If AWS reports that Lambda cannot assume the IAM role immediately after role creation, allow IAM propagation and retry.

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

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab04-resources.env
```

### Step 4 — Verify Lambda Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime,Role:Role,Timeout:Timeout}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Role": "arn:aws:iam::123456789012:role/api-lab04-lambda-role",
  "Timeout": 10
}
```

The account number is an example.

---

## 10. Configure CloudWatch Logs

### Step 1 — Create Log Group

```bash
aws logs create-log-group \
  --log-group-name "$LOG_GROUP" \
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Configure Log Retention

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

Expected retention:

```text
7 days
```

---

## 11. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export REST_API_ID=$(aws apigateway create-rest-api \
  --name "$REST_API_NAME" \
  --description "Lab 04 API Gateway Lambda integration troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$REST_API_ID"

echo "export REST_API_ID='$REST_API_ID'" >> lab04-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_RESOURCE_ID"

echo "export ROOT_RESOURCE_ID='$ROOT_RESOURCE_ID'" >> lab04-resources.env
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

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab04-resources.env
```

### Step 4 — Configure GET Method

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

Verify:

```bash
echo "$INTEGRATION_URI"
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

The client uses GET, while API Gateway invokes the Lambda service using POST.

### Step 4 — Define Source ARN

```bash
export SOURCE_ARN="arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${REST_API_ID}/${STAGE_NAME}/GET/orders"

echo "$SOURCE_ARN"
```

### Step 5 — Grant API Gateway Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "$SOURCE_ARN" \
  --source-account "$ACCOUNT_ID" \
  --region "$AWS_REGION"
```

### Step 6 — Verify Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Expected key information:

```text
Effect = Allow

Principal = apigateway.amazonaws.com

Action = lambda:InvokeFunction
```

The source ARN should match the specific API, stage, method, and path.

---

## 13. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab04 healthy Lambda integration deployment" \
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

echo "export API_URL='$API_URL'" >> lab04-resources.env
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

print("SUCCESS: Healthy API Gateway-Lambda integration confirmed")
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
LAB04_REQUEST method=GET path=/orders

LAB04_ORDER_SUCCESS count=2
```

### Step 6 — Save Healthy Permission Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab04-healthy-policy.json
```

The baseline proves that the API route, integration configuration, and invocation permission are working before the failure is introduced.

---

## 15. Fault Injection — Remove Lambda Permission

### Step 1 — Remove Invocation Permission

```bash
aws lambda remove-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --region "$AWS_REGION"
```

This deliberately removes the API Gateway invocation permission.

The Lambda function and its execution role remain unchanged.

### Step 2 — Verify Missing Permission

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

If no resource-based statements remain, the Lambda service may return:

```text
ResourceNotFoundException
```

This indicates the resource-based policy is absent. It does not mean the Lambda function itself was deleted.

### Step 3 — Verify Lambda Still Exists

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime,Role:Role}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Role": "arn:aws:iam::123456789012:role/api-lab04-lambda-role"
}
```

### Step 4 — Save Broken Permission Evidence

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab04-broken-policy.json 2>&1 || true
```

Review the output before using it as incident evidence.

### Fault Injection Summary

| Component | State |
|---|---|
| REST API | Deployed |
| GET /orders | Configured |
| Lambda proxy integration | Correct |
| Lambda function | Active |
| Lambda execution role | Present |
| Lambda resource-based permission | Missing |
| API Gateway invocation | Denied |
| Expected HTTP response | 500 |

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
  "message": "Internal server error"
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
  echo "SUCCESS: API Gateway integration failure reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 5 — Validate Error Payload

```bash
python3 - <<'PY'
import json

with open("broken-response.json") as file:
    response = json.load(file)

assert response["message"] == "Internal server error"

print("SUCCESS: Gateway-generated error confirmed")
PY
```

### Broken-State Findings

| Check | Expected Result |
|---|---|
| GET /orders | Exists |
| API stage | Deployed |
| Integration | Configured |
| Lambda function | Active |
| Direct invocation | Successful for authorized caller |
| API Gateway invocation | Rejected |
| Lambda permission | Missing |
| API response | HTTP 500 |
| Root cause | Service invocation authorization |

---

## 17. Investigate CloudWatch Logs

### Step 1 — Inspect Recent Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Because the API Gateway invocation is rejected before the Lambda handler executes, the failed API request is not expected to generate a new Lambda application log.

Logs from earlier successful requests may still appear.

### Step 2 — Search for Successful Executions

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB04_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

The existing successful log messages demonstrate that the function previously executed.

They do not prove the failing request reached Lambda.

### Step 3 — Inspect Recent Lambda Invocations

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION"
```

The rejected request is not expected to execute the Lambda handler.

CloudWatch metrics are aggregated, delayed, and may include baseline invocations.

### Step 4 — Save CloudWatch Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab04-cloudwatch-log-evidence.json
```

### Findings

The investigation should establish that:

1. Lambda previously executed successfully.
2. API Gateway now returns HTTP 500.
3. The failing request does not execute the Lambda handler.
4. The Lambda function remains healthy.
5. The invocation authorization must be investigated.

**Key Lesson:** An API Gateway error without a corresponding Lambda application log can indicate that the request failed before the Lambda handler started.

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

### Step 4 — Compare Integration URI

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query uri \
  --output text \
  --region "$AWS_REGION"
```

Compare this URI with:

```bash
echo "$INTEGRATION_URI"
```

### Step 5 — Inspect Lambda Function

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    State:State,
    Runtime:Runtime,
    LastUpdateStatus:LastUpdateStatus,
    Role:Role
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 6 — Test Lambda Directly

```bash
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  direct-lambda-response.json \
  --region "$AWS_REGION"
```

Inspect:

```bash
cat direct-lambda-response.json | jq .
```

Expected Lambda payload:

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json",
    "Cache-Control": "no-store"
  },
  "isBase64Encoded": false,
  "body": "{\"message\": \"Orders retrieved successfully\", \"orders\": [...]}"
}
```

The `...` above is abbreviated illustrative output. Actual JSON contains the full order records.

This direct invocation requires the AWS CLI identity to have permission to invoke the function.

### Step 7 — Inspect Lambda Resource Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected finding:

```text
Resource-based invocation permission missing
```

### Step 8 — Compare With Healthy Policy

```bash
cat lab04-healthy-policy.json | jq -r '.Policy' | jq .
```

Look for:

```text
Sid = AllowAPIGatewayLab04

Principal = apigateway.amazonaws.com

Action = lambda:InvokeFunction
```

### Investigation Summary

| Component | Finding |
|---|---|
| API resource | Correct |
| HTTP method | Correct |
| Deployment stage | Correct |
| Lambda integration URI | Correct |
| Lambda function | Active |
| Direct Lambda test | Successful |
| Lambda execution role | Correct |
| Lambda resource policy | Permission missing |
| API Gateway invocation | Rejected |
| HTTP 500 source | Integration authorization failure |

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

For a REST API using API-name metric dimensions, CloudWatch may report the API-level metric. Availability and granularity depend on the API configuration.

Expected: a nonzero datapoint after CloudWatch publishes the error metric.

### Step 3 — Inspect Lambda Invocations

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

### Step 4 — Inspect Lambda Errors

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

### Step 5 — Save API Gateway Metric Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value="$REST_API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > lab04-api-5xx-metric.json
```

### Step 6 — Save Lambda Invocation Evidence

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value="$FUNCTION_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --region "$AWS_REGION" \
  > lab04-lambda-invocations-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 5XXError | Increases |
| Lambda Invocations | No handler execution from rejected requests |
| Lambda Errors | No runtime error caused by rejected request |
| Lambda application logs | No new handler log from rejected request |
| API HTTP response | 500 |

CloudWatch metric publishing may be delayed.

A missing or empty datapoint immediately after testing is not enough to confirm that no request occurred.

---

## 20. Root Cause Analysis

### Root Cause

The API Gateway–Lambda integration failed because the required Lambda resource-based invocation permission was removed.

API Gateway remained correctly configured.

The Lambda function was healthy and could execute independently.

However, Lambda did not authorize API Gateway to invoke it.

The request was rejected before application execution.

### Root Cause Diagram

```text
GET /dev/orders
       |
       v
Amazon API Gateway
       |
       v
Lambda Proxy Integration
       |
       v
Lambda Invoke Request
       |
       v
Lambda Resource-Based Policy
       |
       v
Required Permission Missing
       |
       v
Invocation Rejected
       |
       v
Lambda Handler Not Executed
       |
       v
API Gateway Integration Error
       |
       v
HTTP 500 Internal Server Error
```

### Five Whys

**Why 1 — Why did the API return HTTP 500?**

API Gateway could not successfully invoke the Lambda backend.

**Why 2 — Why could API Gateway not invoke Lambda?**

The Lambda service rejected the invocation request.

**Why 3 — Why was the invocation rejected?**

The necessary resource-based permission was missing.

**Why 4 — Why was the permission missing?**

The invocation permission was removed during the simulated infrastructure configuration change.

**Why 5 — How can this incident be prevented?**

Manage invocation policies through reviewed Infrastructure as Code, enforce least privilege, monitor permission changes, and test API integration after deployment.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-004 |
| HTTP Error | 500 |
| API Resource | /orders |
| Method | GET |
| Lambda State | Active |
| Direct Invocation | Successful |
| Integration URI | Correct |
| Missing Permission | `lambda:InvokeFunction` |
| Root Cause | Missing Lambda resource policy |
| Remediation | Restore invocation permission |
| Code Changes | None |
| API Redeployment | Not required |

---

## 21. Remediation — Restore Lambda Permission

### Step 1 — Restore Least-Privilege Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "$SOURCE_ARN" \
  --source-account "$ACCOUNT_ID" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Permission

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Expected policy components:

```text
Effect: Allow

Principal: apigateway.amazonaws.com

Action: lambda:InvokeFunction

SourceArn: matching API execution ARN
```

### Step 3 — Save Recovered Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  > lab04-recovered-policy.json
```

### Step 4 — Validate Policy Statement

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" \
  | jq --arg SID "$PERMISSION_SID" \
    '.Statement[] | select(.Sid == $SID)'
```

### Why API Gateway Redeployment Is Not Required

The following configurations remain unchanged:

```text
REST API
GET method
Resource path
Lambda integration URI
API stage
```

Only the Lambda resource-based policy changes.

Therefore, a new API Gateway deployment is normally unnecessary.

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

print("SUCCESS: API Gateway-Lambda integration restored")
PY
```

### Step 4 — Verify CloudWatch Recovery Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB04_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
LAB04_ORDER_SUCCESS count=2
```

### Step 5 — Save Recovery Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB04_ORDER_SUCCESS"' \
  --output json \
  --region "$AWS_REGION" \
  > lab04-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Healthy | Healthy |
| GET method | Correct | Correct |
| Lambda function | Active | Active |
| Lambda integration | Configured | Configured |
| Invocation permission | Missing | Restored |
| Lambda handler | Not reached by API | Executed |
| CloudWatch application log | No new handler execution | ORDER_SUCCESS |
| HTTP status | 500 | 200 |
| Application code | Unchanged | Unchanged |
| API deployment | Unchanged | Unchanged |

**Recovery is verified when the original GET request returns HTTP 200 and the Lambda handler successfully processes the request.**

---

## 23. Additional Diagnostic — Integration Failure Scenarios

### Scenario 1 — Missing Lambda Invocation Permission

**Symptom:**

```http
HTTP/2 500
```

**Investigation:**

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME"
```

**Remediation:** Restore the appropriate invocation permission.

### Scenario 2 — Incorrect Lambda Function ARN

**Symptom:** API Gateway attempts to invoke an incorrect or nonexistent Lambda function.

**Investigation:**

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET
```

Compare the configured ARN against the actual Lambda function ARN.

**Remediation:** Correct the integration URI and deploy the updated REST API configuration.

### Scenario 3 — Invalid Proxy Response

Incorrect:

```python
def lambda_handler(event, context):
    return {
        "message": "Success"
    }
```

The response does not contain the required proxy response fields.

Typical result:

```http
HTTP/2 502
```

Correct:

```python
def lambda_handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": '{"message":"Success"}'
    }
```

### Scenario 4 — Unhandled Lambda Exception

```python
def lambda_handler(event, context):
    raise RuntimeError("Backend failure")
```

Typical API Gateway Lambda proxy response:

```http
HTTP/2 502
```

### Scenario 5 — Integration Timeout

A Lambda backend may take longer than the configured API Gateway integration timeout.

Possible causes:

```text
Slow database queries
Network connectivity failure
External API latency
Excessive backend processing
```

Investigate:

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{Timeout:Timeout,MemorySize:MemorySize}'
```

Also inspect the API Gateway integration timeout and latency metrics.

### Scenario 6 — API Stage Not Redeployed

Changing the integration URI or API method configuration requires deployment of the relevant REST API changes.

Investigate:

```bash
aws apigateway get-stage \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME"
```

### Troubleshooting Comparison

| Failure | Typical HTTP Error | Investigation |
|---|---|---|
| Missing invoke permission | 500 | Lambda resource policy |
| Incorrect integration ARN | 500 | API Gateway integration |
| Invalid proxy response | 502 | Lambda response format |
| Unhandled Lambda exception | 502 | Lambda application logs |
| Integration timeout | 504 | Timeout and duration |
| Undeployed API changes | Varies | Stage and deployment |

---

## 24. Production Troubleshooting Best Practices

### Investigation Checklist

1. Record the failing API URL and HTTP method.
2. Reproduce the error using curl.
3. Inspect the HTTP response headers and body.
4. Confirm the REST API exists.
5. Check the deployed API stage.
6. Verify the resource path.
7. Inspect the HTTP method.
8. Inspect Lambda integration configuration.
9. Verify the integration URI.
10. Verify Lambda function existence.
11. Inspect Lambda function state.
12. Test Lambda independently.
13. Inspect Lambda resource-based policies.
14. Verify the API Gateway service principal.
15. Verify `lambda:InvokeFunction`.
16. Confirm the source ARN matches the API.
17. Review CloudWatch Logs.
18. Compare API Gateway and Lambda metrics.
19. Investigate relevant CloudTrail events.
20. Identify the root cause.
21. Restore least-privilege access.
22. Repeat the original request.
23. Verify HTTP 200.
24. Document the incident.
25. Clean up temporary resources.

### CloudTrail Investigation

CloudTrail can help identify changes to Lambda permissions.

Look up permission changes:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RemovePermission20150331v2 \
  --max-results 20 \
  --region "$AWS_REGION"
```

The Lambda API's CloudTrail event name can differ from the AWS CLI command name. For reliable investigation, inspect recent events associated with the Lambda function and verify the recorded event names in your account.

A broader lookup can start with:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue="$FUNCTION_NAME" \
  --max-results 50 \
  --region "$AWS_REGION"
```

Review:

```text
Event time
Event name
AWS identity
Source IP address
Affected resource
Request parameters
```

CloudTrail event visibility depends on the event type, retention, and trail or event-history configuration.

### Prevention

Use:

- Terraform or CloudFormation.
- IAM least privilege.
- Pull-request reviews.
- Automated integration tests.
- CloudWatch alarms.
- CloudTrail auditing.
- Configuration drift detection.
- Post-deployment API health checks.

---

## 25. Cloud Security Engineering Considerations

### Service-to-Service Authentication

API Gateway must be authorized to invoke Lambda.

A healthy backend does not mean all integrations are authorized.

### Resource-Based Policy Security

Lambda invocation permissions should be restricted to trusted principals and appropriate source ARNs.

### Least Privilege

Prefer permission scoped to:

```text
Specific AWS Account
Specific API ID
Specific Stage
Specific HTTP Method
Specific API Resource
```

### IAM Role Separation

Do not confuse:

```text
Lambda Execution Role
```

with:

```text
Lambda Invocation Permission
```

They solve different authorization problems.

### Configuration Integrity

Unauthorized or accidental changes to Lambda resource policies can cause outages or expand access.

Use reviewed Infrastructure as Code.

### Monitoring

Track:

```text
API Gateway 5XXError

Lambda Invocations

Lambda Errors

API Gateway IntegrationLatency

Lambda application logs

CloudTrail permission changes
```

### Security Incident Investigation

When a permission unexpectedly disappears, investigate whether the change came from:

- Manual AWS Console modification.
- AWS CLI command.
- Terraform configuration drift.
- CloudFormation update.
- CI/CD pipeline.
- Automation.
- Unauthorized AWS identity.

Do not assume every permission change is malicious.

### Production Improvements

- Use IAM or another suitable API authorization method.
- Restrict Lambda invocation source ARNs.
- Monitor sensitive IAM and resource-policy changes.
- Protect production infrastructure through code review.
- Test API Gateway integrations automatically.
- Avoid sharing raw AWS account information publicly.

---

## 26. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | API request charges |
| AWS Lambda | Requests and execution duration |
| CloudWatch Logs | Ingestion and storage |
| CloudWatch Metrics | Applicable monitoring charges |
| CloudTrail | Charges may apply for additional logging configurations |
| IAM | No separate standard IAM role charge |

### Cost Optimization

- Use temporary lab resources.
- Keep Lambda memory at 128 MB.
- Avoid unnecessary repeated requests.
- Set seven-day log retention.
- Do not create unused CloudWatch alarms.
- Remove lab resources after testing.

This lab does not require:

```text
EC2
RDS
NAT Gateway
VPC Endpoints
Load Balancers
```

---

## 27. AWS Resource Cleanup

**Warning:** Delete only resources created for Lab 04.

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
Project = API-Gateway-Troubleshooting-Lab04
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
| API stage | Deleted |
| API resources | Deleted |
| Lambda integration | Deleted |
| Lambda function | Deleted |
| Invocation permission | Removed with function |
| IAM execution role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |
| VPC | Not created |

---

## 28. Interview Questions and Answers

### Q1. What is an API Gateway–Lambda integration?

It allows API Gateway to invoke a Lambda function to process an API request and return a response.

### Q2. What caused the integration failure in this lab?

The Lambda resource-based policy was missing the permission allowing API Gateway to invoke the function.

### Q3. Why did API Gateway return HTTP 500?

The Lambda service rejected the invocation because API Gateway was not authorized.

### Q4. What is `lambda:InvokeFunction`?

It is an AWS IAM action that authorizes invoking a Lambda function.

### Q5. What is the difference between a Lambda execution role and a resource-based policy?

The execution role controls what AWS resources Lambda can access. The resource-based policy controls which principals or services may invoke Lambda.

### Q6. Can Lambda be healthy while API Gateway returns HTTP 500?

Yes. The Lambda function may be working correctly, but API Gateway may lack invocation permission.

### Q7. How do you inspect Lambda invocation permissions?

Use:

```bash
aws lambda get-policy \
  --function-name FUNCTION_NAME
```

### Q8. How do you restore API Gateway invoke permission?

Use `aws lambda add-permission` with the API Gateway principal, invocation action, and appropriate source ARN.

### Q9. Why might CloudWatch contain no new Lambda application logs?

If Lambda rejects the invocation before the function handler runs, that failed API request does not execute the application code.

### Q10. Why can Lambda Errors remain zero while API Gateway 5XXError increases?

An invocation may be rejected before Lambda executes. The resulting API Gateway failure does not necessarily create a Lambda runtime error.

### Q11. Does restoring Lambda permissions require API Gateway redeployment?

Normally no, because the API Gateway integration configuration remains unchanged.

### Q12. What does `AWS_PROXY` mean?

It means API Gateway uses Lambda proxy integration, forwarding request information to Lambda and using the function's structured proxy response.

### Q13. Why does a GET API method use POST for Lambda integration?

API Gateway uses POST to call the Lambda invocation API, even when the incoming client request uses GET.

### Q14. How would you prevent this incident?

Manage Lambda resource policies through Infrastructure as Code, restrict changes, require reviews, monitor configuration changes, and test integrations after deployment.

### Q15. How would you explain this lab in an interview?

I created an Amazon API Gateway REST API connected to a Python AWS Lambda function.

I configured the Lambda execution role and resource-based invocation policy, then deployed the API and confirmed that the orders endpoint returned HTTP 200.

Next, I intentionally removed the Lambda permission that allowed API Gateway to invoke the function.

The API began returning HTTP 500 even though the Lambda function remained healthy.

I investigated the API Gateway resources, HTTP method, integration URI, Lambda function state, resource-based policy, CloudWatch Logs, and metrics.

I also tested the function independently to confirm that the application itself was working.

The investigation showed that API Gateway lacked the required `lambda:InvokeFunction` permission.

I restored the permission using a source-restricted Lambda resource policy.

After remediation, the same API request returned HTTP 200 without changing the Lambda application code or redeploying API Gateway.

Finally, I verified the recovery and removed all temporary AWS resources.

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
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab04-resources.env
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── direct-lambda-response.json
│   ├── lab04-healthy-policy.json
│   ├── lab04-broken-policy.json
│   ├── lab04-recovered-policy.json
│   ├── lab04-cloudwatch-log-evidence.json
│   ├── lab04-recovered-cloudwatch-evidence.json
│   ├── lab04-api-5xx-metric.json
│   └── lab04-lambda-invocations-metric.json
│
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
| lambda-trust-policy.json | Lambda execution-role trust policy |
| function.zip | Generated Lambda deployment package |
| lab04-resources.env | Local AWS resource variables |
| baseline-headers.txt | Healthy HTTP headers |
| baseline-response.json | Healthy API response |
| broken-headers.txt | HTTP 500 headers |
| broken-response.json | Gateway error response |
| recovered-headers.txt | Recovered HTTP headers |
| recovered-response.json | Recovered API response |
| direct-lambda-response.json | Direct Lambda invocation test |
| lab04-healthy-policy.json | Original invocation policy |
| lab04-broken-policy.json | Missing permission evidence |
| lab04-recovered-policy.json | Restored invocation policy |
| lab04-cloudwatch-log-evidence.json | CloudWatch investigation evidence |
| lab04-recovered-cloudwatch-evidence.json | Successful Lambda execution logs |
| lab04-api-5xx-metric.json | API Gateway error metrics |
| lab04-lambda-invocations-metric.json | Lambda invocation metrics |

### Recommended Public GitHub Files

```text
04-api-gateway-lambda-integration-failure/
├── README.md
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 04
04-api-gateway-lambda-integration-failure/function.zip
04-api-gateway-lambda-integration-failure/lab04-resources.env
04-api-gateway-lambda-integration-failure/lab04-*.json
04-api-gateway-lambda-integration-failure/*-headers.txt
04-api-gateway-lambda-integration-failure/*-response.json

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

Review all files before committing. Do not publish credentials, sensitive logs, account-specific infrastructure details, or unreviewed incident evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how an Amazon API Gateway REST API can fail because of missing service-to-service invocation authorization.

We created a REST API integrated with a Python Lambda function.

We first configured the Lambda execution role and resource-based policy correctly.

The API successfully invoked Lambda and returned HTTP 200.

Next, we intentionally removed the Lambda permission allowing API Gateway to invoke the function.

The API began returning HTTP 500, although the function itself remained healthy.

We investigated API Gateway configuration, Lambda function state, resource-based policies, CloudWatch Logs, and CloudWatch metrics.

The investigation identified missing `lambda:InvokeFunction` authorization as the root cause.

We restored the resource-based permission using the API Gateway service principal and a restricted source ARN.

The API returned HTTP 200 again without changing the application code or API Gateway deployment.

Finally, the lab provided a cleanup procedure for all temporary AWS resources.

**Key Lesson:** A healthy Lambda function does not guarantee a working API Gateway integration. Engineers must verify both backend functionality and service-to-service authorization.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 500 troubleshooting
- Lambda proxy integration
- Python 3.13
- AWS IAM execution roles
- Lambda resource-based policies
- `lambda:InvokeFunction`
- Service-to-service authorization
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch API metrics
- CloudWatch Lambda metrics
- CloudTrail investigation
- Production fault injection
- Root cause analysis
- Least-privilege remediation
- Recovery verification
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-004 |
| Scenario | API Gateway–Lambda Integration Failure |
| REST API | api-lab04-integration-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab04-order-handler |
| Broken State | Invocation permission missing |
| Healthy State | Invocation permission present |
| Broken API Response | HTTP 500 |
| Root Cause | Missing Lambda resource policy |
| Remediation | Restore `lambda:InvokeFunction` |
| Recovery Response | HTTP 200 |
| Code Changes | None |
| API Gateway Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Effective serverless troubleshooting requires understanding API Gateway integrations, Lambda invocation policies, CloudWatch observability, and least-privilege service authorization.

---

## Official AWS Documentation

- [AWS Lambda — Granting API Gateway Access to Lambda](https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway.html)
- [AWS Lambda — Resource-Based Policies](https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html)
- [API Gateway — Lambda Proxy Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [API Gateway — Handle Lambda Errors](https://docs.aws.amazon.com/apigateway/latest/developerguide/handle-errors-in-lambda-integration.html)
- [API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS CLI — Lambda Add Permission](https://docs.aws.amazon.com/cli/latest/reference/lambda/add-permission.html)
- [AWS CLI — Lambda Get Policy](https://docs.aws.amazon.com/cli/latest/reference/lambda/get-policy.html)
- [AWS CLI — Lambda Remove Permission](https://docs.aws.amazon.com/cli/latest/reference/lambda/remove-permission.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)