# Lab 06 — Amazon API Gateway Missing Authentication Token

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP **403 Forbidden — Missing Authentication Token** error in an Amazon API Gateway REST API integrated with AWS Lambda.

In production, applications frequently use API Gateway as the entry point for backend services. Frontend applications, mobile clients, and internal services send HTTP requests to API Gateway, which routes those requests to the appropriate backend.

When API Gateway receives a request for an unsupported resource or HTTP method, it may return:

```json
{
  "message": "Missing Authentication Token"
}
```

Although the error message mentions authentication, the problem does not necessarily involve missing credentials.

For REST APIs, API Gateway can generate this response when the requested resource path or HTTP method does not match the deployed API configuration.

In this lab, we create a REST API exposing a `GET /orders` endpoint backed by a Python Lambda function.

We first verify that the API returns HTTP 200 and successfully retrieves order information.

Next, we intentionally reproduce two production routing failures.

**Failure 1 — Incorrect Resource Path**

We change the requested endpoint from `/orders` to `/order`.

API Gateway cannot find the requested resource and returns HTTP 403 with the message `Missing Authentication Token`.

**Failure 2 — Unsupported HTTP Method**

We send an HTTP POST request to `/orders`, even though the API supports only GET.

API Gateway again returns HTTP 403.

We investigate the failures using AWS CLI, curl, API Gateway resources, HTTP methods, deployment stages, Lambda configuration, CloudWatch Logs, and CloudWatch metrics.

After identifying the incorrect client requests as the root causes, we restore the correct resource path and HTTP method.

We repeat the original API request and verify HTTP 200 without modifying the Lambda application or redeploying API Gateway.

Finally, we document the incident, review production security considerations, and remove the temporary AWS resources.

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
Test Lambda Independently
           |
           v
Create API Gateway REST API
           |
           v
Create /orders Resource
           |
           v
Configure GET Method
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
Fault Injection 1
           |
           v
Change /orders to /order
           |
           v
Send GET /dev/order
           |
           v
API Gateway Cannot Match Resource
           |
           v
HTTP 403 Missing Authentication Token
           |
           v
Fault Injection 2
           |
           v
Send POST /dev/orders
           |
           v
API Gateway Cannot Match HTTP Method
           |
           v
HTTP 403 Missing Authentication Token
           |
           v
Investigate API Gateway Resources
           |
           v
Inspect GET and POST Methods
           |
           v
Verify Deployment Stage
           |
           v
Verify Lambda Function Health
           |
           v
Inspect CloudWatch Logs and Metrics
           |
           v
Identify Routing Mismatch
           |
           v
Restore Correct GET /dev/orders Request
           |
           v
Verify HTTP 200
           |
           v
Confirm Lambda Execution
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-006 |
| Lab Name | Missing Authentication Token |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab06-auth-token-troubleshooting` |
| API Resource | `/orders` |
| Supported HTTP Method | GET |
| Unsupported HTTP Method | POST |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab06-order-handler` |
| Lambda Execution Role | `api-lab06-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Healthy Endpoint | `GET /dev/orders` |
| Broken Endpoint | `GET /dev/order` |
| Broken Method | `POST /dev/orders` |
| Healthy Response | HTTP 200 |
| Broken Response | HTTP 403 |
| Error Message | Missing Authentication Token |
| CloudWatch API Metric | `4XXError` |
| CloudWatch Log Marker | `LAB06_ORDER_SUCCESS` |
| Root Cause | Incorrect API resource or HTTP method |
| Remediation | Correct client request configuration |
| Lambda Code Changes | Not required |
| API Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand HTTP 403 Forbidden.
- Understand API Gateway's Missing Authentication Token error.
- Distinguish routing failures from authentication failures.
- Configure an Amazon API Gateway REST API.
- Deploy a Python Lambda backend.
- Configure Lambda proxy integration.
- Understand API Gateway resources and methods.
- Understand API deployment stages.
- Reproduce HTTP 403 using an invalid resource path.
- Reproduce HTTP 403 using an unsupported HTTP method.
- Investigate API Gateway routing configuration.
- Verify Lambda execution independently.
- Inspect REST API methods using AWS CLI.
- Inspect deployed API stages.
- Compare successful and failed HTTP requests.
- Investigate CloudWatch Logs.
- Analyze API Gateway 4XX metrics.
- Identify the true root cause.
- Apply targeted remediation.
- Verify recovery without unnecessary redeployment.
- Apply secure API troubleshooting practices.
- Clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application using Amazon API Gateway and AWS Lambda.

The company exposes the following backend API:

```http
GET /dev/orders
```

The endpoint retrieves order information from a Python Lambda function.

Under normal conditions, the application returns HTTP 200 and order records.

Example:

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

During a frontend configuration deployment, the API endpoint is accidentally changed.

The correct resource:

```text
/dev/orders
```

is replaced with:

```text
/dev/order
```

After deployment, customers begin receiving:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Missing Authentication Token"
}
```

The development team initially suspects an authentication or authorization problem because the error mentions a missing token.

However, the REST API does not require authentication for this temporary lab endpoint.

