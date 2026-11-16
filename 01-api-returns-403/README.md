# Lab 01 — Amazon API Gateway Returns 403 Forbidden

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an Amazon API Gateway REST API returning `403 Forbidden` because the client does not meet the API method's AWS IAM authorization requirements.

In production, API Gateway is commonly used to provide secure HTTPS endpoints for web applications, mobile applications, internal services, and serverless applications.

A request may fail even when the API Gateway endpoint, deployment, and Lambda backend are configured correctly.

In this lab, we create an API Gateway REST API with a `GET /orders` endpoint integrated with an AWS Lambda function.

We intentionally configure the API method to require `AWS_IAM` authorization.

When a client sends an ordinary unsigned HTTP request, API Gateway rejects the request with HTTP 403 before invoking Lambda.

We investigate the incident using AWS CLI, curl, IAM configuration, API Gateway method settings, Lambda invocation permissions, and CloudWatch Logs.

After identifying the root cause, we demonstrate the correct production remediation: sending an AWS Signature Version 4 (SigV4) signed request from an authorized IAM identity.

We also include an optional diagnostic test that temporarily removes authorization to confirm that the API Gateway–Lambda integration works independently of IAM authentication.

The original IAM authorization requirement is restored immediately afterward.

Finally, we delete the temporary API Gateway, Lambda, IAM, and CloudWatch resources.

### Troubleshooting Workflow

```text
Create IAM Execution Role
            |
            v
Deploy Python Lambda
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
Set Authorization = AWS_IAM
            |
            v
Configure Lambda Proxy Integration
            |
            v
Grant API Gateway Lambda Invoke Permission
            |
            v
Deploy API to dev Stage
            |
            v
Send Unsigned HTTP Request
            |
            v
HTTP 403 Forbidden
            |
            v
Inspect API Method Authorization
            |
            v
Check Route and Deployment
            |
            v
Verify Lambda Integration
            |
            v
Investigate CloudWatch Logs
            |
            v
Identify Missing SigV4 Authorization
            |
            v
Send Signed Request
            |
            v
Verify execute-api:Invoke Permission
            |
            v
HTTP 200 OK
            |
            v
Confirm Lambda Execution
            |
            v
Verify IAM Protection
            |
            v
Cleanup AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-001 |
| Lab Name | API Returns 403 |
| Difficulty | Beginner to Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| API Type | REST API |
| Endpoint Type | Regional |
| AWS Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| REST API Name | `api-lab01-403-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization Type | `AWS_IAM` |
| Lambda Function | `api-lab01-order-handler` |
| Lambda Runtime | Python 3.13 |
| Lambda Handler | `lambda_function.lambda_handler` |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| IAM Execution Role | `api-lab01-lambda-role` |
| Lambda Integration | AWS_PROXY |
| Backend Invocation Method | POST |
| Broken Request | Unsigned GET |
| Expected Failure | HTTP 403 |
| Root Cause | Missing SigV4 authorization |
| Required Caller Permission | `execute-api:Invoke` |
| Remediation | Sign request using authorized AWS credentials |
| Recovery Status | HTTP 200 |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand API Gateway REST API architecture.
- Understand HTTP 403 Forbidden.
- Configure REST API resources and methods.
- Create a Lambda proxy integration.
- Understand API Gateway deployment stages.
- Configure AWS IAM authorization.
- Understand AWS Signature Version 4.
- Distinguish API client authorization from Lambda invocation permissions.
- Reproduce an unauthorized request.
- Inspect API Gateway method configurations.
- Investigate Lambda resource-based policies.
- Inspect CloudWatch Logs.
- Identify failures occurring before Lambda invocation.
- Send authenticated requests using curl.
- Understand `execute-api:Invoke`.
- Redeploy API Gateway after configuration changes.
- Verify successful remediation.
- Apply least-privilege security principles.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-processing API using Amazon API Gateway and AWS Lambda.

The application exposes the following endpoint:

```http
GET /dev/orders
```

The endpoint retrieves basic order-processing information from the Lambda backend.

The API Gateway method is protected using AWS IAM authorization.

This means clients must send valid AWS-signed requests and have permission to invoke the API.

However, an application client sends a regular HTTPS request without AWS SigV4 authentication.

The client receives:

```http
HTTP/2 403 Forbidden
```

The API response contains a message similar to:

```json
{
  "message": "Missing Authentication Token"
}
```

The application team suspects the Lambda backend is failing.

The Cloud Engineer begins investigating.

The engineer verifies that:

