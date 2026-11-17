# Lab 05 — Amazon API Gateway CORS Error

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve a **Cross-Origin Resource Sharing (CORS) error** in an Amazon API Gateway REST API integrated with AWS Lambda.

In production, frontend applications often communicate with backend APIs hosted on different domains.

For example, a frontend application may run on:

`https://app.example.com`

while its backend API is hosted on:

`https://api.example.com`

Because these URLs have different origins, browsers enforce the Same-Origin Policy and use CORS to determine whether cross-origin requests are permitted.

When CORS is incorrectly configured, a browser may block a request even when the backend API is working correctly.

In this lab, we create a REST API exposing a `GET /orders` endpoint integrated with a Python Lambda function.

We first configure a healthy Lambda backend that returns HTTP 200 when invoked using curl.

However, the API Gateway REST API does not have an OPTIONS method, and the Lambda response does not include the required CORS headers.

We then create a simple HTML frontend running on `http://localhost:8000`.

The frontend sends a cross-origin request with a custom `X-Lab-Client` header, causing the browser to perform an OPTIONS preflight request.

Because the OPTIONS method is missing, API Gateway rejects the preflight request. The browser prevents the frontend from accessing the API response.

We investigate the failure using AWS CLI, curl, browser Developer Tools, API Gateway methods, Lambda configuration, and CloudWatch Logs.

After identifying the missing CORS configuration, we update the Lambda response headers and configure an OPTIONS method with Lambda proxy integration.

We redeploy the REST API and repeat the original browser request.

The recovered API successfully processes the OPTIONS preflight and GET request.

Finally, we verify the recovery, review production security considerations, and remove the temporary AWS resources.

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
Verify API Using curl — HTTP 200
           |
           v
Create Local HTML Frontend
           |
           v
Send Cross-Origin Browser Request
           |
           v
Browser Sends OPTIONS Preflight
           |
           v
API Gateway OPTIONS Method Missing
           |
           v
Preflight Returns HTTP 403
           |
           v
Browser Blocks Cross-Origin Request
           |
           v
Investigate API Gateway Methods
           |
           v
Inspect Lambda Response Headers
           |
           v
Identify Missing CORS Configuration
           |
           v
Add CORS Headers to Lambda
           |
           v
Create OPTIONS Method
           |
           v
Configure OPTIONS Lambda Integration
           |
           v
Redeploy REST API
           |
           v
Verify OPTIONS — HTTP 204
           |
           v
Verify GET — HTTP 200
           |
           v
Verify Browser Request
           |
           v
Inspect CloudWatch Recovery Logs
           |
           v
Clean Up AWS Resources
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-005 |
| Lab Name | API Gateway CORS Error |
| Difficulty | Intermediate |
| Primary Service | Amazon API Gateway |
| Supporting Services | AWS Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, Python, curl, jq |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab05-cors-troubleshooting` |
| API Resource | `/orders` |
| HTTP Methods | GET, OPTIONS |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration Type | AWS_PROXY |
| Lambda Function | `api-lab05-order-handler` |
| Lambda Execution Role | `api-lab05-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Memory | 128 MB |
| Lambda Timeout | 10 seconds |
| Frontend Origin | `http://localhost:8000` |
| Custom Request Header | `X-Lab-Client` |
| Broken Configuration | OPTIONS method and CORS headers missing |
| Broken OPTIONS Response | HTTP 403 |
| Broken GET Response | HTTP 200 without CORS headers |
| Browser Result | Cross-origin request blocked |
| Recovered OPTIONS Response | HTTP 204 |
| Recovered GET Response | HTTP 200 with CORS headers |
| Root Cause | Incomplete CORS configuration |
| Remediation | Configure OPTIONS and Lambda CORS headers |
| API Redeployment | Required for new OPTIONS method |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |

### Learning Objectives

- Understand the Same-Origin Policy.
- Understand Cross-Origin Resource Sharing.
- Distinguish origins, domains, and URL paths.
- Understand browser CORS enforcement.
- Configure API Gateway REST APIs.
- Configure Lambda proxy integration.
- Understand preflight OPTIONS requests.
- Reproduce a CORS failure.
- Investigate HTTP 403 preflight responses.
- Understand `Access-Control-Allow-Origin`.
- Understand `Access-Control-Allow-Methods`.
- Understand `Access-Control-Allow-Headers`.
- Distinguish curl results from browser behavior.
- Inspect browser Developer Tools.
- Investigate API Gateway methods.
- Identify missing CORS response headers.
- Configure OPTIONS integration.
- Update Lambda response headers.
- Redeploy an API Gateway REST API.
- Verify preflight and actual requests.
- Investigate CloudWatch Logs.
- Apply secure CORS policies.
- Perform root cause analysis.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an online order-management application.

The frontend application communicates with a backend API through Amazon API Gateway.

The frontend is hosted on:

```text
https://app.example.com
```

The backend API is hosted on:

```text
https://api.example.com
```

Customers use the frontend to retrieve order information.

The frontend sends:

```http
GET /orders
```

The API Gateway endpoint invokes a Lambda function that returns order information.

During a deployment, the frontend begins sending an additional custom header.

The browser now performs a CORS preflight request before sending the actual GET request.

However, the API Gateway REST API does not contain an OPTIONS method for the `/orders` resource.

As a result, the preflight fails.

The browser displays an error similar to:

```text
Access to fetch at 'https://api.example.com/orders'
from origin 'https://app.example.com'
has been blocked by CORS policy.
```

The frontend application cannot retrieve order information.

The backend Lambda function remains healthy.

Engineers test the endpoint using curl and receive HTTP 200.