The Cloud Engineering team investigates.

The engineer verifies that:

- The REST API exists.
- The `dev` deployment stage exists.
- The `/orders` resource is configured.
- The GET method exists.
- Lambda proxy integration is configured correctly.
- API Gateway has permission to invoke Lambda.
- The Lambda function is Active.
- Direct Lambda invocation succeeds.
- Requests to `/order` do not match a deployed resource.
- POST requests to `/orders` do not match a supported method.

The engineer determines that the failure originates from incorrect client routing rather than an authentication problem.

After correcting the request to `GET /dev/orders`, the API returns HTTP 200.

### Incident Symptoms

- API Gateway returns HTTP 403.
- The response contains `Missing Authentication Token`.
- The Lambda function remains healthy.
- Direct Lambda invocation succeeds.
- The correct API endpoint returns HTTP 200.
- The incorrect resource path returns HTTP 403.
- Unsupported HTTP methods return HTTP 403.
- Failed requests do not execute the Lambda handler.
- Correcting the API request resolves the incident.

### Business Impact

An incorrect API route may cause:

- Failed customer requests.
- Broken frontend application functionality.
- Unavailable order information.
- Interrupted business workflows.
- Increased API Gateway 4XX errors.
- Failed frontend-to-backend communication.
- Increased operational support tickets.
- Delayed customer transactions.
- Confusion during incident investigation.

### Objective

Identify whether the Missing Authentication Token error originates from authentication, authorization, API routing, or deployment configuration.

Restore the correct client request and verify HTTP 200 without weakening API security or making unnecessary infrastructure changes.

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
               /orders Resource
                      |
                      v
                 GET Method
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
             LAB06_ORDER_SUCCESS
                      |
                      v
               Orders Retrieved
                      |
                      v
                 HTTP 200 OK
```

### Broken Architecture — Incorrect Resource

```text
                  API Client
                      |
                      v
                GET /dev/order
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
               Resource Matching
                      |
                      v
             /order Does Not Exist
                      |
                      v
              No Matching Resource
                      |
                      v
              Gateway Rejects Request
                      |
                      v
                  HTTP 403
                      |
                      v
           Missing Authentication Token
```

### Broken Architecture — Unsupported Method

```text
                  API Client
                      |
                      v
               POST /dev/orders
                      |
                      v
               Amazon API Gateway
                      |
                      v
                 REST API
                      |
                      v
                /orders Resource
                      |
                      v
               Method Matching
                      |
                      v
              Only GET Is Configured
                      |
                      v
               POST Not Supported
                      |
                      v
                  HTTP 403
                      |
                      v
           Missing Authentication Token
```

### Recovered Architecture

```text
                  API Client
                      |
                      v
              Correct Client Request
                      |
                      v
                GET /dev/orders
                      |
                      v
               Amazon API Gateway
                      |
                      v
              Resource /orders Exists
                      |
                      v
               GET Method Exists
                      |
                      v
             Lambda Proxy Integration
                      |
                      v
                 AWS Lambda
                      |
                      v
                Order Response
                      |
                      v
                 HTTP 200 OK
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives and routes API requests |
| REST API | Defines resources and methods |
| `/orders` Resource | Exposes order information |
| GET Method | Supports order retrieval |
| `dev` Stage | Hosts deployed API configuration |
| Lambda Proxy Integration | Invokes Lambda |
| AWS Lambda | Processes order requests |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Allows API Gateway invocation |
| CloudWatch Logs | Records backend execution |
| API Gateway 4XXError | Measures client-side API errors |
| curl | Reproduces HTTP failures |
| AWS CLI | Investigates API configuration |

---

## 4. Understanding Missing Authentication Token

### What Is HTTP 403?

HTTP 403 Forbidden indicates that the server understood the request but refuses to fulfill it.

In API Gateway REST APIs, the default `MISSING_AUTHENTICATION_TOKEN` gateway response uses HTTP 403.

However, this error does not always indicate a missing credential.

### Why Does API Gateway Return Missing Authentication Token?

Common causes include:

1. Incorrect API resource path.
2. Unsupported HTTP method.
3. Incorrect API deployment stage.
4. Resource or method not deployed.
5. Authentication-related conditions in certain configurations.

For this lab, the causes are incorrect API routing and unsupported methods.

### Example 1 — Correct Resource

Configured API:

```http
GET /dev/orders
```

Client request:

```http
GET /dev/orders
```

Expected:

```http
HTTP/2 200
```

### Example 2 — Incorrect Resource

Configured:

```http
GET /dev/orders
```

Requested:

```http
GET /dev/order
```