- The REST API exists.
- The `/orders` resource exists.
- The GET method is configured.
- The `dev` stage is deployed.
- API Gateway is integrated with Lambda.
- Lambda is Active.
- API Gateway has permission to invoke Lambda.
- The GET method requires AWS IAM authorization.
- The client request does not contain a valid AWS signature.

CloudWatch shows no corresponding Lambda handler execution for the rejected request.

The engineer determines that the request is rejected by API Gateway before reaching Lambda.

The correct solution is to use a properly signed request from an IAM identity authorized to invoke the method.

After sending a signed request, API Gateway accepts it and invokes Lambda successfully.

### Incident Symptoms

- API Gateway endpoint exists.
- Lambda function is Active.
- Unsigned requests return HTTP 403.
- Response may contain `Missing Authentication Token`.
- Lambda handler is not invoked for rejected requests.
- API Gateway method uses `AWS_IAM`.
- Authorized signed requests return HTTP 200.
- No Lambda application code changes are required.

### Business Impact

An API authorization misconfiguration or incorrect client authentication may cause:

- Application request failures.
- Inaccessible backend services.
- Failed internal API integrations.
- Customer-facing errors.
- Interrupted business operations.
- Unnecessary backend troubleshooting.
- Increased incident response time.

### Objective

Identify the IAM authorization requirement responsible for the HTTP 403 response, verify that the Lambda backend is healthy, and restore authorized API access without weakening production security.

---

## 3. AWS Architecture

### Broken Architecture

```text
                  API Client
                      |
                      v
                Unsigned Request
                      |
                      v
                 GET /orders
                      |
                      v
               Amazon API Gateway
                      |
                      v
             AWS_IAM Authorization
                      |
                      v
                Signature Check
                      |
                      v
               No Valid Signature
                      |
                      v
                 Access Denied
                      |
                      v
                HTTP 403 Forbidden
                      |
                      X
                      |
                  AWS Lambda
                      |
                      v
                 Not Invoked
```

### Recovered Architecture

```text
                   API Client
                       |
                       v
               AWS SigV4 Request
                       |
                       v
                  GET /orders
                       |
                       v
                Amazon API Gateway
                       |
                       v
                IAM Authorization
                       |
                       v
              Validate Request Signature
                       |
                       v
             Check execute-api:Invoke
                       |
                       v
                 Access Allowed
                       |
                       v
              Lambda Proxy Integration
                       |
                       v
                AWS Lambda Handler
                       |
                       v
               Process API Request
                       |
                       v
                  HTTP 200 OK
                       |
                       v
                    API Client
```

### Architecture Components

| Component | Purpose |
|---|---|
| API Client | Sends HTTPS requests |
| API Gateway REST API | Receives and processes API requests |
| `/orders` Resource | Defines the API endpoint path |
| GET Method | Defines the supported operation |
| AWS_IAM | Requires AWS-signed authorization |
| SigV4 | Authenticates AWS API requests |
| execute-api:Invoke | Grants permission to invoke the API |
| Lambda Proxy Integration | Connects API Gateway to Lambda |
| Lambda Resource-Based Policy | Allows API Gateway to invoke Lambda |
| IAM Execution Role | Allows Lambda to write CloudWatch logs |
| CloudWatch Logs | Records backend execution |
| CloudWatch Metrics | Tracks API errors and request activity |

---

## 4. Understanding API Gateway HTTP 403

### What Does HTTP 403 Mean?

HTTP 403 indicates that the server understood the request but refuses to authorize the requested operation.

### Why Does API Gateway Return 403?

Possible causes include:

- Missing IAM authentication.
- Missing `execute-api:Invoke` permission.
- Explicit IAM denial.
- API Gateway resource policy denial.
- Invalid API key.
- AWS WAF block.
- Incorrect API resource or HTTP method.
- Incorrect deployment stage.
- Private API endpoint restrictions.
- Disabled default execute-api endpoint.

### What Is AWS_IAM Authorization?

AWS IAM authorization requires API clients to sign requests using AWS credentials.

API Gateway evaluates the request identity and relevant permissions before invoking the backend.

### What Is AWS Signature Version 4?

AWS SigV4 is an AWS request-signing mechanism.

It signs important request information using AWS credentials so that AWS can authenticate the request.

### What Is execute-api:Invoke?

It is an IAM action used to authorize API invocation.

Example:

```json
{
  "Effect": "Allow",
  "Action": "execute-api:Invoke",
  "Resource": "arn:aws:execute-api:us-east-1:ACCOUNT_ID:API_ID/dev/GET/orders"
}
```

### What Is Missing Authentication Token?

