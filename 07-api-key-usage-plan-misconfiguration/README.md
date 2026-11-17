# Lab 07 — Amazon API Gateway API Key / Usage Plan Misconfiguration

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve an HTTP **403 Forbidden** error caused by an API key and usage plan misconfiguration in Amazon API Gateway.

In production, organizations often expose REST APIs to internal applications, business partners, and third-party clients.

Amazon API Gateway supports API keys and usage plans to identify API consumers and manage API usage through throttling and quotas.

A usage plan defines which deployed API stages are available to associated API keys and can apply request limits.

For an API Gateway REST API method requiring an API key, the caller must provide a valid, enabled API key associated with a usage plan that includes the requested API stage.

If the API key is missing, invalid, disabled, or not associated with an applicable usage plan, API Gateway can return:

```http
HTTP/2 403
```

```json
{
  "message": "Forbidden"
}
```

In this lab, we create an Amazon API Gateway REST API exposing a `GET /orders` endpoint integrated with a Python AWS Lambda function.

The API is configured with:

```text
apiKeyRequired = true
```

We then create an API key and a usage plan with request throttling and a daily quota.

However, we intentionally do not associate the API key with the usage plan.

We reproduce three HTTP 403 failure scenarios:

1. Request without an API key.
2. Request with an invalid API key.
3. Request with a valid and enabled API key that is not associated with the usage plan.

We investigate the failures using AWS CLI, curl, API Gateway methods, API keys, usage plans, usage plan keys, Lambda configuration, and CloudWatch.

The investigation identifies the missing API key-to-usage-plan association as the root cause of the primary incident.

We restore access using:

```bash
aws apigateway create-usage-plan-key
```

After associating the API key, we repeat the original request and verify HTTP 200.

The Lambda application code and API Gateway deployment remain unchanged.

Finally, we review API key security, usage plan throttling, production troubleshooting practices, cost considerations, and AWS resource cleanup.

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
Enable apiKeyRequired
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
Create API Gateway Usage Plan
           |
           v
Associate API dev Stage
           |
           v
Configure Throttling and Quota
           |
           v
Create Enabled API Key
           |
           v
Intentionally Skip Usage Plan Key Association
           |
           v
Test Without API Key — HTTP 403
           |
           v
Test Invalid API Key — HTTP 403
           |
           v
Test Valid Unassociated Key — HTTP 403
           |
           v
Investigate API Method
           |
           v
Verify API Key Is Enabled
           |
           v
Inspect Usage Plan
           |
           v
Verify API Stage Association
           |
           v
List Usage Plan Keys
           |
           v
Identify Missing API Key Association
           |
           v
Restore Usage Plan Key Association
           |
           v
Verify API Key Association
           |
           v
Repeat GET /orders Request
           |
           v
Verify HTTP 200
           |
           v
Confirm Lambda Execution
           |
           v
Inspect CloudWatch Metrics
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-007 |
| Lab Name | API Key / Usage Plan Misconfiguration |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab07-key-troubleshooting` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Method Authorization | NONE — temporary lab |
| API Key Required | `true` |
| API Key Source | HEADER |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab07-order-handler` |
| Lambda Execution Role | `api-lab07-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| API Key Name | `api-lab07-partner-key` |
| Usage Plan Name | `api-lab07-partner-plan` |
| Usage Plan Rate Limit | 5 requests/second |
| Usage Plan Burst Limit | 10 |
| Usage Plan Daily Quota | 1,000 requests |
| Broken Configuration | API key not associated with usage plan |
| Broken HTTP Response | 403 |
| Recovered HTTP Response | 200 |
| CloudWatch API Metric | `4XXError` |
| CloudWatch Lambda Metric | `Invocations` |
| CloudWatch Log Marker | `LAB07_ORDER_SUCCESS` |
| Root Cause | Missing usage plan key association |
| Remediation | `create-usage-plan-key` |
| Lambda Code Changes | Not required |
| API Redeployment | Not required |
| Cleanup | API Gateway, API Key, Usage Plan, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand API Gateway API keys.
- Understand API Gateway usage plans.
- Configure REST API methods requiring API keys.
- Understand the `apiKeyRequired` property.
- Understand the `x-api-key` request header.
- Create and enable an API Gateway API key.
- Create a usage plan.
- Associate an API stage with a usage plan.
- Configure request throttling and quotas.
- Reproduce HTTP 403 errors.
- Investigate missing API keys.
- Investigate invalid API keys.
- Investigate valid but unassociated API keys.
- Inspect usage plan key associations.
- Understand API key validation.
- Distinguish API key management from authentication.
- Investigate Lambda invocation behavior.
- Inspect CloudWatch Logs and metrics.
- Apply least-privilege remediation.
- Verify successful recovery.
- Protect API key values.
- Practice production root cause analysis.
- Clean up AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management platform using Amazon API Gateway and AWS Lambda.

The company provides an API endpoint to an approved business partner.

The partner sends:

```http
GET /dev/orders
x-api-key: <partner-api-key>
```

The API Gateway REST API requires an API key.

The organization also uses a usage plan to control partner API consumption.

The usage plan has:

```text
Rate Limit: 5 requests per second

Burst Limit: 10 requests

Daily Quota: 1000 requests
```

The API key is created and enabled.

However, during an infrastructure configuration deployment, the API key-to-usage-plan association is omitted.

The partner begins receiving:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Forbidden"
}
```

The partner reports that the API key is correct.

The Cloud Engineering team investigates.

The engineer verifies:

- The REST API exists.
- The `dev` stage is deployed.
- The `/orders` resource exists.
- The GET method is configured.
- `apiKeyRequired` is enabled.
- Lambda proxy integration is correct.
- The Lambda function is Active.
- The API key exists.
- The API key is enabled.
- The usage plan exists.
- The usage plan includes the correct API stage.
- The API key is not associated with the usage plan.

The investigation confirms that API Gateway rejects the request before invoking Lambda.

The Cloud Engineer restores the API key association with the usage plan.

After remediation, the same request returns HTTP 200.

### Incident Symptoms