Expected:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Missing Authentication Token"
}
```

### Example 3 — Unsupported HTTP Method

Configured:

```http
GET /dev/orders
```

Requested:

```http
POST /dev/orders
```

Expected:

```http
HTTP/2 403
```

### Authentication Failure vs. Routing Failure

| Scenario | Possible Response | Investigation |
|---|---|---|
| Incorrect resource | 403 | API resource path |
| Unsupported method | 403 | API methods |
| Incorrect stage | 403 | Deployment stage |
| Missing IAM signature | 403 | IAM authorization |
| Invalid API key | 403 | API key and usage plan |
| Missing authorizer token | 401 | Authorizer configuration |
| Correct unauthenticated GET | 200 | Backend response |

The exact HTTP status depends on the API configuration and gateway response customization.

### Important Concept

**Never assume that `Missing Authentication Token` means you must disable authentication or add credentials.**

First verify the requested API path, HTTP method, stage, and deployment.

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
lambda:InvokeFunction
lambda:AddPermission
lambda:GetPolicy
lambda:ListTags
lambda:DeleteFunction

apigateway:POST
apigateway:GET
apigateway:DELETE

logs:DescribeLogGroups
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

These are relevant IAM actions rather than a complete policy document. Production policies should restrict access to approved resources and actions.

### Safety Rules

- Use a dedicated REST API.
- Do not modify production APIs.
- Do not disable existing production authorizers.
- Do not connect to real order databases.
- Use fabricated customer data.
- Avoid exposing AWS credentials.
- Do not publish sensitive CloudWatch logs.
- Verify resource tags before cleanup.
- Delete temporary AWS resources after testing.

### API Authorization

This lab uses:

```text
Authorization = NONE
```

This is appropriate only for the temporary endpoint containing fabricated data.

Production APIs should implement suitable authentication and authorization.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 06-missing-authorization-token

cd 06-missing-authorization-token
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

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab06"

export API_NAME="api-lab06-auth-token-troubleshooting"

export FUNCTION_NAME="api-lab06-order-handler"

export ROLE_NAME="api-lab06-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab06"
```

### Step 4 — Save Environment Variables

```bash
cat > lab06-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export API_NAME="$API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STAGE_NAME="$STAGE_NAME"
export PERMISSION_SID="$PERMISSION_SID"
EOF

chmod 600 lab06-resources.env
```

Restore variables when needed:

```bash
source lab06-resources.env
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

Do not overwrite unrelated existing resources.

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
  --description "API Gateway Lab 06 Lambda execution role" \
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

### Understanding the Execution Role

The Lambda execution role allows the function to write logs to CloudWatch.

It does not determine whether an API Gateway resource or HTTP method exists.

Therefore, this role is not the root cause of our intentionally incorrect API requests.

---

## 8. Create the Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info(
        "LAB06_ORDER_REQUEST method=%s path=%s",
        event.get("httpMethod"),
        event.get("path")
    )

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

    logger.info(
        "LAB06_ORDER_SUCCESS count=%s",
        len(orders)
    )

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
EOF
```

### Understanding the Application

The function receives API Gateway request information.

It records:

```text
LAB06_ORDER_REQUEST
```

and:

```text
LAB06_ORDER_SUCCESS
```

in CloudWatch Logs.

It returns fabricated order records.

The application does not contain any intentional errors.

This allows the lab to isolate failures originating from API Gateway resource and method matching.

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

IAM role propagation can take a short time. If Lambda cannot assume the newly created role immediately, retry after the role becomes available.

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

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab06-resources.env
```

### Step 4 — Verify Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime,Timeout:Timeout}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13",
  "Timeout": 10
}
```

---

## 10. Test Lambda Independently

### Step 1 — Invoke Lambda Directly

```bash
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  lambda-response.json \
  --region "$AWS_REGION"
```

This requires the AWS CLI identity to have `lambda:InvokeFunction` permission.

### Step 2 — Inspect the Response

```bash
cat lambda-response.json | jq .
```

Expected response structure:

```json
{
  "statusCode": 200,
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"message\": \"Orders retrieved successfully\", \"orders\": [{\"order_id\": \"1001\", \"status\": \"processing\"}, {\"order_id\": \"1002\", \"status\": \"shipped\"}]}"
}
```

### Step 3 — Validate Lambda Response

```bash
python3 - <<'PY'
import json

with open("lambda-response.json") as file:
    response = json.load(file)

assert response["statusCode"] == 200

body = json.loads(response["body"])

assert len(body["orders"]) == 2

print("SUCCESS: Lambda backend verified")
PY
```

### Investigation Value

A successful direct invocation establishes that the Lambda application can execute under an authorized identity.

It does not prove the API Gateway resource path or HTTP method is correct.

---

## 11. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab06 Missing Authentication Token troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_ID"

echo "export API_ID='$API_ID'" >> lab06-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_ID"

echo "export ROOT_ID='$ROOT_ID'" >> lab06-resources.env
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

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab06-resources.env
```

### Step 4 — Configure GET Method

```bash
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --authorization-type NONE \
  --region "$AWS_REGION"
```

### Step 5 — Verify GET Method

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

Only GET is configured for this resource.

---

## 12. Configure Lambda Proxy Integration

### Step 1 — Generate Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Configure Integration

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

### Step 5 — Verify Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --query Policy \
  --output text \
  --region "$AWS_REGION" | jq .
```

Confirm:

```text
Principal = apigateway.amazonaws.com

Action = lambda:InvokeFunction
```