For API Gateway REST APIs, this message can appear when:

- A request is sent without the required AWS signature.
- A resource path does not exist.
- An HTTP method is not supported.
- The stage or endpoint is incorrect.

Therefore, the response must be investigated with the API method and route configuration.

### Does 403 Mean Lambda Failed?

Not necessarily.

API Gateway can reject a request before invoking Lambda.

A missing Lambda handler log for a rejected request is consistent with authorization failure, although production investigations should correlate request IDs and gateway logs where possible.

### Client IAM Permission vs. Lambda Permission

| Permission | Purpose |
|---|---|
| `execute-api:Invoke` | Allows an API client to invoke the API |
| `lambda:InvokeFunction` | Allows API Gateway to invoke the Lambda backend |
| Lambda execution-role permissions | Control what Lambda can do while running |

These are three different authorization concerns.

---

## 5. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Bash.
- Python 3.
- curl with AWS SigV4 support.
- ZIP and unzip.
- jq.
- IAM management permissions.
- API Gateway management permissions.
- Lambda management permissions.
- CloudWatch access.

### Relevant AWS Permissions

```text
sts:GetCallerIdentity

iam:CreateRole
iam:GetRole
iam:AttachRolePolicy
iam:ListAttachedRolePolicies
iam:ListRoleTags
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

execute-api:Invoke

logs:CreateLogGroup
logs:PutRetentionPolicy
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

Permissions should be limited to the resources and operations required by the lab wherever possible.

### Safety Rules

- Use a dedicated REST API.
- Use a dedicated Lambda function and IAM role.
- Never disable authorization on production APIs for testing.
- Do not expose AWS credentials in screenshots or logs.
- Do not commit generated AWS access keys or session tokens.
- Use least-privilege permissions.
- Restore IAM authorization after any diagnostic changes.
- Verify project tags before deleting resources.
- Remove all temporary AWS resources.

### Cost Considerations

This lab uses:

- API Gateway requests.
- Lambda executions.
- CloudWatch logging and metrics.

No EC2, RDS, NAT Gateway, or dedicated VPC resources are required.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create the Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 01-api-returns-403

cd 01-api-returns-403
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

sudo apt install -y \
  curl \
  zip \
  unzip \
  jq
```

### Step 3 — Configure AWS Variables

```bash
export AWS_REGION="us-east-1"
export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab01"

export REST_API_NAME="api-lab01-403-troubleshooting"

export FUNCTION_NAME="api-lab01-order-handler"

export ROLE_NAME="api-lab01-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export HTTP_METHOD="GET"

export RESOURCE_PATH="orders"

export PERMISSION_SID="AllowAPIGatewayLab01"
```

### Step 4 — Save Resource Variables

```bash
cat > lab01-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export REST_API_NAME="$REST_API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STAGE_NAME="$STAGE_NAME"
export HTTP_METHOD="$HTTP_METHOD"
export RESOURCE_PATH="$RESOURCE_PATH"
export PERMISSION_SID="$PERMISSION_SID"
EOF

chmod 600 lab01-resources.env
```

Restore later:

```bash
source lab01-resources.env
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

Check existing REST APIs:

```bash
aws apigateway get-rest-apis \
  --query "items[?name=='${REST_API_NAME}'].{Id:id,Name:name}" \
  --output table \
  --region "$AWS_REGION"
```

Do not overwrite unrelated resources.

---

## 7. Create the Lambda Execution Role

### Step 1 — Create IAM Trust Policy

Save as `lambda-trust-policy.json`:

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
  --description "API Gateway Lab 01 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Policy

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
```

### Step 2 — Understand the Handler

The function returns an API Gateway-compatible Lambda proxy response.

Expected body:

```json
{
  "message": "Orders API working",
  "status": "success",
  "method": "GET",
  "path": "/orders"
}
```

The handler logs:

```text
LAB01_BACKEND_INVOKED
```

This helps confirm whether a request reached the backend.

### Step 3 — Validate Python Syntax

```bash
python3 - <<'PY'
import ast
from pathlib import Path

ast.parse(Path("lambda_function.py").read_text())

print("SUCCESS: Python syntax valid")
PY
```

### Step 4 — Create ZIP Package

```bash
zip function.zip lambda_function.py
```

Verify:

```bash
unzip -l function.zip
```

### Step 5 — Deploy Lambda

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

### Step 6 — Wait for Activation

```bash
aws lambda wait function-active-v2 \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Retrieve Function ARN

```bash
export FUNCTION_ARN=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --query Configuration.FunctionArn \
  --output text \
  --region "$AWS_REGION")