- API Gateway returns HTTP 403.
- The response contains `Forbidden`.
- The client supplies an API key.
- The API key is valid and enabled.
- The method requires an API key.
- The usage plan exists.
- The requested stage is included in the usage plan.
- The API key-to-usage-plan association is missing.
- Lambda remains healthy.
- Failed requests do not execute the Lambda handler.
- Associating the key with the usage plan resolves the incident.

### Business Impact

An API key or usage plan misconfiguration can cause:

- Failed partner API requests.
- Interrupted business integrations.
- Unavailable order information.
- Failed automated workflows.
- Increased API Gateway 4XX errors.
- Application integration outages.
- Delayed partner transactions.
- Increased operational support tickets.
- Reduced service reliability.

### Objective

Identify whether HTTP 403 originates from a missing API key, invalid API key, disabled API key, incorrect API stage association, or missing usage plan key association.

Restore access using the smallest required configuration change without disabling API key enforcement or modifying the backend application.

---

## 3. AWS Architecture

### Intended Healthy Architecture

```text
                Partner API Client
                       |
                       v
                 GET /dev/orders
                       |
                       v
                x-api-key Header
                       |
                       v
                Amazon API Gateway
                       |
                       v
                 REST API /dev
                       |
                       v
                 GET /orders
                       |
                       v
               apiKeyRequired=true
                       |
                       v
                 API Key Validation
                       |
                       v
                  API Key Enabled
                       |
                       v
                    Usage Plan
                       |
                       v
                  API Stage Match
                       |
                       v
               API Key Association
                       |
                       v
               Request Authorized
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

### Broken Architecture

```text
                Partner API Client
                       |
                       v
                 GET /dev/orders
                       |
                       v
                Valid x-api-key
                       |
                       v
                Amazon API Gateway
                       |
                       v
                API Key Validation
                       |
                       v
                 API Key Exists
                       |
                       v
                API Key Is Enabled
                       |
                       v
                 Check Usage Plan
                       |
                       v
                Usage Plan Exists
                       |
                       v
                API Stage Matches
                       |
                       v
              API Key Association?
                       |
                       v
                      NO
                       |
                       v
                Request Rejected
                       |
                       v
                HTTP 403 Forbidden
                       |
                       v
               Lambda Not Invoked
```

### Recovered Architecture

```text
                Partner API Client
                       |
                       v
                 GET /dev/orders
                       |
                       v
                Valid x-api-key
                       |
                       v
                Amazon API Gateway
                       |
                       v
                  API Key Validation
                       |
                       v
                 Usage Plan Lookup
                       |
                       v
                API Key Associated
                       |
                       v
               API Stage Included
                       |
                       v
                 Request Accepted
                       |
                       v
             Lambda Proxy Integration
                       |
                       v
                   AWS Lambda
                       |
                       v
               LAB07_ORDER_SUCCESS
                       |
                       v
                   HTTP 200 OK
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives API requests |
| REST API | Defines resources and methods |
| GET /orders | Retrieves order information |
| `apiKeyRequired` | Enables API key requirement |
| API Key | Identifies API consumer |
| Usage Plan | Associates API stages and keys and defines usage limits |
| Usage Plan Key | Connects API key to usage plan |
| API Stage | Hosts deployed API configuration |
| Lambda Proxy Integration | Invokes Lambda |
| AWS Lambda | Processes order requests |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Allows API Gateway invocation |
| CloudWatch Logs | Records backend activity |
| CloudWatch Metrics | Tracks API and Lambda behavior |
| curl | Tests API responses |
| AWS CLI | Manages and investigates AWS services |

---

## 4. Understanding API Keys and Usage Plans

### What Is an API Gateway API Key?

An API key is an identifier that a client supplies when calling an API method requiring a key.

For an API using HEADER as the API key source, the client provides:

```http
x-api-key: <api-key-value>
```

API Gateway checks whether the key can be used for the requested API stage.

### What Is a Usage Plan?

A usage plan connects API keys to deployed REST API stages.

It can also configure:

- Request rate limits.
- Burst limits.
- Daily, weekly, or monthly quotas.
- Method-level throttling settings.

### API Key vs. Usage Plan

| Component | Purpose |
|---|---|
| API Key | Identifies API consumer |
| Usage Plan | Defines associated API stages and usage limits |
| Usage Plan Key | Associates an API key with a usage plan |
| API Stage | Identifies deployed API environment |
| `apiKeyRequired` | Requires a key for the method |

### API Key Validation Flow

```text
Client Request
      |
      v
API Gateway Method
      |
      v
apiKeyRequired=true
      |
      v
Read x-api-key Header
      |
      v
Check API Key
      |
      v
Key Exists?
      |
      v
Key Enabled?
      |
      v
Usage Plan Association?
      |
      v
Requested Stage Included?
      |
      v
Evaluate Applicable Usage Limits
      |
      v
Invoke Backend
```

### Important API Key Conditions

For the key to work in this lab:

1. The API Gateway method must require an API key.
2. The client must provide the correct API key value.
3. The API key must exist and be enabled.
4. The key must be associated with an applicable usage plan.
5. The usage plan must include the correct API stage.
6. The request must not be rejected by applicable throttling or quota controls.

### Important Security Concept

**API keys are not a replacement for authentication and authorization.**

They are primarily intended for API client identification and usage management.

Sensitive production APIs should use an appropriate authorization mechanism such as IAM authorization, Cognito, or an API Gateway authorizer.

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
apigateway:DELETE

logs:DescribeLogGroups
logs:FilterLogEvents
logs:DeleteLogGroup

cloudwatch:GetMetricStatistics
```

These are relevant actions rather than a complete IAM policy. Access should be restricted to approved resources wherever possible.

### Safety Rules

- Use a temporary REST API.
- Do not modify production usage plans.
- Do not modify real partner API keys.
- Use fabricated order information.
- Do not expose API key values in GitHub.
- Do not publish secrets in terminal screenshots.
- Do not share sensitive CloudWatch evidence.
- Keep local secret files protected.
- Verify resource tags before cleanup.
- Delete all temporary AWS resources after testing.

### API Authorization

This lab uses:

```text
Authorization = NONE

apiKeyRequired = true
```

This configuration isolates API key and usage plan behavior.

It does not provide strong user authentication.

Production applications should use appropriate authentication and authorization controls in addition to any API key requirements.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 07-api-key-usage-plan-misconfiguration

cd 07-api-key-usage-plan-misconfiguration
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

### Step 3 — Configure Environment Variables

```bash
export AWS_REGION="us-east-1"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab07"