The configured API Gateway invocation permission applies to the intended GET endpoint.

---

## 13. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab06 healthy orders API deployment" \
  --region "$AWS_REGION"
```

### Step 2 — Verify Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Generate Working API URL

```bash
export API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/orders"

echo "$API_URL"

echo "export API_URL='$API_URL'" >> lab06-resources.env
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

### Step 4 — Verify API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].{Path:path,Methods:resourceMethods}' \
  --output json \
  --region "$AWS_REGION"
```

The `/orders` resource should list GET as a supported method.

---

## 14. Verify Healthy Baseline

### Step 1 — Send Correct GET Request

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

### Step 5 — Check Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected application logs:

```text
LAB06_ORDER_REQUEST method=GET path=/orders

LAB06_ORDER_SUCCESS count=2
```

### Baseline Findings

| Component | Expected Result |
|---|---|
| REST API | Deployed |
| `/orders` resource | Exists |
| GET method | Exists |
| Lambda integration | Healthy |
| Lambda invocation | Successful |
| HTTP response | 200 |

This baseline establishes that the infrastructure is working before introducing invalid client requests.

---

## 15. Fault Injection — Incorrect API Resource Path

### Step 1 — Define Incorrect URL

The correct resource is:

```text
/orders
```

We intentionally request:

```text
/order
```

Configure the broken URL:

```bash
export BROKEN_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/order"

echo "$BROKEN_URL"
```

### Step 2 — Send Incorrect GET Request

```bash
curl -i "$BROKEN_URL"
```

Expected:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Missing Authentication Token"
}
```

### Step 3 — Save Broken Response

```bash
curl -sS \
  -D broken-path-headers.txt \
  -o broken-path-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$BROKEN_URL"
```

Expected:

```text
HTTP Status: 403
```

### Step 4 — Inspect Error

```bash
python3 -m json.tool broken-path-response.json
```

### Step 5 — Validate Error Payload

```bash
python3 - <<'PY'
import json

with open("broken-path-response.json") as file:
    response = json.load(file)

assert response["message"] == "Missing Authentication Token"

print("SUCCESS: Incorrect resource path reproduced")
PY
```

### Step 6 — Verify HTTP Status

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$BROKEN_URL")

if [ "$STATUS" = "403" ]; then
  echo "SUCCESS: HTTP 403 reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Fault Injection Findings

| Component | State |
|---|---|
| API Gateway | Healthy |
| Lambda backend | Healthy |
| Requested resource | `/order` |
| Configured resource | `/orders` |
| Resource match | Failed |
| Lambda invocation | Not reached |
| HTTP response | 403 |
| Error | Missing Authentication Token |

---

## 16. Fault Injection — Unsupported HTTP Method

### Step 1 — Verify Supported Method

The API supports:

```http
GET /dev/orders
```

The API does not support:

```http
POST /dev/orders
```

### Step 2 — Send Unsupported POST Request

```bash
curl -i -X POST "$API_URL"
```

Expected:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Missing Authentication Token"
}
```

### Step 3 — Save Broken Method Response

```bash
curl -sS \
  -D broken-method-headers.txt \
  -o broken-method-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  -X POST "$API_URL"
```

Expected:

```text
HTTP Status: 403
```

### Step 4 — Inspect Response

```bash
python3 -m json.tool broken-method-response.json
```

### Step 5 — Validate Error

```bash
python3 - <<'PY'
import json

with open("broken-method-response.json") as file:
    response = json.load(file)

assert response["message"] == "Missing Authentication Token"

print("SUCCESS: Unsupported HTTP method reproduced")
PY
```

### Step 6 — Verify POST Method Is Missing

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method POST \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Broken-State Findings

| Check | Expected Result |
|---|---|
| GET /orders | Configured |
| POST /orders | Not configured |
| GET request | HTTP 200 |
| POST request | HTTP 403 |
| Error message | Missing Authentication Token |
| Lambda invocation from POST | Not reached |
| Root cause | Unsupported HTTP method |

---

## 17. Investigate API Gateway Configuration

### Step 1 — Inspect REST API

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].{Path:path,ID:id}' \
  --output table \
  --region "$AWS_REGION"
```

Expected paths:

```text
/
/orders
```

The `/order` resource should not appear.

### Step 3 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 4 — Inspect POST Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method POST \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 5 — Inspect Lambda Integration

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

Remember that the Lambda integration's backend POST method is not the same as a public POST method on the REST API.

### Step 6 — Inspect Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Save Resource Configuration Evidence

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --output json \
  --region "$AWS_REGION" \
  > lab06-api-resources-evidence.json
```

### Step 8 — Save Method Configuration Evidence

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --output json \
  --region "$AWS_REGION" \
  > lab06-get-method-evidence.json
```

### Investigation Summary

| Component | Finding |
|---|---|
| REST API | Exists |
| API stage | Deployed |
| `/orders` resource | Exists |
| `/order` resource | Missing |
| GET method | Exists |
| POST method | Missing |
| Lambda integration | Correct |
| API routing | Incorrect client request |
| HTTP 403 source | API Gateway |

---