echo "$FUNCTION_ARN"

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab01-resources.env
```

---

## 9. Configure CloudWatch Logs

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

### Step 3 — Verify Configuration

```bash
aws logs describe-log-groups \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='${LOG_GROUP}'].{Name:logGroupName,Retention:retentionInDays}" \
  --output table \
  --region "$AWS_REGION"
```

---

## 10. Create the API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export REST_API_ID=$(aws apigateway create-rest-api \
  --name "$REST_API_NAME" \
  --description "API Gateway Lab 01 IAM 403 troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$REST_API_ID"

echo "export REST_API_ID='$REST_API_ID'" >> lab01-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_RESOURCE_ID"

echo "export ROOT_RESOURCE_ID='$ROOT_RESOURCE_ID'" >> lab01-resources.env
```

### Step 3 — Create the /orders Resource

```bash
export RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id "$REST_API_ID" \
  --parent-id "$ROOT_RESOURCE_ID" \
  --path-part "$RESOURCE_PATH" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$RESOURCE_ID"

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab01-resources.env
```

### Step 4 — Verify API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

Expected paths:

```text
/
 /orders
```

---

## 11. Configure AWS IAM Authorization

### Step 1 — Create GET Method

```bash
aws apigateway put-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --authorization-type AWS_IAM \
  --region "$AWS_REGION"
```

### Step 2 — Verify Method Configuration

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

Expected fields:

```json
{
  "httpMethod": "GET",
  "authorizationType": "AWS_IAM",
  "apiKeyRequired": false
}
```

### Understanding the Configuration

The GET method requires signed AWS requests.

An ordinary unsigned request cannot access the method.

This is our intentional misconfiguration from the client's perspective: the API requires authentication, but the test client does not provide it.

---

## 12. Configure Lambda Proxy Integration

### Step 1 — Generate Integration URI

```bash
export INTEGRATION_URI="arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${FUNCTION_ARN}/invocations"
```

### Step 2 — Create Integration

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

### Why Does the Backend Use POST?

The public endpoint uses:

```http
GET /orders
```

But API Gateway invokes the Lambda service through its invocation API using POST.

The API client method and backend invocation method serve different purposes.

### Step 3 — Verify Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

Expected:

```text
type = AWS_PROXY
httpMethod = POST
```

### Step 4 — Allow API Gateway to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${REST_API_ID}/*/GET/orders" \
  --region "$AWS_REGION"
```

### Step 5 — Verify Lambda Invocation Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Confirm the policy grants API Gateway permission to invoke the Lambda function.

This does not grant anonymous clients access to the API.

---

## 13. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab01 IAM protected deployment" \
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

echo "export API_URL='$API_URL'" >> lab01-resources.env
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

### Step 4 — Verify Deployment

```bash
aws apigateway get-deployments \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

---

## 14. Fault Injection — Reproduce HTTP 403

### Step 1 — Send an Unsigned Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 403 Forbidden
```

Possible response:

```json
{
  "message": "Missing Authentication Token"
}
```

### Step 2 — Save Response Headers and Body

```bash
curl -sS \
  -D broken-headers.txt \
  -o broken-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 403
```

### Step 3 — Inspect Response Headers

```bash
cat broken-headers.txt
```

Look for:

```text
HTTP/2 403
```

### Step 4 — Inspect Response Body

```bash
python3 -m json.tool broken-response.json
```

### Step 5 — Verify the Failure

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "403" ]; then
  echo "SUCCESS: HTTP 403 reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Broken-State Verification

| Check | Expected |
|---|---|
| REST API | Created |
| `/orders` resource | Exists |
| GET method | Exists |
| Stage | Deployed |
| Lambda integration | Configured |
| Authorization type | AWS_IAM |
| Client request | Unsigned |
| API response | HTTP 403 |
| Lambda invocation for rejected request | None |

---

## 15. Investigate the 403 Error

### Step 1 — Inspect API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

Confirm that `/orders` exists.

### Step 2 — Inspect Method Authorization

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Method:httpMethod,Authorization:authorizationType,ApiKeyRequired:apiKeyRequired}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Method": "GET",
  "Authorization": "AWS_IAM",
  "ApiKeyRequired": false
}
```

### Step 3 — Inspect API Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Deployments

```bash
aws apigateway get-deployments \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Step 5 — Inspect Lambda Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 6 — Inspect Lambda Resource Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Inspect Lambda Logs

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB01_BACKEND_INVOKED"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected before any successful invocation:

```json
[]
```

### Step 8 — Save Method Evidence

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION" \
  > lab01-broken-method-config.json
```