export API_NAME="api-lab07-key-troubleshooting"

export FUNCTION_NAME="api-lab07-order-handler"

export ROLE_NAME="api-lab07-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export API_KEY_NAME="api-lab07-partner-key"

export USAGE_PLAN_NAME="api-lab07-partner-plan"

export PERMISSION_SID="AllowAPIGatewayLab07"
```

### Step 4 — Save Environment Variables

```bash
cat > lab07-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export API_NAME="$API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export LOG_GROUP="$LOG_GROUP"
export STAGE_NAME="$STAGE_NAME"
export API_KEY_NAME="$API_KEY_NAME"
export USAGE_PLAN_NAME="$USAGE_PLAN_NAME"
export PERMISSION_SID="$PERMISSION_SID"
EOF

chmod 600 lab07-resources.env
```

Restore when necessary:

```bash
source lab07-resources.env
```

### Step 5 — Configure Local Git Ignore Rules

Create `.gitignore` in the Lab 07 directory:

```bash
cat > .gitignore <<'EOF'
function.zip
lab07-resources.env
lab07-secrets.env
lab07-*.json
*-headers.txt
*-response.json
__pycache__/
*.pyc
EOF
```

This prevents accidental commits of local evidence, deployment packages, and the API key value stored in the secret environment file.

### Step 6 — Check Existing Resources

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

Do not overwrite existing unrelated resources.

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
  --description "API Gateway Lab 07 Lambda execution role" \
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Policy

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

The Lambda execution role allows logging.

It does not control API key validation or usage plan association.

---

## 8. Create Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info(
        "LAB07_ORDER_REQUEST method=%s path=%s",
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
        "LAB07_ORDER_SUCCESS count=%s",
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

The Lambda function retrieves fabricated order information.

When invoked successfully, it records:

```text
LAB07_ORDER_REQUEST
```

and:

```text
LAB07_ORDER_SUCCESS count=2
```

in CloudWatch Logs.

The application itself does not validate API keys.

API Gateway evaluates the API key requirement before invoking Lambda.

This separation allows us to isolate usage plan configuration failures from backend application errors.

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

If Lambda cannot assume the newly created role immediately, retry after IAM role propagation.

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

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab07-resources.env
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

## 10. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab07 API Key and Usage Plan troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_ID"

echo "export API_ID='$API_ID'" >> lab07-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_ID"

echo "export ROOT_ID='$ROOT_ID'" >> lab07-resources.env
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

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab07-resources.env
```

### Step 4 — Configure GET With API Key Required

```bash
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --authorization-type NONE \
  --api-key-required \
  --region "$AWS_REGION"
```

### Step 5 — Verify Method Configuration

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{
    Method:httpMethod,
    Authorization:authorizationType,
    APIKeyRequired:apiKeyRequired
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Method": "GET",
  "Authorization": "NONE",
  "APIKeyRequired": true
}
```

### Understanding `apiKeyRequired`

When this property is enabled, API Gateway expects an API key for requests to the method.

For this REST API, the key comes from the `x-api-key` HTTP header.

The API key requirement is separate from the `authorizationType` setting.

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

---

## 12. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab07 API key required deployment" \
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

echo "export API_URL='$API_URL'" >> lab07-resources.env
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

### Step 4 — Verify API Key Source

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --query '{Name:name,APIKeySource:apiKeySource}' \
  --output json \
  --region "$AWS_REGION"
```

For this lab, the expected API key source is:

```text
HEADER
```

This means API Gateway expects the key in the `x-api-key` header.

---

## 13. Create API Gateway Usage Plan

### Step 1 — Create Usage Plan

```bash
export USAGE_PLAN_ID=$(aws apigateway create-usage-plan \
  --name "$USAGE_PLAN_NAME" \
  --description "Lab07 Partner API Usage Plan" \
  --api-stages "apiId=$API_ID,stage=$STAGE_NAME" \
  --throttle burstLimit=10,rateLimit=5 \
  --quota limit=1000,period=DAY \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$USAGE_PLAN_ID"
```

### Step 2 — Save Usage Plan ID

```bash
echo "export USAGE_PLAN_ID='$USAGE_PLAN_ID'" >> lab07-resources.env
```

### Step 3 — Verify Usage Plan

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Rate and Quota

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query '{Name:name,APIStages:apiStages,Throttle:throttle,Quota:quota}' \
  --output json \
  --region "$AWS_REGION"
```

Expected configuration:

```json
{
  "Throttle": {
    "burstLimit": 10,
    "rateLimit": 5.0
  },
  "Quota": {
    "limit": 1000,
    "offset": 0,
    "period": "DAY"
  }
}
```

The complete response also includes the usage plan name and API stage information.

### Usage Plan Configuration

| Setting | Value |
|---|---|
| Usage Plan | `api-lab07-partner-plan` |
| API | Lab 07 REST API |
| Stage | `dev` |
| Rate Limit | 5 requests/second |
| Burst Limit | 10 |
| Quota | 1,000 requests/day |

### Important Concept

Creating a usage plan does not automatically associate every API key with it.

The API key association must be configured separately.

---

## 14. Create and Verify API Key

### Step 1 — Create API Key

```bash
export API_KEY_ID=$(aws apigateway create-api-key \
  --name "$API_KEY_NAME" \
  --description "Lab07 Partner API Key" \
  --enabled \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_KEY_ID"
```

### Step 2 — Save API Key ID

```bash
echo "export API_KEY_ID='$API_KEY_ID'" >> lab07-resources.env
```

### Step 3 — Retrieve API Key Value

```bash
export API_KEY_VALUE=$(aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --include-value \
  --query value \
  --output text \
  --region "$AWS_REGION")
```

Do not print the API key value in screenshots or public logs.

### Step 4 — Save Secret Locally

```bash
umask 077

printf 'export API_KEY_VALUE=%q\n' "$API_KEY_VALUE" \
  > lab07-secrets.env

chmod 600 lab07-secrets.env
```

The file `lab07-secrets.env` is ignored by Git.

### Step 5 — Verify API Key Is Enabled

```bash
aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --query '{Id:id,Name:name,Enabled:enabled}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Id": "example-key-id",
  "Name": "api-lab07-partner-key",
  "Enabled": true
}
```

The ID is illustrative.

### Step 6 — Verify Association Is Missing

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "items": []
}
```