## 18. Investigate Lambda and CloudWatch Logs

### Step 1 — Verify Lambda Function

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{
    FunctionName:FunctionName,
    State:State,
    Runtime:Runtime,
    Role:Role
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected state:

```text
Active
```

### Step 2 — Verify Lambda Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

The policy should allow API Gateway to invoke Lambda through the configured GET route.

### Step 3 — Inspect CloudWatch Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected logs from successful requests:

```text
LAB06_ORDER_REQUEST method=GET path=/orders

LAB06_ORDER_SUCCESS count=2
```

### Step 4 — Search for Successful Execution

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB06_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 5 — Save CloudWatch Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab06-cloudwatch-evidence.json
```

### Important Observation

The incorrect path and unsupported method are rejected during API Gateway routing.

Therefore, the failed requests are not expected to execute the Lambda handler.

However, earlier successful requests and direct Lambda tests may still appear in CloudWatch Logs.

### Findings

1. Lambda remains healthy.
2. Successful GET requests reach Lambda.
3. Incorrect client requests return HTTP 403.
4. Failed route-matching requests do not reach Lambda.
5. The problem originates before backend integration.

---

## 19. Investigate CloudWatch Metrics

### Step 1 — Define Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect API Gateway 4XXError

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

Expected: a nonzero API-level 4XX datapoint after CloudWatch publishes the failed requests, subject to metric availability and aggregation.

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
  --metric-name 4XXError \
  --dimensions Name=ApiName,Value="$API_NAME" \
  --start-time "$START_TIME" \
  --end-time "$END_TIME" \
  --period 60 \
  --statistics Sum \
  --output json \
  --region "$AWS_REGION" \
  > lab06-api-4xx-metric.json
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
  --output json \
  --region "$AWS_REGION" \
  > lab06-lambda-invocations-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 4XXError | Increases |
| Lambda Invocations | No invocation caused by unmatched requests |
| Lambda Errors | No runtime error caused by unmatched requests |
| Lambda Logs | Successful requests only |
| Incorrect GET response | 403 |
| Unsupported POST response | 403 |

CloudWatch metrics may be delayed.

Because the lab includes successful baseline requests and a direct Lambda test, total Lambda invocation counts cannot be attributed exclusively to one request type without additional correlation.

---

## 20. Root Cause Analysis

### Root Cause

The API Gateway REST API returned Missing Authentication Token because the client requests did not match deployed API resources and methods.

The deployed endpoint was:

```http
GET /dev/orders
```

However, the client sent:

```http
GET /dev/order
```

and:

```http
POST /dev/orders
```

Neither request matched the configured endpoint.

API Gateway rejected the requests before Lambda invocation.

### Root Cause Diagram

```text
Client API Request
        |
        v
Amazon API Gateway
        |
        v
REST API Stage
        |
        v
Resource and Method Matching
        |
        +----------------------+
        |                      |
        v                      v
GET /dev/order          POST /dev/orders
        |                      |
        v                      v
Resource Missing        Method Missing
        |                      |
        +-----------+----------+
                    |
                    v
           No Matching Route
                    |
                    v
                HTTP 403
                    |
                    v
       Missing Authentication Token
```

### Five Whys

**Why 1 — Why did the API return HTTP 403?**

The incoming request did not match a deployed API Gateway resource and method.

**Why 2 — Why did route matching fail?**

The client used an incorrect resource path or unsupported HTTP method.

**Why 3 — Why was the client request incorrect?**

The simulated client configuration did not match the deployed REST API contract.

**Why 4 — Why did the error mention authentication?**

API Gateway REST APIs use the default `MISSING_AUTHENTICATION_TOKEN` gateway response for certain unmatched requests, including unsupported resources and methods.

**Why 5 — How can this incident be prevented?**

Use validated endpoint configuration, automated API integration tests, documented API contracts, and deployment verification.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-006 |
| HTTP Error | 403 |
| Error Message | Missing Authentication Token |
| Correct Resource | `/orders` |
| Incorrect Resource | `/order` |
| Supported Method | GET |
| Unsupported Method | POST |
| Lambda State | Active |
| Lambda Integration | Correct |
| Root Cause | Client routing mismatch |
| Remediation | Correct path and HTTP method |
| Lambda Code Changes | None |
| API Redeployment | Not required |

---

## 21. Remediation — Restore Correct Resource Path

### Step 1 — Identify the Correct Resource

Inspect configured resources:

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].path' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
[
  "/",
  "/orders"
]
```

### Step 2 — Restore Correct URL

```bash
export API_URL="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/orders"
```

Verify:

```bash
echo "$API_URL"
```

The URL must end with:

```text
/dev/orders
```

### Step 3 — Send Correct GET Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
```

### Step 4 — Verify Order Response

```bash
curl -sS "$API_URL" | jq .
```

Expected order records should appear.

### Why API Gateway Redeployment Is Not Required

The REST API configuration was already correct.

The issue originated from an incorrect client URL.

No API Gateway resources, methods, integrations, or stages need to be modified.

Therefore, redeployment is unnecessary.

---

## 22. Remediation — Restore Correct HTTP Method

### Step 1 — Inspect Supported Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 2 — Confirm POST Is Unsupported

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method POST \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 3 — Replace POST With GET

Incorrect:

```bash
curl -i -X POST "$API_URL"
```

Correct:

```bash
curl -i -X GET "$API_URL"
```

Expected:

```http
HTTP/2 200
```

### Step 4 — Save Recovered Response

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

### Step 5 — Validate Response

```bash
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: API routing issue resolved")
PY
```

### Important Production Distinction

If an application genuinely requires POST, the correct remediation may be to create and deploy a POST method with an appropriate backend integration.

However, this lab's API contract requires GET.

Adding an unnecessary POST method would expand the API surface without solving the underlying client configuration problem appropriately.

---

## 23. Verify Successful Recovery

### Step 1 — Repeat Original Correct Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
content-type: application/json
```

### Step 2 — Verify Response Body

```bash
python3 -m json.tool recovered-response.json
```

Expected:

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

### Step 3 — Verify HTTP Status Automatically

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "200" ]; then
  echo "SUCCESS: API recovered"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 4 — Verify CloudWatch Recovery Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB06_ORDER_SUCCESS"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