### Step 9 — Save Integration Evidence

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION" \
  > lab01-integration-evidence.json
```

### Investigation Findings

| Component | Finding |
|---|---|
| REST API | Correct |
| API resource | Correct |
| HTTP method | Correct |
| Deployment | Present |
| Stage | Correct |
| Lambda integration | Correct |
| Lambda invocation permission | Correct |
| API method authorization | AWS_IAM |
| Client signature | Missing |
| Root cause | Unsigned IAM-protected request |

---

## 16. Root Cause Analysis

### Root Cause

The API Gateway REST API GET method was configured with `AWS_IAM` authorization.

The client sent an unsigned HTTP request.

API Gateway could not authenticate and authorize the request.

Therefore, the request was rejected before Lambda invocation.

### Root Cause Diagram

```text
API Client
     |
     v
GET /dev/orders
     |
     v
No AWS SigV4 Signature
     |
     v
API Gateway
     |
     v
Method Authorization = AWS_IAM
     |
     v
Authentication Requirement Not Met
     |
     v
HTTP 403 Forbidden
     |
     v
Lambda Not Invoked
```

### Five Whys

**Why 1 — Why did the API request fail?**

API Gateway returned HTTP 403.

**Why 2 — Why did API Gateway return 403?**

The API method required IAM authorization.

**Why 3 — Why was authorization unsuccessful?**

The request did not contain a valid AWS SigV4 signature.

**Why 4 — Why didn't Lambda process the request?**

API Gateway rejected it before invoking the integration.

**Why 5 — How can this be prevented?**

Require authorized clients to sign their requests and grant the necessary `execute-api:Invoke` permissions.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-001 |
| Failure | HTTP 403 Forbidden |
| API Method | GET /orders |
| Authorization | AWS_IAM |
| Client Request | Unsigned |
| Lambda Backend | Healthy |
| Root Cause | Missing SigV4 authentication |
| Recommended Remediation | Authorized signed request |
| Backend Code Changes | Not required |

---

## 17. Remediation — Use AWS SigV4 Authentication

### Step 1 — Identify AWS CLI Identity

```bash
aws sts get-caller-identity
```

### Step 2 — Generate Least-Privilege Invoke Policy

```bash
python3 - <<'PY'
import json
import os

region = os.environ["AWS_REGION"]
account = os.environ["ACCOUNT_ID"]
api_id = os.environ["REST_API_ID"]
stage = os.environ["STAGE_NAME"]

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowInvokeLab01Orders",
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": (
                f"arn:aws:execute-api:{region}:"
                f"{account}:{api_id}/{stage}/GET/orders"
            )
        }
    ]
}

with open("api-invoke-policy.json", "w") as file:
    json.dump(policy, file, indent=2)

print("Invoke policy generated")
PY
```

### Step 3 — Inspect Policy

```bash
python3 -m json.tool api-invoke-policy.json
```

The policy must be granted to an approved API client IAM identity.

It does not belong on the Lambda execution role.

If the existing AWS identity already has permission, no additional policy is required.

Otherwise, an authorized administrator should grant only the specific API invocation permission needed.

### Step 4 — Verify curl SigV4 Support

```bash
curl --help all | grep aws-sigv4
```

### Step 5 — Export Resolved AWS Credentials

Disable shell command tracing:

```bash
set +x
```

Export AWS credentials in environment-variable format:

```bash
eval "$(aws configure export-credentials --format env)"
```

This supplies the AWS access key and secret key, and the session token if applicable.

Do not print or commit these environment values.

### Step 6 — Configure Optional Session Token Header

```bash
TOKEN_HEADER=()

if [ -n "${AWS_SESSION_TOKEN:-}" ]; then
  TOKEN_HEADER=(
    -H "X-Amz-Security-Token: $AWS_SESSION_TOKEN"
  )
fi
```

### Step 7 — Send Signed Request

```bash
curl -sS \
  --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
  --user "${AWS_ACCESS_KEY_ID}:${AWS_SECRET_ACCESS_KEY}" \
  "${TOKEN_HEADER[@]}" \
  -D signed-headers.txt \
  -o signed-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected with an authorized identity:

```text
HTTP Status: 200
```

### Step 8 — Inspect Response

```bash
python3 -m json.tool signed-response.json
```

Expected:

```json
{
  "message": "Orders API working",
  "status": "success",
  "method": "GET",
  "path": "/orders"
}
```

### Step 9 — Verify Recovery