The real API response may include pagination fields.

### Fault Injection Setup

At this point:

- The REST API exists.
- The GET method requires an API key.
- Lambda integration is configured.
- The API is deployed.
- The usage plan exists.
- The correct API stage is associated.
- The API key exists and is enabled.
- The API key is not associated with the usage plan.

This is the intentionally broken configuration.

---

## 15. Fault Injection — Missing API Key

### Step 1 — Send Request Without API Key

```bash
curl -i "$API_URL"
```

Expected:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Forbidden"
}
```

### Step 2 — Save Broken Response

```bash
curl -sS \
  -D missing-key-headers.txt \
  -o missing-key-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

Expected:

```text
HTTP Status: 403
```

### Step 3 — Inspect Error Response

```bash
python3 -m json.tool missing-key-response.json
```

### Step 4 — Verify HTTP Status

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL")

if [ "$STATUS" = "403" ]; then
  echo "SUCCESS: Missing API key failure reproduced"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Findings

| Check | Result |
|---|---|
| GET /orders | Exists |
| API key required | Yes |
| API key provided | No |
| Gateway response | 403 |
| Lambda invocation | Not reached |
| Failure reason | Missing API key |

---

## 16. Fault Injection — Invalid API Key

### Step 1 — Send Invalid API Key

```bash
curl -i "$API_URL" \
  -H "x-api-key: invalid-lab07-api-key"
```

Expected:

```http
HTTP/2 403
```

### Step 2 — Save Broken Response

```bash
curl -sS \
  -D invalid-key-headers.txt \
  -o invalid-key-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL" \
  -H "x-api-key: invalid-lab07-api-key"
```

Expected:

```text
HTTP Status: 403
```

### Step 3 — Inspect Error

```bash
python3 -m json.tool invalid-key-response.json
```

Expected body:

```json
{
  "message": "Forbidden"
}
```

### Step 4 — Compare Missing and Invalid Key Responses

```bash
cat missing-key-response.json

cat invalid-key-response.json
```

Both requests are expected to fail.

### Findings

| Check | Result |
|---|---|
| API method | Correct |
| API key required | Yes |
| Supplied API key | Invalid |
| Key recognized | No |
| HTTP response | 403 |
| Lambda invocation | Not reached |

**Important:** The generic HTTP 403 response does not provide enough information by itself to distinguish every API key configuration problem.

The engineer must inspect API Gateway configuration and key associations.

---

## 17. Fault Injection — Valid API Key Without Usage Plan Association

### Step 1 — Verify API Key Is Enabled

```bash
aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --query '{Name:name,Enabled:enabled}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Name": "api-lab07-partner-key",
  "Enabled": true
}
```

### Step 2 — Send Request With Valid API Key

```bash
curl -i "$API_URL" \
  -H "x-api-key: $API_KEY_VALUE"
```

Expected:

```http
HTTP/2 403
```

Response:

```json
{
  "message": "Forbidden"
}
```

### Step 3 — Save Broken Response

```bash
curl -sS \
  -D unassociated-key-headers.txt \
  -o unassociated-key-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL" \
  -H "x-api-key: $API_KEY_VALUE"
```

Expected:

```text
HTTP Status: 403
```

### Step 4 — Verify Error Body

```bash
python3 -m json.tool unassociated-key-response.json
```

### Step 5 — Validate Error

```bash
python3 - <<'PY'
import json

with open("unassociated-key-response.json") as file:
    response = json.load(file)

assert response["message"] == "Forbidden"

print("SUCCESS: Unassociated API key failure reproduced")
PY
```

### Step 6 — Compare Three Failure Scenarios

| Scenario | API Key | Usage Plan Association | HTTP Status |
|---|---|---|---|
| Missing API key | Not provided | N/A | 403 |
| Invalid API key | Unrecognized | N/A | 403 |
| Valid unassociated key | Enabled | Missing | 403 |
| Correctly associated key | Enabled | Present | 200 after recovery |

### Broken-State Findings

The API key is valid.

The API key is enabled.

The usage plan exists.

The API stage is configured.

However, the API key is not associated with the usage plan.

This is the primary production incident reproduced in Lab 07.

---

## 18. Investigate API Gateway Configuration

### Step 1 — Inspect REST API

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

### Step 2 — Inspect API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].{Path:path,ID:id}' \
  --output table \
  --region "$AWS_REGION"
```

### Step 3 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 4 — Verify API Key Requirement

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query '{Method:httpMethod,APIKeyRequired:apiKeyRequired}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Method": "GET",
  "APIKeyRequired": true
}
```

### Step 5 — Inspect Lambda Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Step 6 — Inspect API Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Inspect API Key Source

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --query '{APIKeySource:apiKeySource}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "APIKeySource": "HEADER"
}
```

### Investigation Summary

| Component | Finding |
|---|---|
| REST API | Exists |
| `/orders` | Exists |
| GET method | Correct |
| API key required | True |
| API key source | HEADER |
| Lambda integration | Correct |
| API stage | Deployed |
| API Gateway configuration | Healthy |
| Remaining investigation | API key and usage plan associations |

---

## 19. Investigate API Key and Usage Plan

### Step 1 — Inspect API Key

```bash
aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --query '{Id:id,Name:name,Enabled:enabled}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```text
Enabled = true
```

### Step 2 — Inspect Usage Plan

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --region "$AWS_REGION"
```

### Step 3 — Verify Usage Plan API Stage

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query 'apiStages' \
  --output json \
  --region "$AWS_REGION"
```

The expected stage association contains the Lab 07 API ID and `dev`.

### Step 4 — List Associated API Keys

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "items": []
}
```

### Step 5 — Search Usage Plans by API Key ID

```bash
aws apigateway get-usage-plans \
  --key-id "$API_KEY_ID" \
  --output json \
  --region "$AWS_REGION"
```

The Lab 07 usage plan should not appear before remediation.

### Step 6 — Save Usage Plan Evidence

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --output json \
  --region "$AWS_REGION" \
  > lab07-usage-plan-evidence.json