LAB06_ORDER_SUCCESS count=2
```

### Step 5 — Save Recovery Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB06_ORDER_SUCCESS"' \
  --output json \
  --region "$AWS_REGION" \
  > lab06-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Healthy | Healthy |
| Resource requested | `/order` | `/orders` |
| HTTP method | POST or invalid path | GET |
| Resource match | Failed | Successful |
| Method match | Failed | Successful |
| Lambda invocation | Not reached | Successful |
| HTTP status | 403 | 200 |
| Application code | Unchanged | Unchanged |
| API configuration | Unchanged | Unchanged |
| API redeployment | Not required | Not required |

**Recovery is verified when the corrected GET request returns HTTP 200 and CloudWatch confirms successful order retrieval.**

---

## 24. Additional Production Troubleshooting Scenarios

### Scenario 1 — Incorrect Stage Name

Configured stage:

```text
/dev
```

Incorrect request:

```text
/prod/orders
```

Possible result:

```http
HTTP/2 403
```

**Investigation:**

```bash
aws apigateway get-stages \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

**Remediation:** Use the correct deployed stage.

### Scenario 2 — API Resource Not Deployed

A new resource may exist in the API configuration but not in the active deployment.

**Investigation:**

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

**Remediation:** Create a new deployment after confirming the API changes are correct.

### Scenario 3 — Incorrect HTTP Method

The API supports GET, but the client sends POST.

**Investigation:**

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method POST \
  --region "$AWS_REGION"
```

**Remediation:** Correct the client method or deliberately add the required method if supported by the application's API contract.

### Scenario 4 — IAM Authentication Failure

An endpoint configured with `AWS_IAM` authorization requires a correctly signed AWS request from an authorized principal.

**Investigation:** Inspect method authorization settings and the caller's permissions.

**Remediation:** Configure the caller's credentials and SigV4 signing appropriately. Do not disable IAM authorization merely to make the request work.

### Scenario 5 — API Key Failure

A method requiring an API key can return HTTP 403 when the supplied key is invalid or not associated with the required usage plan.

**Investigation:** Inspect API key requirements, usage plans, and stage associations.

**Remediation:** Correct the API key configuration without exposing keys publicly.

### Scenario 6 — Custom Domain API Mapping Error

A request sent through a custom domain may use the wrong API mapping or base path.

**Investigation:** Inspect custom domain mappings and compare them with the execute-api endpoint.

**Remediation:** Correct the API mapping or client URL.

### Common Error Comparison

| Symptom | Possible Cause | Investigation |
|---|---|---|
| HTTP 403 Missing Authentication Token | Wrong resource | API Gateway resources |
| HTTP 403 Missing Authentication Token | Unsupported method | API Gateway methods |
| HTTP 403 Missing Authentication Token | Wrong stage | API stages |
| HTTP 403 | IAM authorization failure | Credentials and IAM policy |
| HTTP 403 | Invalid API key | Usage plan and API key |
| HTTP 401 | Missing authorizer token | Authorization configuration |
| HTTP 500 | Integration configuration failure | API integration |
| HTTP 502 | Lambda execution or proxy response error | Lambda logs |
| HTTP 504 | Integration timeout | Timeout and latency |

---

## 25. Cloud Security Engineering Considerations

### Do Not Confuse Routing With Authentication

The message `Missing Authentication Token` does not automatically indicate a missing credential.

Confirm the resource path and HTTP method before modifying authorization.

### Avoid Disabling Authentication During Troubleshooting

A production engineer should not change:

```text
AWS_IAM
```

to:

```text
NONE
```

simply because an API request returns HTTP 403.

Such a change can unintentionally expose protected API functionality.

### Apply Least Privilege

Lambda resource-based policies should permit only the intended API Gateway invocation sources.

IAM permissions should be restricted to required operations and resources.

### Validate API Contracts

Frontend and backend teams should agree on:

```text
API Base URL
Deployment Stage
Resource Path
HTTP Method
Required Headers
Authentication Method
```

### Manage API Configuration as Code

Use Terraform or CloudFormation to manage:

- REST APIs.
- Resources.
- HTTP methods.
- Integrations.
- Deployment stages.
- Authorization settings.
- Lambda permissions.

### Automated API Testing

CI/CD pipelines should validate supported endpoints after deployment.

Example:

```bash
curl -sS \
  -o /dev/null \
  -w '%{http_code}\n' \
  "$API_URL"