```bash
python3 - <<'PY'
import json

with open("signed-response.json") as file:
    response = json.load(file)

assert response["status"] == "success"
assert response["method"] == "GET"
assert response["path"] == "/orders"

print("SUCCESS: Authorized API request processed")
PY
```

### Step 10 — Verify Backend Invocation

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB01_BACKEND_INVOKED"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

Expected: the Lambda backend invocation marker appears after the signed request succeeds and CloudWatch Logs are delivered.

### Remediation Summary

| Configuration | Broken | Recovered |
|---|---|---|
| API Gateway | AWS_IAM | AWS_IAM |
| Client request | Unsigned | SigV4 signed |
| IAM invoke permission | Not demonstrated | Authorized |
| API response | 403 | 200 |
| Lambda invoked | No | Yes |
| Backend code | Unchanged | Unchanged |
| API security | Protected | Still protected |

**The recommended recovery preserves IAM authorization.**

---

## 18. Optional Diagnostic — Temporarily Disable Authorization

This diagnostic test is only appropriate for the dedicated lab API.

It should never be used to bypass required production authorization.

### Step 1 — Temporarily Set Authorization to NONE

```bash
aws apigateway update-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --patch-operations \
  op=replace,path=/authorizationType,value=NONE \
  --region "$AWS_REGION"
```

### Step 2 — Redeploy the API

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Temporary Lab01 authorization diagnostic" \
  --region "$AWS_REGION"
```

### Step 3 — Test Unsigned Request

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 200
```

This confirms that the backend integration works without the IAM authorization requirement.

### Step 4 — Restore IAM Authorization Immediately

```bash
aws apigateway update-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --patch-operations \
  op=replace,path=/authorizationType,value=AWS_IAM \
  --region "$AWS_REGION"
```

### Step 5 — Redeploy Protected Configuration

```bash
aws apigateway create-deployment \
  --rest-api-id "$REST_API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Restore Lab01 IAM authorization" \
  --region "$AWS_REGION"
```

### Step 6 — Verify Authorization

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Authorization:authorizationType}' \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Authorization": "AWS_IAM"
}
```

### Step 7 — Verify Unsigned Requests Are Rejected Again

```bash
curl -sS \
  -o /dev/null \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 403
```

This confirms that IAM authorization has been restored.

---

## 19. CloudWatch Troubleshooting

### Step 1 — Define Observation Window

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 2 — Inspect API Gateway 4XX Errors

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

Expected: nonzero 4XX errors after metric data is published.

### Step 3 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 30m \
  --region "$AWS_REGION"
```

### Step 4 — Compare Request Outcomes

| Request | API Response | Lambda Handler |
|---|---|---|
| Unsigned, IAM protected | 403 | Not invoked |
| Signed, authorized | 200 | Invoked |
| Temporary authorization NONE | 200 | Invoked |
| Unsigned after IAM restored | 403 | Not invoked |

### Observability Lessons

API Gateway can reject requests before invoking the backend.

Therefore, Lambda logs alone may not explain an API failure.

Production investigations should examine API Gateway access logs, gateway response categories, IAM configuration, and backend logs together.

Enabling REST API execution logging may require an account-level CloudWatch role. This lab does not modify shared account-wide logging settings.

---

## 20. Production Troubleshooting Best Practices

### Standard Investigation Checklist

1. Identify the failing API endpoint.
2. Verify AWS account and Region.
3. Check the HTTP status and response body.
4. Inspect response headers.
5. Confirm the API resource exists.
6. Confirm the HTTP method exists.
7. Check the deployment stage.
8. Verify the deployed API configuration.
9. Inspect authorization settings.
10. Identify the client authentication method.
11. Check IAM `execute-api:Invoke` permissions.
12. Inspect API Gateway resource policies.
13. Verify Lambda integration settings.
14. Check Lambda resource-based invocation permissions.
15. Inspect CloudWatch logs.
16. Determine whether the request reached Lambda.
17. Identify the root cause.
18. Apply least-privilege remediation.
19. Repeat the original test.
20. Verify security remains enabled.
21. Clean up temporary AWS resources.

### Common API Gateway 403 Causes

| Problem | Possible Cause | Investigation |
|---|---|---|
| Missing Authentication Token | Unsigned IAM request or invalid route/method | Method, path, signature |
| Access denied | Missing execute-api permission | IAM policies |
| Invalid API key | Wrong or inactive key | API key and usage plan |
| Resource policy deny | Explicit API restriction | REST API policy |
| WAF block | Web ACL rule | WAF logs |
| Incorrect stage | Wrong URL | API deployments |
| Invalid signature | Credential or signing error | SigV4 configuration |
| Expired token | Temporary credentials expired | STS credentials |
| Lambda not invoked | Gateway rejects request first | Authorization and logs |