```

### Step 7 — Save Missing Association Evidence

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --output json \
  --region "$AWS_REGION" \
  > lab07-broken-usage-plan-keys.json
```

### Investigation Findings

1. The REST API is correctly configured.
2. GET requires an API key.
3. The API key exists.
4. The API key is enabled.
5. The usage plan exists.
6. The usage plan includes the `dev` stage.
7. The API key is missing from the usage plan's associated keys.
8. API Gateway rejects requests using the unassociated key.

**Confirmed root cause:** Missing API key-to-usage-plan association.

---

## 20. Investigate CloudWatch Logs and Metrics

### Step 1 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

The failed API key requests are not expected to execute the Lambda handler.

Therefore, the rejected requests should not generate new Lambda application logs.

The Lambda log group may not exist yet because no invocation has succeeded.

A missing log group does not automatically indicate that the function is broken.

### Step 2 — Define Metric Time Range

```bash
export START_TIME=$(date -u -d '30 minutes ago' '+%Y-%m-%dT%H:%M:%SZ')

export END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
```

### Step 3 — Inspect API Gateway 4XXError

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

Expected: a nonzero 4XX datapoint after failed requests are reported, subject to metric aggregation and publication delay.

### Step 4 — Inspect Lambda Invocations

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

Expected: no successful Lambda invocation caused by rejected API key requests.

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
  > lab07-api-4xx-metric.json
```

### Step 6 — Save Lambda Metric Evidence

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
  > lab07-lambda-invocations-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 4XXError | Increases |
| Lambda Invocations | No invocation from rejected requests |
| Lambda Errors | No execution error caused by rejected requests |
| Lambda application logs | No new handler log from rejected requests |
| HTTP status | 403 |

CloudWatch metrics may be delayed and aggregated.

API-level metrics should be interpreted together with request tests and configuration evidence.

---

## 21. Root Cause Analysis

### Root Cause

The primary incident was caused by a missing association between the enabled API key and the usage plan.

The API Gateway method was configured correctly.

The usage plan existed and included the correct API stage.

However, the API key was not included in the usage plan's associated keys.

As a result, API Gateway rejected the request with HTTP 403 before invoking Lambda.

### Root Cause Diagram

```text
GET /dev/orders
       |
       v
Amazon API Gateway
       |
       v
apiKeyRequired=true
       |
       v
Read x-api-key
       |
       v
API Key Exists
       |
       v
API Key Enabled
       |
       v
Check Usage Plan
       |
       v
Usage Plan Exists
       |
       v
API Stage Matches
       |
       v
API Key Association Missing
       |
       v
Request Rejected
       |
       v
HTTP 403 Forbidden
```

### Five Whys

**Why 1 — Why did the API return HTTP 403?**

API Gateway rejected the API key for the requested endpoint.

**Why 2 — Why was the valid API key rejected?**

The key was not associated with an applicable usage plan.

**Why 3 — Why was the association missing?**

The API key and usage plan were created independently, but the association step was omitted.

**Why 4 — Why was the misconfiguration not detected earlier?**

The deployment did not include an integration test using the enabled partner API key.

**Why 5 — How can the incident be prevented?**

Manage API keys, usage plans, and associations with Infrastructure as Code, require deployment reviews, and run integration tests against protected endpoints.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-007 |
| HTTP Error | 403 |
| Error Message | Forbidden |
| API Resource | /orders |
| HTTP Method | GET |
| API Key Required | True |
| API Key Enabled | True |
| Usage Plan | Exists |
| API Stage | Correct |
| Missing Configuration | Usage plan key association |
| Root Cause | Unassociated API key |
| Remediation | Create usage plan key association |
| Lambda Code Changes | None |
| API Redeployment | Not required |

---

## 22. Remediation — Restore API Key Association

### Step 1 — Associate API Key With Usage Plan

```bash
aws apigateway create-usage-plan-key \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --key-id "$API_KEY_ID" \
  --key-type API_KEY \
  --region "$AWS_REGION"
```

This creates the missing association.

### Step 2 — Verify Associated Keys

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query 'items[].{Id:id,Name:name,Type:type}' \
  --output table \
  --region "$AWS_REGION"
```

Expected: the API key named `api-lab07-partner-key` appears.

### Step 3 — Verify Usage Plan by Key ID

```bash
aws apigateway get-usage-plans \
  --key-id "$API_KEY_ID" \
  --output json \
  --region "$AWS_REGION"
```

Expected: the Lab 07 usage plan is included.

### Step 4 — Verify API Stage Association

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query 'apiStages' \
  --output json \
  --region "$AWS_REGION"
```

Confirm that the plan contains:

```text
API ID = Lab07 REST API ID

Stage = dev
```

### Step 5 — Save Recovered Association Evidence

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --output json \
  --region "$AWS_REGION" \
  > lab07-recovered-usage-plan-keys.json
```

### Why API Gateway Redeployment Is Not Required

The following configurations remain unchanged:

- REST API resource.
- GET method.
- API key requirement.
- Lambda integration.
- Deployment stage.
- Lambda application code.

Only the API key-to-usage-plan association changes.

Therefore, API Gateway does not normally require a new deployment.

API key and usage plan updates may take a short time to propagate.

---

## 23. Verify Successful Recovery

### Step 1 — Repeat Original Request

```bash
curl -i "$API_URL" \
  -H "x-api-key: $API_KEY_VALUE"
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

### Step 3 — Save Recovery Response

```bash
curl -sS \
  -D recovered-headers.txt \
  -o recovered-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL" \
  -H "x-api-key: $API_KEY_VALUE"
```

Expected:

```text
HTTP Status: 200
```

### Step 4 — Validate Response

```bash
python3 - <<'PY'
import json