```

Expected:

```text
200
```

### Monitoring

Monitor:

```text
API Gateway 4XXError

API Gateway 5XXError

Lambda Invocations

Lambda Errors

API deployment changes

Application request failures
```

### Auditability

Use CloudTrail and approved deployment records to investigate API configuration changes.

An unexpected route change may result from:

- Manual configuration.
- Incorrect deployment.
- Infrastructure as Code changes.
- CI/CD pipeline errors.
- Client configuration mistakes.

### Security Principle

**Fix the incorrect request rather than weakening security controls.**

---

## 26. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Request charges |
| AWS Lambda | Invocation and execution charges |
| CloudWatch Logs | Ingestion and retention |
| CloudWatch Metrics | Applicable monitoring charges |
| IAM | No separate standard IAM role charge |

### Cost Optimization

- Use temporary resources.
- Keep Lambda memory at 128 MB.
- Limit unnecessary API requests.
- Avoid unnecessary custom monitoring resources.
- Delete the lab after verification.
- Do not create infrastructure unrelated to the incident.

### Services Not Required

```text
EC2

RDS

NAT Gateway

Application Load Balancer

VPC Endpoints
```

The lab uses a simple serverless architecture.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only resources created for Lab 06.

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
Project = API-Gateway-Troubleshooting-Lab06
```

### Step 4 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$API_ID" \
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

If the log group was not created, AWS may report `ResourceNotFoundException`.

### Step 9 — Verify API Deletion

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
| API resources | Deleted |
| Lambda integration | Deleted |
| Lambda function | Deleted |
| Lambda invocation permission | Removed with function |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |
| VPC | Not created |

---

## 28. Interview Questions and Answers

### Q1. What does HTTP 403 mean?

HTTP 403 means the server understands the request but refuses to fulfill it.

### Q2. What does Missing Authentication Token mean in API Gateway?

In API Gateway REST APIs, it can indicate that a request does not match a deployed resource or HTTP method. It does not always mean authentication credentials are missing.

### Q3. What caused HTTP 403 in this lab?

The client requested an incorrect resource path or an unsupported HTTP method.

### Q4. Why did API Gateway return HTTP 403 rather than 404?

API Gateway REST APIs use the default `MISSING_AUTHENTICATION_TOKEN` gateway response, commonly HTTP 403, for certain unmatched requests.

### Q5. Why was Lambda healthy while the API returned HTTP 403?

The API Gateway routing layer rejected the request before invoking Lambda.

### Q6. How do you inspect API Gateway resources?

Use:

```bash
aws apigateway get-resources \
  --rest-api-id REST_API_ID
```

### Q7. How do you check whether a method exists?

Use:

```bash
aws apigateway get-method \
  --rest-api-id REST_API_ID \
  --resource-id RESOURCE_ID \
  --http-method GET
```

### Q8. How do you verify the deployed stage?

Use:

```bash
aws apigateway get-stage \
  --rest-api-id REST_API_ID \
  --stage-name dev
```

### Q9. Why might Lambda have no new error logs?

An incorrect resource or unsupported method is rejected by API Gateway before the Lambda handler executes.

### Q10. Does correcting the client URL require API redeployment?

No. The API configuration remains unchanged.

### Q11. When is API Gateway redeployment required?

REST API deployment is required when changes to methods, resources, or integrations must become available through a deployed stage.

### Q12. How do you distinguish routing failures from permission failures?

Inspect the request path, HTTP method, deployment stage, authorization configuration, integration, and Lambda invocation behavior.

### Q13. Which CloudWatch metric is relevant to this incident?

The API Gateway `4XXError` metric is useful for investigating client-side API errors.

### Q14. Should you disable API authorization to fix Missing Authentication Token?

No. First determine whether the request matches a supported API route. Disabling authorization without investigation can create a security risk.

### Q15. How would you prevent this problem in production?

Use versioned API contracts, automated integration tests, validated endpoint configuration, deployment reviews, and monitoring.

### Q16. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python AWS Lambda backend.

The API exposed a GET endpoint for retrieving order information.

I first verified that the correct endpoint returned HTTP 200.

Next, I intentionally changed the request path from `/orders` to `/order`.

API Gateway returned HTTP 403 with the message Missing Authentication Token.

I then reproduced the same error by sending an unsupported POST request to the `/orders` endpoint.

I investigated the REST API resources, GET and POST method configurations, deployment stage, Lambda integration, CloudWatch Logs, and CloudWatch metrics.

The investigation confirmed that the Lambda function was healthy and the API infrastructure was correctly configured.