However, the browser continues blocking the request.

The Cloud Engineering team investigates why curl works but the browser fails.

The investigation finds:

- The REST API exists.
- The GET method is deployed.
- Lambda proxy integration is configured correctly.
- Lambda returns valid JSON.
- API Gateway can invoke Lambda.
- The OPTIONS method is missing.
- The Lambda GET response does not include CORS headers.
- The browser blocks the cross-origin request.

The team configures CORS correctly and redeploys the REST API.

The browser then successfully retrieves the order data.

### Incident Symptoms

- Frontend requests fail.
- Browser Console displays a CORS error.
- Curl GET requests return HTTP 200.
- OPTIONS requests return HTTP 403.
- API Gateway has no OPTIONS method.
- Lambda returns no allow-origin header.
- The browser blocks access to the API.
- Adding OPTIONS support and CORS headers resolves the issue.

### Business Impact

Incorrect CORS configuration may cause:

- Frontend application failures.
- Inaccessible API data.
- Broken customer dashboards.
- Interrupted order-management operations.
- Failed browser-based workflows.
- Increased support tickets.
- Reduced application reliability.
- Deployment-related outages.

### Objective

Identify the CORS configuration problem, implement correct preflight handling, return appropriate response headers, and verify that the frontend can access the API without weakening authentication or authorization.

---

## 3. AWS Architecture

### Healthy Backend — Before Browser Testing

```text
                 API Client
                    |
                    v
               curl GET /orders
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
          Lambda Proxy Integration
                    |
                    v
                AWS Lambda
                    |
                    v
             Python Order Handler
                    |
                    v
              Order Data Returned
                    |
                    v
                 HTTP 200
```

The backend works because curl does not enforce browser CORS restrictions.

### Broken Browser Architecture

```text
              Browser Frontend
             localhost:8000
                    |
                    v
             JavaScript fetch()
                    |
                    v
          Custom X-Lab-Client Header
                    |
                    v
          Browser Sends Preflight
                    |
                    v
                OPTIONS /orders
                    |
                    v
             Amazon API Gateway
                    |
                    v
              OPTIONS Missing
                    |
                    v
                 HTTP 403
                    |
                    v
              Preflight Failed
                    |
                    v
             Browser Blocks GET
                    |
                    v
           Frontend Displays Error
```

### Recovered Architecture

```text
              Browser Frontend
             localhost:8000
                    |
                    v
             JavaScript fetch()
                    |
                    v
              OPTIONS /orders
                    |
                    v
             Amazon API Gateway
                    |
                    v
           OPTIONS Lambda Integration
                    |
                    v
                AWS Lambda
                    |
                    v
            Return CORS Headers
                    |
                    v
                 HTTP 204
                    |
                    v
             Preflight Accepted
                    |
                    v
               GET /orders
                    |
                    v
             Amazon API Gateway
                    |
                    v
                AWS Lambda
                    |
                    v
              Return Order Data
                    |
                    v
           HTTP 200 + CORS Headers
                    |
                    v
           Browser Accepts Response
                    |
                    v
          Orders Displayed in Frontend
```

### AWS Components

| Component | Purpose |
|---|---|
| Amazon API Gateway | Receives HTTP requests |
| GET /orders | Retrieves order information |
| OPTIONS /orders | Handles CORS preflight |
| Lambda Proxy Integration | Invokes Lambda |
| AWS Lambda | Processes GET and OPTIONS |
| IAM Execution Role | Allows Lambda logging |
| Lambda Resource Policy | Authorizes API Gateway invocation |
| CloudWatch Logs | Records Lambda execution |
| Python HTTP Server | Serves local frontend |
| Browser Developer Tools | Diagnoses CORS failures |
| curl | Tests HTTP headers and responses |
| AWS CLI | Configures and investigates resources |

---

## 4. Understanding CORS

### What Is the Same-Origin Policy?

The Same-Origin Policy is a browser security mechanism.

It restricts how scripts loaded from one origin can interact with resources from another origin.

An origin consists of:

```text
Scheme + Host + Port
```

Example:

```text
http://localhost:8000
```

Different ports, schemes, or hosts can create different origins.

### Same-Origin Examples

| Frontend | Backend | Same Origin? |
|---|---|---|
| `https://app.example.com` | `https://app.example.com/api` | Yes |
| `https://app.example.com` | `https://api.example.com` | No |
| `http://localhost:8000` | `http://localhost:3000` | No |
| `http://example.com` | `https://example.com` | No |

### What Is CORS?

Cross-Origin Resource Sharing allows a server to indicate which browser origins may access its resources.

The server provides HTTP response headers describing allowed origins, methods, and headers.

### Important CORS Headers

| Header | Purpose |
|---|---|
| `Access-Control-Allow-Origin` | Identifies an allowed browser origin |
| `Access-Control-Allow-Methods` | Identifies allowed HTTP methods for preflight |
| `Access-Control-Allow-Headers` | Identifies permitted request headers |
| `Access-Control-Allow-Credentials` | Controls credentialed cross-origin access |
| `Access-Control-Max-Age` | Allows browsers to cache preflight results |
| `Vary: Origin` | Helps caches handle origin-dependent responses |

### What Is a Preflight Request?

A browser may send an OPTIONS request before the actual request.

Example:

```http
OPTIONS /orders
Origin: http://localhost:8000
Access-Control-Request-Method: GET
Access-Control-Request-Headers: X-Lab-Client
```

The server must return an acceptable CORS response.

Example:

```http
HTTP/2 204
Access-Control-Allow-Origin: http://localhost:8000
Access-Control-Allow-Methods: GET,OPTIONS
Access-Control-Allow-Headers: Content-Type,X-Lab-Client
```