with open("recovered-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2
assert response["orders"][0]["order_id"] == "1001"

print("SUCCESS: API key and usage plan issue resolved")
PY
```

### Step 5 — Verify HTTP Status Automatically

```bash
STATUS=$(curl -sS \
  -o /dev/null \
  -w '%{http_code}' \
  "$API_URL" \
  -H "x-api-key: $API_KEY_VALUE")

if [ "$STATUS" = "200" ]; then
  echo "SUCCESS: API Gateway access restored"
else
  echo "Unexpected HTTP status: $STATUS"
fi
```

### Step 6 — Verify CloudWatch Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected:

```text
LAB07_ORDER_REQUEST method=GET path=/orders

LAB07_ORDER_SUCCESS count=2
```

### Step 7 — Save Recovery Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB07_ORDER_SUCCESS"' \
  --output json \
  --region "$AWS_REGION" \
  > lab07-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| REST API | Healthy | Healthy |
| GET method | Correct | Correct |
| API key required | True | True |
| API key | Enabled | Enabled |
| Usage plan | Exists | Exists |
| API stage association | Correct | Correct |
| API key association | Missing | Present |
| Lambda integration | Correct | Correct |
| Lambda execution | Not reached | Successful |
| HTTP response | 403 | 200 |
| Lambda code | Unchanged | Unchanged |
| API deployment | Unchanged | Unchanged |

**Recovery is verified when the original request with the approved API key returns HTTP 200 and CloudWatch confirms that Lambda processed the request.**

---

## 24. Additional Production Troubleshooting Scenarios

### Scenario 1 — Disabled API Key

**Symptom:** A client provides an existing API key but receives HTTP 403.

**Investigation:**

```bash
aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --query '{Enabled:enabled,Name:name}' \
  --output json
```

If the key is disabled, an authorized administrator can investigate whether it should be re-enabled.

**Remediation:** Restore the intended key state after confirming the key is approved for use.

### Scenario 2 — Incorrect API Stage Association

**Symptom:** The API key works in one environment but fails in another.

**Possible Cause:** The usage plan includes `dev` but not `prod`.

**Investigation:**

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query 'apiStages'
```

**Remediation:** Associate the intended API stage with the appropriate usage plan.

### Scenario 3 — Incorrect API Key Header

The client might send:

```http
Authorization: api-key-value
```

instead of:

```http
x-api-key: api-key-value
```

For an API using HEADER as its API key source, the expected header is `x-api-key`.

**Remediation:** Correct the client request header.

### Scenario 4 — Wrong Usage Plan

A valid API key may be associated with a usage plan that does not include the requested API stage.

**Investigation:**

```bash
aws apigateway get-usage-plans \
  --key-id "$API_KEY_ID"
```

**Remediation:** Confirm the correct plan and stage relationship.

### Scenario 5 — API Throttling

**Symptom:** The client receives HTTP 429.

**Possible Cause:** Request rate exceeds applicable throttling limits.

**Investigation:**

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --query '{Throttle:throttle}'
```

**Remediation:** Investigate traffic patterns, optimize client retries, or adjust approved limits when justified.

### Scenario 6 — API Quota Exceeded

A client may exceed an API usage plan quota.

API Gateway can reject additional requests with HTTP 429.

**Investigation:** Inspect the usage plan quota and usage data.

### Scenario 7 — API Key Required Setting Disabled

**Symptom:** Requests succeed without an API key.

**Investigation:**

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --query 'apiKeyRequired'
```

Expected for protected methods:

```text
true
```

**Remediation:** Configure the method according to the intended API contract and redeploy when changing REST API method settings.

### Troubleshooting Comparison

| Symptom | Possible Cause | Investigation |
|---|---|---|
| HTTP 403 | Missing API key | Request headers |
| HTTP 403 | Invalid API key | API key configuration |
| HTTP 403 | Disabled API key | Key enabled state |
| HTTP 403 | Missing usage plan association | Usage plan keys |
| HTTP 403 | Wrong API stage association | Usage plan API stages |
| HTTP 429 | Rate limit exceeded | Throttling settings |
| HTTP 429 | Quota exceeded | Usage plan quota |
| Request succeeds without key | API key not required | Method configuration |

---

## 25. Cloud Security Engineering Considerations

### API Keys Are Not Authentication

An API key identifies an API consumer for usage management.

It should not be treated as a complete authentication or authorization mechanism.

For sensitive production APIs, use appropriate access controls such as IAM authorization, Cognito, JWT authorizers, or another supported authorization mechanism.

### Protect API Key Values

API keys should not be exposed in:

```text
GitHub repositories
Public README files
Screenshots
Public logs
Frontend source code
Shared documents
```

Store values in approved secrets-management systems when appropriate.

### Avoid Hardcoding Keys

Do not write API key values directly into application source code.

For local labs, use protected environment variables or a local ignored secret file.

### Use HTTPS

Send API keys over HTTPS to protect them in transit.

The default API Gateway invoke URL uses HTTPS.

### Rotate Compromised Keys

If a key is accidentally exposed, treat it as compromised.

Replace or rotate it according to the organization's key-management process.

### Restrict AWS Management Permissions

IAM principals managing API keys and usage plans should have only the permissions required for their responsibilities.

### Monitor Usage Patterns

Monitor unexpected increases in:

- API Gateway requests.
- HTTP 403 errors.
- HTTP 429 errors.
- API usage by key.
- API stage traffic.
- Configuration changes.

### Usage Plans Are Not Hard Security Boundaries

Usage plan throttling and quotas are best-effort controls.

They should not be relied on as guaranteed spending limits or strong protection against abusive traffic.

For production protection, combine appropriate authentication, authorization, AWS WAF rules where applicable, request validation, monitoring, and cost controls.

### Infrastructure as Code

Manage API Gateway resources using Terraform or CloudFormation.

Relevant resources include:

```text
AWS::ApiGateway::RestApi
AWS::ApiGateway::Method
AWS::ApiGateway::Deployment
AWS::ApiGateway::Stage
AWS::ApiGateway::ApiKey
AWS::ApiGateway::UsagePlan
AWS::ApiGateway::UsagePlanKey
```

### Important Security Principle

**Do not disable API key enforcement merely to resolve HTTP 403. Identify the actual configuration issue and restore the intended association.**

---

## 26. Cost Management

### Potential Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Request charges |
| AWS Lambda | Invocation and execution charges |
| CloudWatch Logs | Log ingestion and retention |
| CloudWatch Metrics | Applicable monitoring charges |
| Usage Plan | No separate standard usage plan charge |
| API Key | No separate standard API key charge |
| IAM | No separate standard IAM role charge |

### Cost Optimization

- Use a temporary REST API.
- Keep Lambda memory at 128 MB.
- Limit unnecessary requests.
- Avoid generating large volumes of test traffic.
- Delete unused API keys.
- Delete unused usage plans.
- Remove temporary Lambda and API resources.
- Do not rely on usage plan quotas alone to control AWS spending.

### Infrastructure Not Required

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

**Warning:** Delete only resources created for Lab 07.

### Step 1 — Verify REST API Tags

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

### Step 4 — Verify Usage Plan Tags

```bash
aws apigateway get-tags \
  --resource-arn "arn:aws:apigateway:${AWS_REGION}::/usageplans/${USAGE_PLAN_ID}" \
  --region "$AWS_REGION"
```

### Step 5 — Verify API Key Tags

```bash
aws apigateway get-tags \
  --resource-arn "arn:aws:apigateway:${AWS_REGION}::/apikeys/${API_KEY_ID}" \
  --region "$AWS_REGION"
```

Confirm the resources belong to:

```text
Project = API-Gateway-Troubleshooting-Lab07
```

### Step 6 — Delete Usage Plan Key Association

```bash
aws apigateway delete-usage-plan-key \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --key-id "$API_KEY_ID" \
  --region "$AWS_REGION"
```

### Step 7 — Delete Usage Plan

```bash
aws apigateway delete-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --region "$AWS_REGION"
```

### Step 8 — Delete API Key

```bash
aws apigateway delete-api-key \
  --api-key "$API_KEY_ID" \
  --region "$AWS_REGION"
```

### Step 9 — Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

### Step 10 — Delete Lambda Function

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 11 — Detach IAM Logging Policy

```bash
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

### Step 12 — Delete IAM Role

```bash
aws iam delete-role \
  --role-name "$ROLE_NAME"
```

### Step 13 — Delete CloudWatch Log Group

```bash
aws logs delete-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

If the log group was not created, AWS may return `ResourceNotFoundException`.

### Step 14 — Clear API Key From Environment

```bash
unset API_KEY_VALUE

rm -f lab07-secrets.env
```

### Step 15 — Verify REST API Deletion

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 16 — Verify API Key Deletion

```bash
aws apigateway get-api-key \
  --api-key "$API_KEY_ID" \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 17 — Verify Usage Plan Deletion

```bash
aws apigateway get-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

### Step 18 — Verify Lambda Deletion

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected:

```text
ResourceNotFoundException
```

### Step 19 — Verify IAM Role Deletion

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected:

```text
NoSuchEntity
```

### Step 20 — Verify CloudWatch Cleanup

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
| API methods and resources | Deleted |
| Usage plan key association | Deleted |
| Usage plan | Deleted |
| API key | Deleted |
| Lambda function | Deleted |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| Local API key secret | Removed |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |

---

## 28. Interview Questions and Answers

### Q1. What is an API Gateway API key?

An API key identifies an API consumer and is used with API Gateway usage plans for API access and usage management.

### Q2. What is an API Gateway usage plan?

A usage plan associates API keys with deployed API stages and can define request throttling and quotas.

### Q3. What caused HTTP 403 in this lab?

The valid API key was not associated with the usage plan containing the requested API stage.

### Q4. Can a valid and enabled API key still return HTTP 403?

Yes. If the key is not associated with an applicable usage plan, API Gateway can reject the request.

### Q5. What does `apiKeyRequired=true` mean?

It means the API Gateway method requires an API key.

### Q6. Which HTTP header contains the API key?

For an API using HEADER as its API key source:

```http
x-api-key: <api-key-value>
```

### Q7. How do you inspect an API key?

```bash
aws apigateway get-api-key \
  --api-key API_KEY_ID
```

### Q8. How do you inspect a usage plan?

```bash
aws apigateway get-usage-plan \
  --usage-plan-id USAGE_PLAN_ID
```

### Q9. How do you list API keys associated with a usage plan?

```bash
aws apigateway get-usage-plan-keys \
  --usage-plan-id USAGE_PLAN_ID
```

### Q10. How do you associate an API key with a usage plan?

Use:

```bash
aws apigateway create-usage-plan-key \
  --usage-plan-id USAGE_PLAN_ID \
  --key-id API_KEY_ID \
  --key-type API_KEY
```

### Q11. Why might Lambda have no logs when the API returns HTTP 403?

API Gateway can reject the request during API key validation before the Lambda handler executes.

### Q12. Does correcting the usage plan key association require API redeployment?

Normally no. The API method and integration remain unchanged.

### Q13. What is the difference between HTTP 403 and HTTP 429 in this context?

HTTP 403 indicates a forbidden request, such as a missing or invalid API key.

HTTP 429 indicates the client is being throttled or has exceeded applicable usage limits.

### Q14. Are API keys a secure replacement for authentication?

No. API keys are primarily intended for API client identification and usage management.

### Q15. Can an API key belong to multiple usage plans?

Yes, subject to API Gateway's association constraints. A given key cannot be associated with different usage plans for the same API stage.

### Q16. How do you prevent usage plan misconfiguration?

Manage the key, usage plan, API stage, and association through reviewed Infrastructure as Code and automated integration tests.

### Q17. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

The API exposed a GET endpoint that required an API key.

I created an enabled API key and a usage plan containing the API's `dev` stage.

The usage plan had a request rate limit, burst limit, and daily quota.

To simulate a production misconfiguration, I intentionally omitted the API key-to-usage-plan association.

I reproduced HTTP 403 using three scenarios: no API key, an invalid key, and a valid but unassociated key.

I investigated the API method configuration, API key enabled state, usage plan, API stage association, Lambda integration, CloudWatch Logs, and metrics.

The investigation confirmed that the valid API key was missing its usage plan association.

I restored the association using the AWS CLI `create-usage-plan-key` command.

After the configuration change, the API returned HTTP 200 and Lambda successfully processed the request.

I completed the remediation without modifying the Lambda application code or redeploying API Gateway.

Finally, I verified the association, reviewed API key security, and removed the temporary resources.

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
│   ├── README.md
│   ├── .gitignore
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── function.zip
│   ├── lab07-resources.env
│   ├── lab07-secrets.env
│   ├── missing-key-headers.txt
│   ├── missing-key-response.json
│   ├── invalid-key-headers.txt
│   ├── invalid-key-response.json
│   ├── unassociated-key-headers.txt
│   ├── unassociated-key-response.json
│   ├── recovered-headers.txt
│   ├── recovered-response.json
│   ├── lab07-usage-plan-evidence.json
│   ├── lab07-broken-usage-plan-keys.json
│   ├── lab07-recovered-usage-plan-keys.json
│   ├── lab07-api-4xx-metric.json
│   ├── lab07-lambda-invocations-metric.json
│   └── lab07-recovered-cloudwatch-evidence.json
│
├── 08-api-throttling-429/
├── 09-api-timeout-504/
└── 10-custom-domain-certificate-failure/
```

### File Descriptions

| File | Purpose |
|---|---|
| README.md | Incident documentation and remediation |
| .gitignore | Excludes secrets and local evidence |
| lambda_function.py | Python orders API backend |
| lambda-trust-policy.json | Lambda IAM trust policy |
| function.zip | Generated Lambda deployment package |
| lab07-resources.env | Local AWS resource variables |
| lab07-secrets.env | Protected local API key value |
| missing-key-headers.txt | Missing API key HTTP 403 headers |
| missing-key-response.json | Missing API key error response |
| invalid-key-headers.txt | Invalid API key HTTP 403 headers |
| invalid-key-response.json | Invalid API key error response |
| unassociated-key-headers.txt | Unassociated API key HTTP 403 headers |
| unassociated-key-response.json | Usage plan misconfiguration response |
| recovered-headers.txt | HTTP 200 headers after recovery |
| recovered-response.json | Recovered application response |
| lab07-usage-plan-evidence.json | Usage plan configuration |
| lab07-broken-usage-plan-keys.json | Missing association evidence |
| lab07-recovered-usage-plan-keys.json | Restored association evidence |
| lab07-api-4xx-metric.json | API Gateway 4XX metrics |
| lab07-lambda-invocations-metric.json | Lambda invocation metrics |
| lab07-recovered-cloudwatch-evidence.json | Successful backend execution logs |

### Recommended Public GitHub Files

```text
07-api-key-usage-plan-misconfiguration/
├── README.md
├── .gitignore
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 07
07-api-key-usage-plan-misconfiguration/function.zip
07-api-key-usage-plan-misconfiguration/lab07-resources.env
07-api-key-usage-plan-misconfiguration/lab07-secrets.env
07-api-key-usage-plan-misconfiguration/lab07-*.json
07-api-key-usage-plan-misconfiguration/*-headers.txt
07-api-key-usage-plan-misconfiguration/*-response.json

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

Never commit the API key value.

Review all files before publishing account-specific troubleshooting evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how Amazon API Gateway can reject a valid API key when its usage plan association is missing.

We created a REST API integrated with a Python Lambda function.

The API exposed a GET endpoint requiring an API key.

We created a usage plan with a request rate limit, burst limit, and daily quota.

We then created an enabled API key but intentionally omitted the association between the API key and the usage plan.

We reproduced three HTTP 403 failures.

The first occurred when the client did not provide an API key.

The second occurred when the client provided an invalid API key.

The third occurred when the client supplied a valid, enabled API key that was not associated with the usage plan.

We investigated the API Gateway method configuration, API key enabled state, usage plan, API stage, key associations, Lambda integration, CloudWatch Logs, and metrics.

The investigation confirmed that the primary incident originated from a missing usage plan key association.

We restored the association using the AWS CLI.

After remediation, the same API request returned HTTP 200 and Lambda successfully processed the order request.

The Lambda application code and API Gateway deployment did not require modifications.

Finally, the lab documented secure API key handling and AWS resource cleanup.

**Key Lesson:** An API key being valid and enabled does not guarantee that API Gateway will accept it. The key must be associated with an applicable usage plan containing the requested API stage.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- API key management
- Usage plan configuration
- Usage plan key associations
- `apiKeyRequired` configuration
- HTTP 403 troubleshooting
- HTTP 403 versus HTTP 429
- Request throttling
- API quotas
- Lambda proxy integration
- Python 3.13
- IAM execution roles
- Lambda resource-based policies
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch metrics
- Root cause analysis
- API configuration remediation
- Recovery verification
- Secure API key handling
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-007 |
| Scenario | API Key / Usage Plan Misconfiguration |
| REST API | api-lab07-key-troubleshooting |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab07-order-handler |
| API Key | api-lab07-partner-key |
| Usage Plan | api-lab07-partner-plan |
| API Key Required | True |
| Broken Configuration | Missing usage plan association |
| Missing Key Response | HTTP 403 |
| Invalid Key Response | HTTP 403 |
| Unassociated Key Response | HTTP 403 |
| Root Cause | Missing usage plan key |
| Remediation | `create-usage-plan-key` |
| Recovered API Response | HTTP 200 |
| Lambda Code Changes | None |
| API Gateway Redeployment | Not required |
| Cleanup | API Gateway, API Key, Usage Plan, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Effective API Gateway troubleshooting requires understanding the relationship between API keys, usage plans, API stages, and backend integrations. Engineers must verify each association before modifying application code or weakening security controls.

---

## Official AWS Documentation

- [Amazon API Gateway — Usage Plans and API Keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [Amazon API Gateway — Set Up API Keys](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-setup-api-keys.html)
- [Amazon API Gateway — Set Up Usage Plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-usage-plans.html)
- [Amazon API Gateway — API Key Sources](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-key-source.html)
- [Amazon API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS CLI — Create API Key](https://docs.aws.amazon.com/cli/latest/reference/apigateway/create-api-key.html)
- [AWS CLI — Create Usage Plan](https://docs.aws.amazon.com/cli/latest/reference/apigateway/create-usage-plan.html)
- [AWS CLI — Create Usage Plan Key](https://docs.aws.amazon.com/cli/latest/reference/apigateway/create-usage-plan-key.html)
- [AWS CLI — Get Usage Plan Keys](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-usage-plan-keys.html)
- [AWS CLI — Get Usage Plans](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-usage-plans.html)
- [AWS CLI — Delete Usage Plan Key](https://docs.aws.amazon.com/cli/latest/reference/apigateway/delete-usage-plan-key.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)