---

## 21. Cloud Security Engineering Considerations

### IAM Least Privilege

Grant only the required API invocation permission.

Example:

```text
execute-api:Invoke
```

Scope the permission to the specific API, stage, method, and resource.

### Lambda Invocation Security

Grant API Gateway permission to invoke only the intended backend Lambda function and route.

### Do Not Disable Authorization to Fix Production Errors

An HTTP 403 is sometimes expected security behavior.

The correct goal is to restore legitimate access while preserving access restrictions.

### Credential Security

Do not store AWS access keys in source code or GitHub.

Use approved AWS credential providers, temporary credentials, and role-based access where possible.

### Monitoring

Monitor unusual increases in 403 responses, access-denied events, failed authentication, and API request patterns.

### Auditability

Use AWS CloudTrail to investigate relevant API Gateway and IAM configuration changes.

### Defense in Depth

Production APIs may use IAM authorization, resource policies, AWS WAF, HTTPS, throttling, and monitoring depending on the architecture.

---

## 22. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Requests |
| AWS Lambda | Invocations and execution duration |
| CloudWatch Logs | Log ingestion and storage |
| CloudWatch Metrics | Metric usage and applicable charges |
| IAM | No separate charge for standard role configuration |

### Cost Optimization

- Use a dedicated temporary API.
- Avoid unnecessary repeated requests.
- Keep Lambda invocations short.
- Configure log retention.
- Delete lab resources after testing.
- Avoid creating unrelated services.

---

## 23. AWS Resource Cleanup