If the preflight succeeds, the browser can proceed with the GET request.

### Why This Lab Triggers Preflight

The frontend includes:

```javascript
headers: {
    "X-Lab-Client": "browser-test"
}
```

`X-Lab-Client` is a custom request header.

Because it is not a CORS-safelisted request header, the browser sends a preflight request.

### Important Distinction

CORS is not authentication.

CORS is a browser-enforced cross-origin access mechanism.

It does not replace:

- AWS IAM authorization.
- Amazon Cognito.
- JWT authorization.
- API keys.
- Application authentication.
- Backend access control.

---

## 5. Prerequisites and Safety

### Requirements

- AWS account.
- AWS CLI v2.
- WSL2 Ubuntu.
- Python 3.
- Bash.
- curl.
- jq.
- ZIP and unzip.
- Web browser with Developer Tools.
- IAM permissions.
- Lambda permissions.
- API Gateway permissions.
- CloudWatch permissions.

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
lambda:UpdateFunctionCode
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

- Use a temporary REST API.
- Do not change production APIs.
- Do not expose sensitive order data.
- Do not include real customer information.
- Avoid unnecessary wildcard CORS policies.
- Do not publish AWS credentials.
- Review CloudWatch evidence before uploading.
- Verify resource tags before cleanup.
- Delete temporary AWS resources after testing.

### API Authorization

This lab uses:

```text
Authorization = NONE
```

This is appropriate only for this temporary API with fabricated data.

Production APIs should implement suitable authentication and authorization.

---

## 6. Prepare WSL Ubuntu

### Step 1 — Create Lab Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 05-cors-error

cd 05-cors-error
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

### Step 3 — Configure Variables

```bash
export AWS_REGION="us-east-1"

export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab05"

export API_NAME="api-lab05-cors-troubleshooting"

export FUNCTION_NAME="api-lab05-order-handler"

export ROLE_NAME="api-lab05-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"

export STAGE_NAME="dev"

export PERMISSION_SID="AllowAPIGatewayLab05"

export FRONTEND_ORIGIN="http://localhost:8000"
```

### Step 4 — Save Environment Variables

```bash
cat > lab05-resources.env <<EOF
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
export FRONTEND_ORIGIN="$FRONTEND_ORIGIN"
EOF

chmod 600 lab05-resources.env
```

Restore variables when needed:

```bash
source lab05-resources.env
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
  --description "API Gateway Lab 05 Lambda execution role" \
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

## 8. Create the Broken Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info("LAB05_ORDER_REQUEST")

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

### Understanding the Broken Application

The Lambda function returns valid order information.

However, its response headers contain only:

```http
Content-Type: application/json
```

The response does not include:

```http
Access-Control-Allow-Origin
```

Therefore, browsers cannot access this response from an unrelated origin unless the required CORS authorization is supplied elsewhere.

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

If IAM role propagation causes an assume-role error, retry after the role becomes available.

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

echo "export FUNCTION_ARN='$FUNCTION_ARN'" >> lab05-resources.env
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

Expected retention:

```text
7 days
```

---

## 11. Create API Gateway REST API

### Step 1 — Create Regional REST API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab05 CORS troubleshooting" \
  --endpoint-configuration types=REGIONAL \
  --tags "Project=$PROJECT_TAG" \
  --query id \
  --output text \
  --region "$AWS_REGION")

echo "$API_ID"

echo "export API_ID='$API_ID'" >> lab05-resources.env
```

### Step 2 — Retrieve Root Resource ID

```bash
export ROOT_ID=$(aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query "items[?path=='/'].id | [0]" \
  --output text \
  --region "$AWS_REGION")

echo "$ROOT_ID"

echo "export ROOT_ID='$ROOT_ID'" >> lab05-resources.env
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

echo "export RESOURCE_ID='$RESOURCE_ID'" >> lab05-resources.env
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

### Step 4 — Grant Lambda Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/${STAGE_NAME}/*/orders" \
  --region "$AWS_REGION"
```

This source ARN allows API Gateway to invoke the function for the `/orders` resource within the lab's `dev` stage.

### Step 5 — Verify Permission

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

---

## 13. Deploy the REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab05 initial CORS troubleshooting deployment" \
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

echo "export API_URL='$API_URL'" >> lab05-resources.env
```

Example:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/orders
```

---

## 14. Verify Healthy Backend Baseline

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

### Step 4 — Validate Backend

```bash
python3 - <<'PY'
import json

with open("baseline-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: Lambda backend healthy")
PY
```

### Step 5 — Check Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected:

```text
LAB05_ORDER_REQUEST
```

The backend is healthy, but browser CORS compatibility has not been established.

---

## 15. Fault Injection — Missing CORS Configuration

### Step 1 — Simulate Browser Preflight

```bash
curl -i -X OPTIONS "$API_URL" \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-Lab-Client"
```

The API does not contain an OPTIONS method.

Expected:

```http
HTTP/2 403
```

Possible response:

```json
{
  "message": "Missing Authentication Token"
}
```

This response occurs because API Gateway cannot match the OPTIONS request to a deployed method.

It does not mean an authentication token needs to be added.

### Step 2 — Send GET With Origin Header

```bash
curl -i "$API_URL" \
  -H "Origin: http://localhost:8000"
```

Expected:

```http
HTTP/2 200
content-type: application/json
```

However, this response lacks:

```http
Access-Control-Allow-Origin: http://localhost:8000
```

### Step 3 — Save Broken Preflight Evidence