The requests failed because the resource path and HTTP method did not match the deployed API.

I corrected the client request to `GET /dev/orders`.

The API returned HTTP 200 and successfully retrieved the order records.

No Lambda code changes or API Gateway redeployment were required.

Finally, I verified the recovery and removed the temporary AWS resources.

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
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab06-resources.env
│   ├── lambda-response.json
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── broken-path-headers.txt
│   ├── broken-path-response.json
│   ├── broken-method-headers.txt
│   ├── broken-method-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab06-api-resources-evidence.json
│   ├── lab06-get-method-evidence.json
│   ├── lab06-cloudwatch-evidence.json
│   ├── lab06-recovered-cloudwatch-evidence.json
│   ├── lab06-api-4xx-metric.json
│   └── lab06-lambda-invocations-metric.json
│
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
| function.zip | Generated Lambda deployment package |
| lab06-resources.env | Local AWS resource variables |
| lambda-response.json | Direct Lambda invocation evidence |
| baseline-headers.txt | Healthy HTTP headers |
| baseline-response.json | Healthy API response |
| broken-path-headers.txt | Incorrect resource HTTP 403 headers |
| broken-path-response.json | Missing Authentication Token response |
| broken-method-headers.txt | Unsupported method HTTP 403 headers |
| broken-method-response.json | Unsupported method error response |
| recovered-headers.txt | Recovered HTTP headers |
| recovered-response.json | Recovered API response |
| lab06-api-resources-evidence.json | REST API resource investigation |
| lab06-get-method-evidence.json | Configured GET method |
| lab06-cloudwatch-evidence.json | Lambda log evidence |
| lab06-recovered-cloudwatch-evidence.json | Successful recovery logs |
| lab06-api-4xx-metric.json | API Gateway 4XX metrics |
| lab06-lambda-invocations-metric.json | Lambda invocation metrics |

### Recommended Public GitHub Files

```text
06-missing-authorization-token/
├── README.md
├── lambda_function.py
└── lambda-trust-policy.json
```

The local evidence files and generated deployment package do not need to be committed.

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 06
06-missing-authorization-token/function.zip
06-missing-authorization-token/lab06-resources.env
06-missing-authorization-token/lab06-*.json
06-missing-authorization-token/lambda-response.json
06-missing-authorization-token/*-headers.txt
06-missing-authorization-token/*-response.json

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

Do not publish credentials, account-specific troubleshooting information, or raw CloudWatch evidence without review.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how an Amazon API Gateway REST API can return HTTP 403 Missing Authentication Token even when the backend Lambda function is healthy.

We created a REST API integrated with a Python Lambda function.

We first verified that the correct GET endpoint returned HTTP 200 and retrieved order information.

We then intentionally changed the client request path from `/orders` to `/order`.

API Gateway could not match the requested resource and returned HTTP 403.

Next, we sent an unsupported POST request to the `/orders` endpoint.

API Gateway returned the same Missing Authentication Token error because the POST method was not configured.

We investigated the REST API resources, HTTP methods, Lambda integration, deployment stage, Lambda function state, CloudWatch Logs, and metrics.

The investigation confirmed that both failures originated from incorrect client requests rather than backend execution or missing authentication.

We restored the correct request path and HTTP method.

The API returned HTTP 200 without modifying Lambda code or redeploying API Gateway.

Finally, the lab included verification and cleanup procedures.

**Key Lesson:** An API Gateway Missing Authentication Token response does not automatically indicate an authentication problem. Engineers must verify the API resource, HTTP method, stage, and deployment before making changes to security controls.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 403 troubleshooting
- Missing Authentication Token investigation
- API resource matching
- HTTP method matching
- REST API deployment stages
- Lambda proxy integration
- Python 3.13
- AWS IAM execution roles
- Lambda resource-based policies
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch API metrics
- Lambda invocation troubleshooting
- Root cause analysis
- API client configuration remediation
- Recovery verification
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-006 |
| Scenario | Missing Authentication Token |
| REST API | api-lab06-auth-token-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab06-order-handler |
| Broken Resource | /order |
| Unsupported Method | POST |
| Broken API Response | HTTP 403 |
| Error Message | Missing Authentication Token |
| Root Cause | Incorrect client route or method |
| Remediation | Restore GET /dev/orders |
| Recovery Response | HTTP 200 |
| Lambda Code Changes | None |
| API Gateway Redeployment | Not required |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Effective API Gateway troubleshooting requires distinguishing routing errors from authorization errors, inspecting deployed API methods and resources, verifying backend health, and correcting only the configuration responsible for the incident.

---

## Official AWS Documentation

- [Amazon API Gateway — Gateway Response Types](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)
- [Amazon API Gateway — REST API Resources and Methods](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-settings-method-request.html)
- [Amazon API Gateway — Deploy REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-deploy-api.html)
- [Amazon API Gateway — Lambda Proxy Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [Amazon API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS Lambda — Python Handler](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [AWS CLI — Get Resources](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-resources.html)
- [AWS CLI — Get Method](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-method.html)
- [AWS CLI — Get Stage](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-stage.html)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)