**Warning: Delete only resources created for Lab 01.**

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
Project = API-Gateway-Troubleshooting-Lab01
```

### Step 4 — Delete the REST API

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

The Lambda resource-based invocation permission is removed with the function.

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

If your administrator granted a temporary API invocation permission for this lab, remove that permission if it is no longer required.

Do not remove unrelated permissions.

### Cleanup Summary

| Resource | Expected State |
|---|---|
| API Gateway REST API | Deleted |
| API deployment | Deleted with REST API |
| API stage | Deleted with REST API |
| Lambda function | Deleted |
| Lambda resource policy | Removed with function |
| IAM execution role | Deleted |
| CloudWatch log group | Deleted |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |
| VPC | Not created |

---

## 24. Interview Questions and Answers

### Q1. What does HTTP 403 mean?

The server refuses to authorize the requested operation.

### Q2. What caused the 403 in this lab?

The client sent an unsigned request to an IAM-protected API Gateway method.

### Q3. What is AWS_IAM authorization?

An API Gateway authorization method that requires appropriately signed requests and AWS identity permissions.

### Q4. What is SigV4?

AWS Signature Version 4 is a request-signing mechanism used to authenticate AWS API requests.

### Q5. What is execute-api:Invoke?

An IAM action that allows an authorized identity to invoke an API Gateway endpoint.

### Q6. Why wasn't Lambda invoked?

API Gateway rejected the request during authorization before the backend integration.

### Q7. Does Missing Authentication Token always mean a JWT is missing?

No. For REST APIs, it can indicate missing IAM signing or an incorrect resource, method, or endpoint.

### Q8. What is the difference between API authorization and Lambda invocation permission?

API authorization controls whether the client can access the API. Lambda invocation permission allows API Gateway to call the backend function.

### Q9. Why does API Gateway use POST for a Lambda integration when the client sends GET?

API Gateway invokes the Lambda service API using POST, while the public-facing REST method remains GET.

### Q10. How do you check method authorization?

Use `aws apigateway get-method` and inspect `authorizationType`.

### Q11. Why must API Gateway be redeployed after method changes?

REST API deployments represent configuration snapshots used by stages.

### Q12. Is disabling authorization a production remediation?

Not when the method is intended to require authorization. The correct remediation is to fix client authentication or permissions.

### Q13. What CloudWatch metric can show client-side API errors?

`4XXError`.

### Q14. How can you identify whether the request reached Lambda?

Correlate API Gateway request information with Lambda execution logs and metrics.

### Q15. How would you explain this lab in an interview?

I created an Amazon API Gateway REST API with a GET /orders endpoint integrated with a Python Lambda function.

I configured AWS IAM authorization on the GET method.

I intentionally sent an unsigned HTTP request using curl and reproduced HTTP 403 Forbidden.

I investigated the API resource, GET method, deployment stage, Lambda proxy integration, IAM authorization, and Lambda invocation permissions.

I identified the missing AWS SigV4 signature as the root cause.

The request was denied by API Gateway before the Lambda handler could execute.

I then used an authorized AWS identity to send a signed request and verified that API Gateway invoked Lambda successfully.

I also performed a temporary authorization comparison test and restored AWS_IAM immediately afterward.

Finally, I removed the REST API, Lambda function, IAM role, and CloudWatch log group.

---

## 25. Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-api-returns-403/
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── api-invoke-policy.json
│   ├── function.zip
│   ├── lab01-resources.env
│   ├── broken-headers.txt
│   ├── broken-response.json
│   ├── signed-headers.txt
│   ├── signed-response.json
│   ├── lab01-broken-method-config.json
│   └── lab01-integration-evidence.json
│
├── 02-api-returns-404/
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
| README.md | Complete troubleshooting documentation |
| lambda_function.py | Python backend |
| lambda-trust-policy.json | Lambda IAM trust policy |
| api-invoke-policy.json | Generated example client IAM policy |
| function.zip | Lambda deployment archive |
| lab01-resources.env | Local AWS resource variables |
| broken-headers.txt | Unsigned API response headers |
| broken-response.json | Unauthorized response body |
| signed-headers.txt | Signed response headers |
| signed-response.json | Successful API response |
| lab01-broken-method-config.json | API authorization configuration evidence |
| lab01-integration-evidence.json | Lambda integration evidence |

### Recommended Public GitHub Files

```text
01-api-returns-403/
├── README.md
├── lambda_function.py
├── lambda-trust-policy.json
└── api-invoke-policy.example.json
```

The public example IAM policy should use placeholder account and API identifiers rather than the generated values from your AWS account.

### Recommended Root .gitignore

Add:

```gitignore
# API Gateway Lab 01
01-api-returns-403/function.zip
01-api-returns-403/lab01-resources.env
01-api-returns-403/lab01-*.json
01-api-returns-403/*-response.json
01-api-returns-403/*-headers.txt
01-api-returns-403/api-invoke-policy.json

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

Do not publish credentials, session tokens, or raw account-specific evidence without review.

---

## 26. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how API Gateway can reject requests before reaching the Lambda backend.

We created a REST API and integrated it with a Python Lambda function.

We configured AWS IAM authorization on the GET /orders method.

When an unsigned client attempted to invoke the endpoint, API Gateway returned HTTP 403.

We investigated the API method, resource, deployment, Lambda integration, permissions, and CloudWatch Logs.

The investigation showed that the client did not satisfy the IAM authorization requirement.

We then tested the API using a properly signed request from an authorized identity.

The API returned HTTP 200 and Lambda processed the request.

We also demonstrated how authorization settings can be temporarily changed for a dedicated diagnostic test and then restored.

Finally, we cleaned up all temporary AWS resources.

**Key Lesson:** HTTP 403 does not necessarily indicate that the Lambda application is broken. API Gateway authorization and access policies should be investigated before changing backend code.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- HTTP 403 troubleshooting
- AWS_IAM authorization
- AWS Signature Version 4
- execute-api:Invoke
- Lambda proxy integration
- Lambda resource-based policies
- IAM execution roles
- REST API resources and methods
- API stages and deployments
- AWS CLI v2
- Linux Bash
- Python 3.13
- curl
- CloudWatch Logs
- CloudWatch 4XX metrics
- Authorization troubleshooting
- Root cause analysis
- Security remediation
- Recovery verification
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-001 |
| Scenario | API Returns 403 |
| API | api-lab01-403-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Authorization | AWS_IAM |
| Broken Request | Unsigned |
| Broken Response | HTTP 403 |
| Root Cause | Missing SigV4 authentication |
| Remediation | Signed, authorized request |
| Recovery Response | HTTP 200 |
| Lambda Backend | Successfully invoked after authorization |
| Security | IAM remains enabled |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved after verification |

**Key Takeaway:** Production API Gateway troubleshooting requires understanding HTTP responses, REST API configuration, IAM authentication, Lambda integration permissions, and CloudWatch observability. The safest remediation restores legitimate access while preserving security controls.

---

## Official AWS Documentation

- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [API Gateway IAM Permissions](https://docs.aws.amazon.com/apigateway/latest/developerguide/permissions.html)
- [API Gateway Gateway Response Types](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)
- [API Gateway Lambda Proxy Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [API Gateway Lambda Proxy Integration Using AWS CLI](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integration-using-cli.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [AWS CLI — Export Credentials](https://docs.aws.amazon.com/cli/latest/reference/configure/export-credentials.html)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)