```bash
curl -sS \
  -D broken-preflight-headers.txt \
  -o broken-preflight-body.json \
  -X OPTIONS "$API_URL" \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-Lab-Client"
```

### Step 4 — Save Broken GET Evidence

```bash
curl -sS \
  -D broken-get-headers.txt \
  -o broken-get-response.json \
  "$API_URL" \
  -H "Origin: http://localhost:8000"
```

### Fault Injection Summary

| Component | State |
|---|---|
| API Gateway | Deployed |
| GET /orders | Working |
| Lambda | Active |
| OPTIONS /orders | Missing |
| Preflight HTTP response | 403 |
| Lambda allow-origin header | Missing |
| Browser access | Blocked |
| Root cause | Incomplete CORS configuration |

---

## 16. Reproduce the CORS Error in a Browser

### Step 1 — Create `index.html`

```bash
cat > index.html <<'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Lab 05 - CORS Troubleshooting</title>
</head>

<body>

    <h2>API Gateway CORS Troubleshooting</h2>

    <button onclick="testAPI()">Test API</button>

    <pre id="result"></pre>

    <script>
        async function testAPI() {

            const result =
                document.getElementById("result");

            try {

                const response = await fetch(
                    "API_URL_PLACEHOLDER",
                    {
                        method: "GET",
                        headers: {
                            "X-Lab-Client": "browser-test"
                        }
                    }
                );

                const data = await response.json();

                result.textContent =
                    JSON.stringify(data, null, 2);

            } catch (error) {

                result.textContent =
                    "Request failed: " + error.message;
            }
        }
    </script>

</body>
</html>
EOF
```

### Step 2 — Insert the API URL

```bash
python3 - <<'PY'
import os
from pathlib import Path

path = Path("index.html")

content = path.read_text()

content = content.replace(
    "API_URL_PLACEHOLDER",
    os.environ["API_URL"]
)

path.write_text(content)
PY
```

### Step 3 — Start Local HTTP Server

```bash
python3 -m http.server 8000
```

### Step 4 — Open Browser

Open:

```text
http://localhost:8000
```

Click:

```text
Test API
```

### Step 5 — Inspect Developer Tools

Open browser Developer Tools.

Navigate to:

```text
F12
 |
 v
Network
 |
 v
Fetch/XHR or All
 |
 v
OPTIONS Request
```

Also inspect the Console tab.

Expected browser error:

```text
Access to fetch has been blocked by CORS policy
```

The JavaScript may display:

```text
Request failed: Failed to fetch
```

### Step 6 — Inspect Network Request

Look for:

```http
OPTIONS /dev/orders
```

Expected response:

```http
HTTP 403
```

The browser does not proceed with the intended GET request because the preflight fails.

### Broken-State Findings

| Check | Result |
|---|---|
| Curl GET | 200 |
| Browser preflight | Failed |
| OPTIONS method | Missing |
| CORS response headers | Missing |
| Lambda backend | Healthy |
| Browser request | Blocked |

---

## 17. Investigate API Gateway Configuration

### Step 1 — Inspect REST API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$API_ID" \
  --query 'items[].{Path:path,ID:id}' \
  --output table \
  --region "$AWS_REGION"
```

Expected:

```text
/
/orders
```

### Step 2 — Inspect GET Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

The GET method should exist.

### Step 3 — Inspect OPTIONS Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method OPTIONS \
  --region "$AWS_REGION"
```

Expected:

```text
NotFoundException
```

This confirms the OPTIONS method is missing from the API configuration.

### Step 4 — Inspect GET Integration

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

### Step 5 — Inspect Lambda Response Headers

```bash
grep -n "Access-Control-Allow" lambda_function.py
```

Expected: no matches.

### Step 6 — Inspect API Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
```

### Investigation Summary

| Component | Finding |
|---|---|
| REST API | Exists |
| `/orders` resource | Exists |
| GET method | Correct |
| Lambda proxy integration | Correct |
| Lambda invocation permission | Correct |
| Lambda backend | Healthy |
| OPTIONS method | Missing |
| Allow-origin response header | Missing |
| Browser access | Blocked |

The failure is caused by CORS configuration rather than backend application availability.

---

## 18. Investigate CloudWatch Logs

### Step 1 — Inspect Recent Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected earlier GET log:

```text
LAB05_ORDER_REQUEST
```

The unsuccessful OPTIONS request does not reach the Lambda handler because API Gateway has no matching OPTIONS method.

### Step 2 — Search for GET Requests

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --filter-pattern '"LAB05_ORDER_REQUEST"' \
  --query 'events[].message' \
  --output json \
  --region "$AWS_REGION"
```

### Step 3 — Save Log Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab05-broken-cloudwatch-evidence.json
```

### Important Observation

CloudWatch Lambda logs may show successful direct GET requests while the browser application remains broken.

This is because API Gateway rejects the browser's preflight request before Lambda executes.

CloudWatch Logs alone cannot establish whether the browser accepted a CORS response.

Use browser Developer Tools and HTTP response-header inspection together with CloudWatch.

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

Expected: an API-level 4XX datapoint associated with the failed OPTIONS request after metrics become available.

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

The failed OPTIONS request is not expected to invoke Lambda.

### Step 4 — Save API Gateway Metric Evidence

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
  > lab05-api-4xx-metric.json
```

### Step 5 — Save Lambda Invocation Evidence

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
  > lab05-lambda-invocations-metric.json
```

### Metric Comparison

| Metric | Expected Observation |
|---|---|
| API Gateway 4XXError | Increases after failed OPTIONS |
| Lambda Invocations | No invocation from missing OPTIONS method |
| Lambda Errors | No backend exception caused by preflight |
| Browser Console | CORS error |
| Preflight HTTP status | 403 |
| Curl GET status | 200 |

CloudWatch metrics may take time to appear.

Not every browser-level CORS failure produces an API Gateway error metric. For example, a GET response can return HTTP 200 while the browser rejects it because its CORS headers are missing.

---

## 20. Root Cause Analysis

### Root Cause

The API Gateway REST API was not configured to support the browser's cross-origin request.

The frontend included a custom request header that triggered a CORS preflight.

API Gateway did not have an OPTIONS method for the `/orders` resource.

The preflight failed with HTTP 403.

Additionally, the Lambda GET response did not contain the required `Access-Control-Allow-Origin` header.

These two configuration problems prevented the browser from accessing the API.

### Root Cause Diagram

```text
Frontend JavaScript
        |
        v
Cross-Origin Request
        |
        v
Custom X-Lab-Client Header
        |
        v
Browser Preflight Required
        |
        v
OPTIONS /dev/orders
        |
        v
API Gateway
        |
        v
OPTIONS Method Missing
        |
        v
HTTP 403 Response
        |
        v
Preflight Rejected
        |
        v
Browser Blocks Request
        |
        v
Frontend Cannot Display Orders
```

### Five Whys

**Why 1 — Why did the frontend request fail?**

The browser blocked the cross-origin request.

**Why 2 — Why did the browser block it?**

The CORS preflight request failed.

**Why 3 — Why did the preflight fail?**

API Gateway did not have a configured OPTIONS method.

**Why 4 — Why was CORS configuration incomplete?**

The API was initially configured only for GET, and the Lambda response did not include CORS headers.

**Why 5 — How can the issue be prevented?**

Test browser-based API integration, configure preflight handling, return correct CORS headers, and validate CORS behavior during deployment.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-005 |
| Main Issue | Browser CORS failure |
| Resource | /orders |
| Actual Method | GET |
| Preflight Method | OPTIONS |
| Broken Preflight | HTTP 403 |
| Backend GET | HTTP 200 |
| Missing Configuration | OPTIONS and CORS headers |
| Root Cause | Incomplete CORS support |
| Remediation | Configure OPTIONS and response headers |
| Lambda Code Update | Required |
| API Redeployment | Required |

---

## 21. Remediation — Configure Lambda CORS Headers

### Step 1 — Update `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALLOWED_ORIGIN = "http://localhost:8000"


def lambda_handler(event, context):

    method = event.get("httpMethod")

    cors_headers = {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,X-Lab-Client",
        "Vary": "Origin"
    }

    if method == "OPTIONS":

        logger.info("LAB05_PREFLIGHT_SUCCESS")

        return {
            "statusCode": 204,
            "headers": cors_headers,
            "body": ""
        }

    logger.info("LAB05_ORDER_SUCCESS")

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

    return {
        "statusCode": 200,
        "headers": {
            **cors_headers,
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Orders retrieved successfully",
            "orders": orders
        })
    }
EOF
```

### Step 2 — Understand the Updated Headers

The response now includes:

```http
Access-Control-Allow-Origin: http://localhost:8000
Access-Control-Allow-Methods: GET,OPTIONS
Access-Control-Allow-Headers: Content-Type,X-Lab-Client
Vary: Origin
```

`Access-Control-Allow-Origin` permits the intended frontend origin.

`Access-Control-Allow-Methods` permits the required methods.

`Access-Control-Allow-Headers` permits the custom frontend request header.

`Vary: Origin` helps indicate origin-dependent behavior to HTTP caches. In this lab, the allow-origin value is fixed to one origin.

### Step 3 — Validate Python Syntax

```bash
python3 - <<'PY'
import ast
from pathlib import Path

ast.parse(Path("lambda_function.py").read_text())

print("SUCCESS: Updated Python syntax valid")
PY
```

### Step 4 — Update Deployment Package

```bash
zip -f function.zip lambda_function.py
```

### Step 5 — Update Lambda Function Code

```bash
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file fileb://function.zip \
  --region "$AWS_REGION"
```

### Step 6 — Wait for Lambda Update

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 7 — Verify Lambda Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,UpdateStatus:LastUpdateStatus}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "UpdateStatus": "Successful"
}
```

---

## 22. Remediation — Configure OPTIONS Method

### Step 1 — Create OPTIONS Method

```bash
aws apigateway put-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method OPTIONS \
  --authorization-type NONE \
  --region "$AWS_REGION"
```

### Step 2 — Configure OPTIONS Lambda Integration

```bash
aws apigateway put-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method OPTIONS \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "$INTEGRATION_URI" \
  --region "$AWS_REGION"
```

### Step 3 — Verify OPTIONS Method

```bash
aws apigateway get-method \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method OPTIONS \
  --region "$AWS_REGION"
```

Expected:

```text
httpMethod = OPTIONS

authorizationType = NONE
```

### Step 4 — Verify OPTIONS Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method OPTIONS \
  --query '{Type:type,IntegrationMethod:httpMethod}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "Type": "AWS_PROXY",
  "IntegrationMethod": "POST"
}
```

### Step 5 — Verify Lambda Invocation Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

The invocation permission created earlier covers the configured HTTP methods under the `/orders` resource in the `dev` stage.

### Step 6 — Redeploy REST API

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab05 CORS remediation deployment" \
  --region "$AWS_REGION"
```

### Why Redeployment Is Required

The REST API configuration changed.

We added:

```text
OPTIONS Method
OPTIONS Lambda Integration
```

REST API method and integration changes must be deployed to the stage before they become available through its invoke URL.

The Lambda code update itself does not require API Gateway redeployment.

---

## 23. Verify Successful Recovery

### Step 1 — Test OPTIONS Preflight

```bash
curl -i -X OPTIONS "$API_URL" \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-Lab-Client"
```

Expected:

```http
HTTP/2 204
access-control-allow-origin: http://localhost:8000
access-control-allow-methods: GET,OPTIONS
access-control-allow-headers: Content-Type,X-Lab-Client
```

HTTP header capitalization may vary.

### Step 2 — Save Recovered Preflight Response

```bash
curl -sS \
  -D recovered-preflight-headers.txt \
  -o /dev/null \
  -w 'HTTP Status: %{http_code}\n' \
  -X OPTIONS "$API_URL" \
  -H "Origin: http://localhost:8000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-Lab-Client"
```

Expected:

```text
HTTP Status: 204
```

### Step 3 — Test GET Response

```bash
curl -i "$API_URL" \
  -H "Origin: http://localhost:8000"
```

Expected:

```http
HTTP/2 200
access-control-allow-origin: http://localhost:8000
content-type: application/json
```

### Step 4 — Save Recovered GET Response

```bash
curl -sS \
  -D recovered-get-headers.txt \
  -o recovered-get-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL" \
  -H "Origin: http://localhost:8000"
```

Expected:

```text
HTTP Status: 200
```

### Step 5 — Validate JSON Response

```bash
python3 - <<'PY'
import json

with open("recovered-get-response.json") as file:
    response = json.load(file)

assert response["message"] == "Orders retrieved successfully"
assert len(response["orders"]) == 2

print("SUCCESS: Recovered API response valid")
PY
```

### Step 6 — Verify Browser Request

Start the local server if it is not already running:

```bash
python3 -m http.server 8000
```

Open:

```text
http://localhost:8000
```

Click:

```text
Test API
```

The frontend should now display:

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

### Step 7 — Inspect Browser Network Tab

Expected request sequence:

```text
OPTIONS /dev/orders  -> 204

GET /dev/orders      -> 200
```

The browser should no longer report a CORS error.

### Step 8 — Verify CloudWatch Recovery Logs

From another terminal with your environment variables loaded, or after stopping the local HTTP server:

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected markers:

```text
LAB05_PREFLIGHT_SUCCESS

LAB05_ORDER_SUCCESS
```

### Step 9 — Save Recovery Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab05-recovered-cloudwatch-evidence.json
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| GET method | Working | Working |
| OPTIONS method | Missing | Configured |
| Preflight HTTP response | 403 | 204 |
| GET HTTP response | 200 | 200 |
| Allow-origin header | Missing | Present |
| Allow-methods header | Missing | Present |
| Allow-headers header | Missing | Present |
| Browser request | Blocked | Successful |
| Lambda backend | Healthy | Healthy |
| API deployment | Original | Updated |

**Recovery is confirmed when the browser successfully completes preflight, sends GET, and displays the Lambda response.**

---

## 24. Additional CORS Troubleshooting Scenarios

### Scenario 1 — Incorrect Allowed Origin

Frontend:

```text
https://app.example.com
```

API response:

```http
Access-Control-Allow-Origin: https://admin.example.com
```

The browser rejects the response because the returned origin does not match the requesting origin.

**Remediation:** Configure the correct approved origin.

### Scenario 2 — Missing Allowed Headers

Browser preflight:

```http
Access-Control-Request-Headers: Authorization
```

API response:

```http
Access-Control-Allow-Headers: Content-Type
```

The required Authorization header is not permitted by the preflight response.

**Remediation:** Include the required header when appropriate.

### Scenario 3 — OPTIONS Method Requires Authorization

A preflight request may fail if API Gateway requires authorization for OPTIONS.

**Remediation:** Ensure appropriate unauthenticated preflight handling while keeping authorization enabled for protected application methods.

### Scenario 4 — CORS Headers Missing on Error Responses

A successful API response may include CORS headers, while errors do not.

For example:

```http
HTTP/2 500
```

without an allow-origin header.

The browser may show a CORS error that hides the actual backend failure from frontend JavaScript.

**Remediation:** Return appropriate CORS headers from application error responses and configure API Gateway gateway responses where needed.

### Scenario 5 — Credentials With Wildcard Origin

The following combination is not appropriate for credentialed browser requests:

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

Credentialed cross-origin requests require an appropriate explicit allowed origin and correct credential handling.

### Scenario 6 — Wrong Allowed Method

Preflight requests:

```http
Access-Control-Request-Method: POST
```

Response:

```http
Access-Control-Allow-Methods: GET
```

The browser will reject the requested POST method.

### Troubleshooting Comparison

| Symptom | Possible Cause | Investigation |
|---|---|---|
| OPTIONS returns 403 | Method missing or authorization issue | API Gateway methods |
| GET returns 200 but browser fails | Missing allow-origin header | Response headers |
| Preflight rejects custom header | Header not allowed | Allow-Headers |
| Only POST requests fail | Method not allowed | Allow-Methods |
| Credentialed requests fail | Incorrect credentials CORS policy | Browser and response headers |
| Error responses produce CORS failure | Missing error-response headers | Lambda and Gateway Responses |
| Browser works with curl but not fetch | Browser CORS enforcement | Developer Tools |

---

## 25. Cloud Security Engineering Considerations

### CORS Is Not Authentication

CORS does not prevent non-browser clients from sending requests.

Attackers may still interact with publicly accessible APIs through curl, scripts, or other HTTP clients.

Always enforce authentication and authorization separately.

### Avoid Unnecessary Wildcard Origins

Do not automatically allow every origin for sensitive applications.

Prefer approved origins such as:

```text
https://app.example.com
```

### Protect Credentialed Requests

When APIs use browser credentials, configure CORS carefully.

Credential handling should match the application's session, cookie, or authorization design.

Do not assume that allowing an origin makes a request authenticated.

### Restrict Allowed Methods

Permit only methods required by the application.

Example:

```http
Access-Control-Allow-Methods: GET,OPTIONS
```

Avoid unnecessarily exposing unsupported methods.

### Restrict Allowed Headers

Example:

```http
Access-Control-Allow-Headers: Content-Type,X-Lab-Client
```

For authenticated APIs, additional headers may be required.

### Secure OPTIONS Handling

A preflight OPTIONS request should be processed without application authentication blocking the browser's preflight negotiation.

Actual protected API operations should still enforce authentication and authorization.

### Monitor Configuration Changes

Changes to API Gateway methods and integrations can break frontend access.

Manage production configurations through Terraform, CloudFormation, or reviewed CI/CD pipelines.

### Test CORS in Deployment Pipelines

A production integration test should validate:

```text
OPTIONS response status

Access-Control-Allow-Origin

Access-Control-Allow-Methods

Access-Control-Allow-Headers

Actual GET or POST response headers
```

Also test using a real browser when practical.

### Security Monitoring

Monitor:

```text
API Gateway 4XXError

API Gateway 5XXError

Lambda Errors

Lambda Invocations

API Gateway configuration changes

Application error logs
```

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
| Local Python HTTP Server | No AWS infrastructure charge |

### Cost Optimization

- Use a temporary REST API.
- Keep Lambda memory at 128 MB.
- Limit unnecessary browser requests.
- Use seven-day CloudWatch log retention.
- Delete temporary API resources.
- Avoid unused monitoring resources.

### Infrastructure Not Required

```text
EC2
RDS
NAT Gateway
Load Balancer
VPC Endpoints
```

This lab uses a lightweight serverless architecture.

---

## 27. AWS Resource Cleanup

**Warning:** Delete only resources created for Lab 05. Stop your local Python HTTP server using Ctrl+C before cleanup.

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
Project = API-Gateway-Troubleshooting-Lab05
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
| GET and OPTIONS methods | Deleted |
| Lambda integrations | Deleted |
| Lambda function | Deleted |
| IAM role | Deleted |
| CloudWatch log group | Deleted |
| Local HTTP server | Stopped |
| EC2 | Not created |
| RDS | Not created |
| NAT Gateway | Not created |

---

## 28. Interview Questions and Answers

### Q1. What is CORS?

CORS is a browser security mechanism that allows servers to control which origins can access their resources through cross-origin browser requests.

### Q2. What caused the CORS error in this lab?

The API Gateway REST API did not have an OPTIONS method, and the Lambda response was missing the required CORS headers.

### Q3. Why did curl work while the browser failed?

Curl does not enforce browser CORS restrictions. The browser required successful CORS preflight handling and appropriate response headers.

### Q4. What is a preflight request?

It is an OPTIONS request sent by a browser to determine whether a cross-origin request using particular methods or headers is allowed.

### Q5. Why did our browser send an OPTIONS request?

The frontend included the custom `X-Lab-Client` header, which triggered a CORS preflight.

### Q6. What does `Access-Control-Allow-Origin` do?

It identifies the browser origin permitted to access the response.

### Q7. What does `Access-Control-Allow-Methods` do?

It identifies the HTTP methods allowed for the cross-origin request during preflight negotiation.

### Q8. What does `Access-Control-Allow-Headers` do?

It identifies request headers the browser is allowed to send after preflight.

### Q9. Why did OPTIONS return HTTP 403?

The API Gateway REST API did not have a deployed OPTIONS method for the requested resource.

### Q10. Does CORS replace authentication?

No. CORS controls browser cross-origin access and does not replace authentication or authorization.

### Q11. Why did we update Lambda?

For Lambda proxy integration, the backend response must provide appropriate CORS headers for the actual GET response.

### Q12. Why did we redeploy API Gateway?

We added a new OPTIONS method and integration. REST API configuration changes must be deployed to the stage.

### Q13. Can an API return HTTP 200 while a browser reports a CORS error?

Yes. If the response does not contain acceptable CORS headers, the browser may prevent JavaScript from accessing it.

### Q14. How do you troubleshoot a CORS error in production?

I inspect browser Developer Tools, identify the request origin, check the preflight OPTIONS response, inspect API Gateway methods and integrations, verify the actual response headers, and test the API after remediation.

### Q15. How do you prevent CORS problems?

Configure permitted origins, methods, and headers explicitly. Use Infrastructure as Code and include automated preflight and browser integration tests.

### Q16. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

The API exposed a GET endpoint that returned order information.

I first verified that the endpoint returned HTTP 200 using curl.

Next, I created a simple HTML frontend running on localhost and sent a cross-origin request with a custom header.

The browser performed an OPTIONS preflight request, but API Gateway did not have an OPTIONS method.

As a result, API Gateway returned HTTP 403 for the preflight and the browser blocked the request.

I investigated the REST API resources, methods, Lambda proxy integration, response headers, browser Developer Tools, and CloudWatch Logs.

I identified two configuration problems: missing OPTIONS support and missing CORS response headers.

I updated the Lambda function to return the correct CORS headers for both OPTIONS and GET.

I then configured the OPTIONS method in API Gateway and redeployed the REST API.

After remediation, the OPTIONS request returned HTTP 204 and the GET request returned HTTP 200 with the required headers.

I verified that the frontend could successfully retrieve and display the order data.

Finally, I reviewed the security implications and removed all temporary AWS resources.

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
│   ├── README.md
│   ├── lambda_function.py
│   ├── lambda-trust-policy.json
│   ├── index.html
│   ├── function.zip
│   ├── lab05-resources.env
│   ├── baseline-headers.txt
│   ├── baseline-response.json
│   ├── broken-preflight-headers.txt
│   ├── broken-preflight-body.json
│   ├── broken-get-headers.txt
│   ├── broken-get-response.json
│   ├── recovered-preflight-headers.txt
│   ├── recovered-get-headers.txt
│   ├── recovered-get-response.json
│   ├── lab05-broken-cloudwatch-evidence.json
│   ├── lab05-recovered-cloudwatch-evidence.json
│   ├── lab05-api-4xx-metric.json
│   └── lab05-lambda-invocations-metric.json
│
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
| lambda_function.py | Lambda backend with CORS support |
| lambda-trust-policy.json | IAM execution-role trust policy |
| index.html | Browser CORS testing frontend |
| function.zip | Generated Lambda deployment package |
| lab05-resources.env | Local AWS resource variables |
| baseline-headers.txt | Initial GET headers |
| baseline-response.json | Initial API response |
| broken-preflight-headers.txt | Failed OPTIONS response headers |
| broken-preflight-body.json | Failed preflight response |
| broken-get-headers.txt | GET headers without CORS |
| broken-get-response.json | Backend response before remediation |
| recovered-preflight-headers.txt | Successful OPTIONS headers |
| recovered-get-headers.txt | Successful GET headers |
| recovered-get-response.json | Recovered API response |
| lab05-broken-cloudwatch-evidence.json | Initial Lambda log evidence |
| lab05-recovered-cloudwatch-evidence.json | Successful Lambda processing logs |
| lab05-api-4xx-metric.json | API Gateway 4XX metrics |
| lab05-lambda-invocations-metric.json | Lambda invocation metrics |

### Recommended Public GitHub Files

```text
05-cors-error/
├── README.md
├── lambda_function.py
├── lambda-trust-policy.json
└── index.html
```

The published `lambda_function.py` should be the recovered version containing the CORS configuration.

The local evidence files do not need to be published.

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 05
05-cors-error/function.zip
05-cors-error/lab05-resources.env
05-cors-error/lab05-*.json
05-cors-error/*-headers.txt
05-cors-error/*-response.json
05-cors-error/broken-preflight-body.json

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

Do not publish AWS credentials or unreviewed troubleshooting evidence.

---

## 30. Lessons Learned and Skills Demonstrated

### Lessons Learned

This lab demonstrates how an API Gateway REST API can work correctly through curl while failing in a browser because of CORS restrictions.

We deployed a REST API integrated with a Python Lambda function.

The GET endpoint successfully returned order information.

However, the Lambda response did not include CORS headers, and the API Gateway REST API did not have an OPTIONS method.

We created a simple HTML frontend and sent a cross-origin request using a custom header.

The browser performed a preflight request.

Because OPTIONS was missing, API Gateway returned HTTP 403 and the browser blocked the request.

We investigated API Gateway resources, HTTP methods, Lambda proxy integration, response headers, browser Developer Tools, and CloudWatch Logs.

The investigation identified incomplete CORS configuration as the root cause.

We updated the Lambda backend to return appropriate CORS headers.

We then created an OPTIONS method, configured Lambda proxy integration, and redeployed the REST API.

After remediation, the OPTIONS preflight returned HTTP 204.

The actual GET request returned HTTP 200 with the correct CORS headers.

The frontend could then retrieve and display the order information.

Finally, we reviewed production security practices and cleaned up the temporary AWS resources.

**Key Lesson:** Successful backend execution does not guarantee browser compatibility. CORS problems must be investigated using browser behavior, preflight responses, and response-header analysis.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- CORS troubleshooting
- Same-Origin Policy
- OPTIONS preflight requests
- HTTP 403 investigation
- Lambda proxy integration
- Python 3.13
- API Gateway methods and deployments
- HTTP response headers
- Browser Developer Tools
- JavaScript fetch API
- AWS CLI v2
- Linux Bash
- curl
- CloudWatch Logs
- CloudWatch Metrics
- IAM execution roles
- Lambda resource-based permissions
- Root cause analysis
- API configuration remediation
- Browser integration testing
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-005 |
| Scenario | API Gateway CORS Error |
| REST API | api-lab05-cors-troubleshooting |
| Resource | /orders |
| Actual Method | GET |
| Preflight Method | OPTIONS |
| Stage | dev |
| Lambda | api-lab05-order-handler |
| Frontend | localhost:8000 |
| Broken OPTIONS | HTTP 403 |
| Recovered OPTIONS | HTTP 204 |
| GET Response | HTTP 200 |
| Root Cause | Missing CORS configuration |
| Remediation | Configure OPTIONS and CORS headers |
| Lambda Code Update | Required |
| API Gateway Redeployment | Required |
| Browser Recovery | Successful after verification |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** Production API troubleshooting requires understanding HTTP methods, browser security behavior, API Gateway integrations, Lambda response headers, and accurate root cause analysis.

---

## Official AWS Documentation

- [Amazon API Gateway — CORS for REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
- [Amazon API Gateway — Lambda Proxy Integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [Amazon API Gateway — Enable CORS for a REST API Resource](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors-console.html)
- [Amazon API Gateway — Gateway Responses](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)
- [Amazon API Gateway — CloudWatch Metrics and Dimensions](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [AWS Lambda — Python Handler](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [MDN — Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)