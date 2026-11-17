# Lab 10 — Amazon API Gateway Custom Domain / Certificate Failure

**AWS API Gateway Troubleshooting Labs | Cloud Engineering & Cloud Security Engineering**

## Overview

This lab demonstrates how to investigate and resolve custom domain, DNS, and TLS certificate failures in Amazon API Gateway.

In production, organizations frequently expose APIs using custom domain names rather than the default API Gateway endpoint.

For example, a company might replace:

`https://abc123.execute-api.us-east-1.amazonaws.com/dev/orders`

with:

`https://api.example.com/orders`

A custom domain improves API naming, supports application integrations, and allows organizations to manage their own DNS and TLS configuration.

However, the custom domain introduces additional components that can fail independently of the backend application.

Common failures include:

- Incorrect or missing DNS records.
- ACM certificate validation failures.
- TLS certificate hostname mismatches.
- Expired or incorrect certificates.
- Certificates deployed in the wrong AWS Region.
- Incorrect API Gateway domain configuration.
- Missing or incorrect API base-path mappings.

In this lab, we first create a healthy Amazon API Gateway REST API integrated with a Python AWS Lambda function.

We verify that the default API Gateway endpoint returns HTTP 200.

We then investigate custom-domain failures using two approaches.

**Path A — No Domain Required**

We reproduce a TLS hostname-verification failure using OpenSSL without modifying any public DNS records or purchasing a domain.

This demonstrates how an HTTPS client rejects a certificate that does not cover the expected hostname.

**Path B — Domain Ownership Required**

For users who control a domain, we request an AWS Certificate Manager certificate, complete DNS validation, create an API Gateway Regional custom domain, and map it to the REST API.

We intentionally leave the application DNS record missing, investigate the connection failure, and restore the DNS configuration.

Finally, we verify HTTPS certificate validity, API mapping, backend connectivity, CloudWatch logs, and resource cleanup.

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
Verify Default Endpoint — HTTP 200
           |
           v
Choose Troubleshooting Path
           |
           +---------------------------+
           |                           |
           v                           v
      Path A                      Path B
   No Domain                     Own Domain
           |                           |
           v                           v
Inspect AWS TLS              Request ACM Certificate
Certificate                          |
           |                           v
           v                    Complete DNS Validation
Verify Correct Hostname              |
           |                           v
           v                    Create Regional Domain
Test Wrong Hostname                  |
           |                           v
           v                    Create API Mapping
TLS Verification Failure             |
           |                           v
           v                    Leave App DNS Missing
Identify Hostname Mismatch           |
           |                           v
           |                    DNS Resolution Failure
           |                           |
           |                           v
           |                    Investigate DNS Target
           |                           |
           |                           v
           |                    Create Correct DNS Record
           |                           |
           |                           v
           |                    Verify TLS Certificate
           |                           |
           |                           v
           |                    Verify HTTPS — HTTP 200
           |                           |
           +-------------+-------------+
                         |
                         v
               Root Cause Analysis
                         |
                         v
             Cloud Security Review
                         |
                         v
               Cost Management
                         |
                         v
                Resource Cleanup
```

---

## 1. Lab Information

| Item | Configuration |
|---|---|
| Incident ID | INC-APIGW-010 |
| Lab Name | Custom Domain / Certificate Failure |
| Difficulty | Advanced |
| Primary Service | Amazon API Gateway |
| Supporting Services | ACM, Route 53, Lambda, IAM, CloudWatch |
| Region | `us-east-1` |
| Operating System | WSL2 Ubuntu |
| Tools | AWS CLI v2, Bash, curl, OpenSSL, dig, jq, Python |
| API Type | REST API |
| Endpoint Type | Regional |
| REST API Name | `api-lab10-custom-domain` |
| API Resource | `/orders` |
| HTTP Method | GET |
| Deployment Stage | `dev` |
| Authorization | NONE — temporary lab |
| Integration | AWS_PROXY |
| Lambda Function | `api-lab10-order-handler` |
| Lambda Execution Role | `api-lab10-lambda-role` |
| Lambda Runtime | Python 3.13 |
| Lambda Timeout | 10 seconds |
| Example Custom Domain | `api.yourdomain.com` |
| Certificate Provider | AWS Certificate Manager |
| Certificate Validation | DNS |
| TLS Security Policy | TLS 1.2 |
| API Mapping | Root base-path mapping |
| Path A | TLS hostname mismatch diagnostic |
| Path B | Missing DNS / custom-domain recovery |
| Healthy Response | HTTP 200 |
| Broken Symptoms | DNS or TLS validation failure |
| Root Cause | Incorrect hostname, DNS, or certificate configuration |
| Remediation | Correct certificate, DNS, and mapping |
| Cleanup | API Gateway, Lambda, IAM, CloudWatch, optional ACM/DNS |

### Learning Objectives

- Understand API Gateway custom domains.
- Understand Regional API endpoints.
- Understand HTTPS and TLS.
- Understand TLS certificate hostname validation.
- Understand certificate Subject Alternative Names.
- Understand AWS Certificate Manager.
- Request and validate ACM certificates.
- Understand DNS validation CNAME records.
- Diagnose DNS resolution failures.
- Understand Route 53 alias records.
- Understand API Gateway Regional domain names.
- Configure API base-path mappings.
- Distinguish TLS failures from HTTP errors.
- Diagnose certificate expiration.
- Diagnose certificate Region mismatch.
- Verify certificate validity with OpenSSL.
- Test custom domains with curl.
- Understand DNS-independent endpoint testing.
- Perform production root cause analysis.
- Apply secure TLS configuration.
- Clean up temporary AWS resources.

---

## 2. Production Incident Scenario

### Incident Description

A company operates an order-management application using Amazon API Gateway and AWS Lambda.

The application initially uses the standard API Gateway endpoint:

```text
https://abc123.execute-api.us-east-1.amazonaws.com/dev/orders
```

The company introduces a custom domain:

```text
https://api.example.com/orders
```

The custom domain uses an ACM TLS certificate and DNS records managed by the company.

After a DNS configuration change, customers begin reporting connection failures.

Possible errors include:

```text
curl: (6) Could not resolve host
```

or:

```text
SSL: no alternative certificate subject name matches
```

The development team initially suspects an API Gateway or Lambda problem.

However, the original execute-api endpoint continues returning HTTP 200.

The Cloud Engineering team investigates.

The engineer verifies:

- The REST API exists.
- The `dev` stage is deployed.
- The `/orders` resource works.
- The Lambda integration is healthy.
- The default API Gateway endpoint returns HTTP 200.
- The custom domain has a DNS or certificate problem.
- The failure occurs before the request reaches Lambda.

After correcting the custom-domain configuration, the endpoint returns HTTP 200 over HTTPS.

### Incident Symptoms

- Default API Gateway endpoint works.
- Custom domain is unavailable.
- DNS resolution may fail.
- TLS certificate verification may fail.
- Lambda remains healthy.
- No new Lambda logs appear for DNS/TLS failures.
- The problem is isolated to the custom-domain entry point.

### Business Impact

Custom-domain failures can cause:

- Customer-facing API outages.
- Failed mobile application requests.
- Broken frontend integrations.
- Failed business partner connections.
- Interrupted automated workflows.
- TLS security warnings.
- Increased support tickets.
- Application availability incidents.

### Objective

Determine whether the failure originates from DNS, TLS certificate validation, certificate association, API mapping, or the backend.

Restore secure HTTPS connectivity without disabling certificate verification or modifying healthy backend infrastructure.

---

## 3. AWS Architecture

### Healthy Backend Architecture

```text
             API Client
                 |
                 v
        Default execute-api URL
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
             HTTP 200
```

### Broken DNS Architecture

```text
              API Client
                  |
                  v
       https://api.example.com
                  |
                  v
              DNS Lookup
                  |
                  v
          DNS Record Missing
                  |
                  v
         Name Resolution Fails
                  |
                  v
         HTTPS Connection Fails
                  |
                  v
        Lambda Is Not Invoked
```

### Broken TLS Architecture

```text
              API Client
                  |
                  v
       Requested API Hostname
                  |
                  v
            TLS Handshake
                  |
                  v
          Server Certificate
                  |
                  v
        Compare Hostname to SAN
                  |
                  v
             No Match
                  |
                  v
        Certificate Verification Fails
```

### Recovered Architecture

```text
              API Client
                  |
                  v
        https://api.example.com
                  |
                  v
             Correct DNS
                  |
                  v
       API Gateway Regional Domain
                  |
                  v
         Valid ACM Certificate
                  |
                  v
         TLS Verification Success
                  |
                  v
          API Base-Path Mapping
                  |
                  v
             REST API /dev
                  |
                  v
              GET /orders
                  |
                  v
               AWS Lambda
                  |
                  v
              HTTP 200 OK
```

---

## 4. Understanding API Gateway Custom Domains

An API Gateway custom domain allows clients to use an organization-controlled hostname instead of the default execute-api hostname.

Example default endpoint:

```text
https://abc123.execute-api.us-east-1.amazonaws.com/dev/orders
```

Example custom domain:

```text
https://api.example.com/orders
```

### Main Components

| Component | Purpose |
|---|---|
| Domain Registration | Establishes domain ownership |
| DNS Provider | Resolves hostname |
| ACM Certificate | Provides TLS certificate |
| API Gateway Custom Domain | Configures HTTPS entry point |
| Regional Domain | AWS-managed API Gateway target |
| Base-Path Mapping | Maps custom URL to API stage |
| REST API | Processes API requests |
| Lambda | Handles backend logic |

### Regional vs. Edge-Optimized

| Feature | Regional | Edge-Optimized |
|---|---|---|
| API endpoint | Regional | CloudFront-managed edge |
| Typical certificate Region | Same Region as API | `us-east-1` |
| DNS target | Regional API Gateway domain | CloudFront distribution domain |
| This lab | Yes | No |

This lab uses a Regional REST API and Regional custom domain.

---

## 5. Understanding TLS Certificates

HTTPS uses TLS to protect communication between clients and servers.

During TLS connection establishment, the client validates the server's certificate.

Important certificate properties include:

- Trusted certificate issuer.
- Certificate validity period.
- Subject Alternative Names.
- Requested hostname.
- Certificate chain.
- Supported TLS parameters.

### Certificate Hostname Validation

Suppose the client requests:

```text
api.example.com
```

The certificate must cover that hostname.

A certificate for an unrelated hostname will fail verification.

### Common TLS Errors

| Error | Possible Cause |
|---|---|
| Hostname mismatch | Incorrect certificate or endpoint |
| Certificate expired | Certificate validity period ended |
| Unknown certificate authority | Certificate chain not trusted |
| Certificate not yet valid | Validity period has not started |
| TLS negotiation failure | Unsupported protocol or configuration |
| Could not resolve host | DNS failure, not TLS |

### Security Principle

Never treat disabling certificate verification as the proper remediation for a production TLS failure.

---

## 6. Prerequisites and Safety

### Required Tools

```bash
aws --version
python3 --version
curl --version
openssl version
dig -v
jq --version
```

Install missing packages:

```bash
sudo apt update

sudo apt install -y \
  curl \
  jq \
  zip \
  unzip \
  openssl \
  dnsutils
```

### Relevant AWS Permissions

```text
sts:GetCallerIdentity

iam:CreateRole
iam:AttachRolePolicy
iam:DetachRolePolicy
iam:DeleteRole
iam:PassRole

lambda:CreateFunction
lambda:GetFunction
lambda:AddPermission
lambda:DeleteFunction

apigateway:GET
apigateway:POST
apigateway:DELETE

acm:RequestCertificate
acm:DescribeCertificate
acm:ListCertificates
acm:DeleteCertificate

route53:ListHostedZones
route53:ListResourceRecordSets
route53:ChangeResourceRecordSets

logs:FilterLogEvents
logs:DeleteLogGroup
```

Additional permissions may be required for custom-domain service-linked roles and associated setup operations.

### Safety Rules

- Use a dedicated test API.
- Do not modify unrelated custom domains.
- Do not overwrite production DNS records.
- Only request certificates for domains you control.
- Do not delete shared ACM certificates.
- Do not remove shared validation CNAME records.
- Do not disable TLS verification.
- Verify project resource ownership before cleanup.

---

## 7. Prepare WSL2 Ubuntu

### Step 1 — Create Directory

```bash
cd ~/aws-api-gateway-troubleshooting-labs

mkdir -p 10-custom-domain-certificate-failure

cd 10-custom-domain-certificate-failure
```

### Step 2 — Configure Variables

```bash
export AWS_REGION="us-east-1"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""

export ACCOUNT_ID=$(aws sts get-caller-identity \
  --query Account \
  --output text)

export PROJECT_TAG="API-Gateway-Troubleshooting-Lab10"

export API_NAME="api-lab10-custom-domain"
export FUNCTION_NAME="api-lab10-order-handler"
export ROLE_NAME="api-lab10-lambda-role"

export ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

export STAGE_NAME="dev"
export PERMISSION_SID="AllowAPIGatewayLab10"

export LOG_GROUP="/aws/lambda/${FUNCTION_NAME}"
```

### Step 3 — Configure `.gitignore`

```bash
cat > .gitignore <<'EOF'
function.zip
lab10-resources.env
lab10-*.json
lab10-*.txt
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

### Step 4 — Save Initial Variables

```bash
cat > lab10-resources.env <<EOF
export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"
export ACCOUNT_ID="$ACCOUNT_ID"
export PROJECT_TAG="$PROJECT_TAG"
export API_NAME="$API_NAME"
export FUNCTION_NAME="$FUNCTION_NAME"
export ROLE_NAME="$ROLE_NAME"
export ROLE_ARN="$ROLE_ARN"
export STAGE_NAME="$STAGE_NAME"
export PERMISSION_SID="$PERMISSION_SID"
export LOG_GROUP="$LOG_GROUP"
EOF

chmod 600 lab10-resources.env
```

---

## 8. Create Lambda Execution Role

### Step 1 — Create Trust Policy

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
  --tags "Key=Project,Value=$PROJECT_TAG"
```

### Step 3 — Attach Logging Permissions

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

Expected policy:

```text
AWSLambdaBasicExecutionRole
```

---

## 9. Create Python Lambda Backend

### Step 1 — Create `lambda_function.py`

```bash
cat > lambda_function.py <<'EOF'
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):

    logger.info("LAB10_ORDER_REQUEST")

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

    logger.info("LAB10_ORDER_SUCCESS")

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

### Step 2 — Validate Python

```bash
python3 -m py_compile lambda_function.py
```

### Step 3 — Package Lambda

```bash
zip function.zip lambda_function.py
```

### Step 4 — Verify Package

```bash
unzip -l function.zip
```

Expected package contains `lambda_function.py`.

---

## 10. Deploy Lambda Function

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
  --tags "Project=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

If IAM propagation temporarily prevents Lambda from assuming the new role, retry after the role becomes available.

### Step 2 — Wait for Activation

```bash
aws lambda wait function-active-v2 \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Step 3 — Retrieve ARN

```bash
export FUNCTION_ARN=$(aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --query Configuration.FunctionArn \
  --output text \
  --region "$AWS_REGION")

echo "$FUNCTION_ARN"
```

### Step 4 — Verify

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --query '{State:State,Runtime:Runtime}' \
  --output json \
  --region "$AWS_REGION"
```

Expected:

```json
{
  "State": "Active",
  "Runtime": "python3.13"
}
```

---

## 11. Create API Gateway REST API

### Step 1 — Create API

```bash
export API_ID=$(aws apigateway create-rest-api \
  --name "$API_NAME" \
  --description "Lab10 Custom Domain Certificate Troubleshooting" \
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
```

### Step 4 — Configure GET

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
  --region "$AWS_REGION"
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

### Step 3 — Grant Lambda Invocation Permission

```bash
aws lambda add-permission \
  --function-name "$FUNCTION_NAME" \
  --statement-id "$PERMISSION_SID" \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/${STAGE_NAME}/GET/orders" \
  --region "$AWS_REGION"
```

### Step 4 — Verify Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
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

---

## 13. Deploy REST API

### Step 1 — Create Deployment

```bash
aws apigateway create-deployment \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --description "Lab10 healthy backend deployment" \
  --region "$AWS_REGION"
```

### Step 2 — Generate Endpoint

```bash
export API_HOST="${API_ID}.execute-api.${AWS_REGION}.amazonaws.com"

export API_URL="https://${API_HOST}/${STAGE_NAME}/orders"

echo "$API_URL"
```

### Step 3 — Save Variables

```bash
cat >> lab10-resources.env <<EOF
export FUNCTION_ARN="$FUNCTION_ARN"
export API_ID="$API_ID"
export ROOT_ID="$ROOT_ID"
export RESOURCE_ID="$RESOURCE_ID"
export API_HOST="$API_HOST"
export API_URL="$API_URL"
EOF
```

### Step 4 — Verify Stage

```bash
aws apigateway get-stage \
  --rest-api-id "$API_ID" \
  --stage-name "$STAGE_NAME" \
  --region "$AWS_REGION"
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
```

### Step 2 — Save Evidence

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

### Step 3 — Inspect Response

```bash
jq . baseline-response.json
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

### Step 4 — Verify CloudWatch Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

Expected:

```text
LAB10_ORDER_REQUEST
LAB10_ORDER_SUCCESS
```

### Baseline Findings

| Component | Result |
|---|---|
| REST API | Healthy |
| GET Method | Correct |
| Lambda Integration | Correct |
| Lambda Function | Active |
| Default Endpoint | HTTP 200 |

The backend works independently of custom-domain configuration.

---

## 15. Path A — Inspect Default API TLS Certificate

This path does not require a domain.

### Step 1 — Inspect Certificate Verification

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  -verify_hostname "$API_HOST" \
  -verify_return_error \
  </dev/null
```

Expected successful verification includes:

```text
Verify return code: 0 (ok)
```

### Step 2 — Inspect Certificate Fields

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  </dev/null 2>/dev/null |
openssl x509 \
  -noout \
  -subject \
  -issuer \
  -dates \
  -ext subjectAltName
```

Review:

- Certificate issuer.
- Validity dates.
- Subject Alternative Names.
- Hostname coverage.

### Step 3 — Save Healthy TLS Evidence

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  -verify_hostname "$API_HOST" \
  -verify_return_error \
  </dev/null \
  > lab10-healthy-tls.txt 2>&1
```

This establishes the default endpoint's healthy TLS baseline.

---

## 16. Path A — Fault Injection: TLS Hostname Mismatch

### Step 1 — Verify Against an Incorrect Hostname

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  -verify_hostname "api.example.com" \
  -verify_return_error \
  </dev/null
```

Expected:

```text
verify error:num=62:hostname mismatch
```

The precise error format can vary with OpenSSL version.

### Step 2 — Save Failure Evidence

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  -verify_hostname "api.example.com" \
  -verify_return_error \
  </dev/null \
  > lab10-hostname-mismatch.txt 2>&1
```

### Step 3 — Compare Hostnames

| Setting | Value |
|---|---|
| Actual TLS server | AWS execute-api endpoint |
| Server Name Indication | Actual AWS hostname |
| Verified hostname | `api.example.com` |
| Certificate match | Expected mismatch |
| Failure | Hostname verification |

### Root Cause

The client is verifying the certificate against a hostname that the certificate does not cover.

This is a controlled client-side diagnostic. It does not mean the default AWS endpoint has a broken certificate or that a custom domain was created.

### Path A Remediation

Verify the certificate against the correct actual hostname:

```bash
openssl s_client \
  -connect "${API_HOST}:443" \
  -servername "$API_HOST" \
  -verify_hostname "$API_HOST" \
  -verify_return_error \
  </dev/null
```

Expected:

```text
Verify return code: 0 (ok)
```

---

## 17. Path A — Investigate ACM and API Gateway Domains

### Step 1 — List ACM Certificates

```bash
aws acm list-certificates \
  --certificate-statuses \
    ISSUED \
    PENDING_VALIDATION \
    EXPIRED \
  --region "$AWS_REGION" \
  --output table
```

### Step 2 — List API Gateway Custom Domains

```bash
aws apigateway get-domain-names \
  --region "$AWS_REGION" \
  --query 'items[].{
    Domain:domainName,
    Status:domainNameStatus,
    Certificate:regionalCertificateArn
  }' \
  --output table
```

### Step 3 — Interpret Certificate Status

| Status | Meaning |
|---|---|
| ISSUED | Certificate issued |
| PENDING_VALIDATION | Awaiting domain validation |
| EXPIRED | Certificate expired |
| FAILED | Issuance unsuccessful |
| REVOKED | Certificate revoked |

### Step 4 — Identify Configuration Risks

Common investigation targets:

- Certificate Region.
- Certificate expiration.
- Subject Alternative Names.
- Custom-domain certificate association.
- DNS target.
- API base-path mapping.

These commands are read-only.

Do not modify certificates or custom domains that belong to another application.

---

## 18. Path B — Request ACM Certificate

**Requirement:** You must control the domain or subdomain used in this section.

### Step 1 — Configure Custom Domain

```bash
export CUSTOM_DOMAIN="api.yourdomain.com"
```

Replace the placeholder with a hostname you own.

### Step 2 — Request Certificate

```bash
export CERT_ARN=$(aws acm request-certificate \
  --domain-name "$CUSTOM_DOMAIN" \
  --validation-method DNS \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --query CertificateArn \
  --output text \
  --region "$AWS_REGION")

echo "$CERT_ARN"
```

### Step 3 — Save Variables

```bash
cat >> lab10-resources.env <<EOF
export CUSTOM_DOMAIN="$CUSTOM_DOMAIN"
export CERT_ARN="$CERT_ARN"
EOF
```

### Step 4 — Inspect Certificate

```bash
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --query 'Certificate.{
    Domain:DomainName,
    Status:Status,
    Validation:DomainValidationOptions
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected initial status is commonly:

```text
PENDING_VALIDATION
```

### Important Requirement

For a Regional API Gateway custom domain, the ACM certificate must be available in the same AWS Region as the API Gateway custom domain.

For this lab:

```text
us-east-1
```

---

## 19. Path B — Complete ACM DNS Validation

### Step 1 — Retrieve DNS Validation Record

```bash
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord' \
  --output json \
  --region "$AWS_REGION"
```

Example:

```json
[
  {
    "Name": "_token.api.yourdomain.com.",
    "Type": "CNAME",
    "Value": "_validation.acm-validations.aws."
  }
]
```

The actual values are generated by ACM.

### Step 2 — Create the Validation CNAME

Add the returned CNAME record to the authoritative public DNS zone for your domain.

Do not use the example token values.

### Step 3 — Verify DNS

```bash
dig CNAME "_token.api.yourdomain.com"
```

Replace the example hostname with the actual ACM validation record name.

### Step 4 — Inspect Certificate Status

```bash
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --query 'Certificate.{
    Status:Status,
    Domain:DomainName
  }' \
  --output json \
  --region "$AWS_REGION"
```

Expected after successful validation:

```json
{
  "Status": "ISSUED",
  "Domain": "api.yourdomain.com"
}
```

### Step 5 — Wait for Validation

```bash
aws acm wait certificate-validated \
  --certificate-arn "$CERT_ARN" \
  --region "$AWS_REGION"
```

### Common Validation Problems

| Problem | Possible Cause |
|---|---|
| Pending validation | CNAME missing |
| CNAME not found | Wrong DNS provider or hosted zone |
| Record incorrect | Wrong name or value |
| Validation delayed | DNS propagation |
| Issuance failed | DNS or domain validation problem |

Do not proceed to custom-domain creation until the certificate is successfully issued.

---

## 20. Path B — Create API Gateway Regional Custom Domain

### Step 1 — Create Custom Domain

```bash
aws apigateway create-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --regional-certificate-arn "$CERT_ARN" \
  --endpoint-configuration types=REGIONAL \
  --security-policy TLS_1_2 \
  --routing-mode BASE_PATH_MAPPING_ONLY \
  --tags "Key=Project,Value=$PROJECT_TAG" \
  --region "$AWS_REGION"
```

### Step 2 — Retrieve Regional Endpoint

```bash
export REGIONAL_DOMAIN=$(aws apigateway get-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --query regionalDomainName \
  --output text \
  --region "$AWS_REGION")

echo "$REGIONAL_DOMAIN"
```

Example:

```text
d-xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

### Step 3 — Retrieve Regional Hosted Zone ID

```bash
export REGIONAL_ZONE_ID=$(aws apigateway get-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --query regionalHostedZoneId \
  --output text \
  --region "$AWS_REGION")
```

### Step 4 — Inspect Domain Status

```bash
aws apigateway get-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --query '{
    Domain:domainName,
    Status:domainNameStatus,
    Certificate:regionalCertificateArn,
    RegionalEndpoint:regionalDomainName,
    RoutingMode:routingMode
  }' \
  --output json \
  --region "$AWS_REGION"
```

Wait until the domain is available.

### Step 5 — Save Endpoint Variables

```bash
cat >> lab10-resources.env <<EOF
export REGIONAL_DOMAIN="$REGIONAL_DOMAIN"
export REGIONAL_ZONE_ID="$REGIONAL_ZONE_ID"
EOF
```

---

## 21. Path B — Configure API Base-Path Mapping

### Step 1 — Create Root Mapping

```bash
aws apigateway create-base-path-mapping \
  --domain-name "$CUSTOM_DOMAIN" \
  --rest-api-id "$API_ID" \
  --stage "$STAGE_NAME" \
  --base-path '(none)' \
  --region "$AWS_REGION"
```

### Step 2 — Inspect Mapping

```bash
aws apigateway get-base-path-mappings \
  --domain-name "$CUSTOM_DOMAIN" \
  --region "$AWS_REGION"
```

Expected mapping:

```text
Custom Domain Root
       |
       v
Lab10 REST API
       |
       v
dev Stage
```

### Step 3 — Understand URL Mapping

Default URL:

```text
https://API_ID.execute-api.us-east-1.amazonaws.com/dev/orders
```

Custom URL:

```text
https://api.yourdomain.com/orders
```

The root base-path mapping selects the `dev` stage, so `/dev` does not need to appear in the custom-domain URL.

### Important Distinction

A valid TLS certificate does not guarantee correct API routing.

If the base-path mapping is incorrect, HTTPS may succeed but the API can still return an HTTP routing error.

---

## 22. Path B — Fault Injection: Missing Application DNS

At this stage, the custom domain and API mapping exist, but we intentionally have not created the application DNS record.

### Step 1 — Check DNS

```bash
dig "$CUSTOM_DOMAIN"
```

If no existing DNS record resolves the hostname, the application domain will not resolve to the API Gateway endpoint.

### Step 2 — Attempt HTTPS Request

```bash
curl -i "https://${CUSTOM_DOMAIN}/orders"
```

Possible result:

```text
curl: (6) Could not resolve host
```

This failure depends on the hostname having no usable existing DNS record.

If the name already points to another application, do not overwrite or remove that existing record.

### Step 3 — Inspect Regional Target

```bash
echo "$REGIONAL_DOMAIN"
```

### Step 4 — Bypass Public DNS for Diagnosis

```bash
curl -i \
  --connect-to "${CUSTOM_DOMAIN}:443:${REGIONAL_DOMAIN}:443" \
  "https://${CUSTOM_DOMAIN}/orders"
```

This targets the Regional API Gateway hostname while preserving the custom hostname for TLS and HTTP routing.

When the certificate and API mapping are ready, this can return:

```http
HTTP/2 200
```

### Investigation Finding

If the DNS-independent request succeeds but the normal custom-domain URL fails to resolve, that strongly indicates a DNS problem rather than a Lambda integration problem.

---

## 23. Path B — Remediation: Restore DNS

### Step 1 — Identify Public Hosted Zone

If using Route 53:

```bash
aws route53 list-hosted-zones \
  --query 'HostedZones[].{
    Id:Id,
    Name:Name,
    Private:Config.PrivateZone
  }' \
  --output table
```

Set the appropriate hosted zone ID:

```bash
export HOSTED_ZONE_ID="YOUR_PUBLIC_HOSTED_ZONE_ID"
```

### Step 2 — Check Existing DNS Records

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='${CUSTOM_DOMAIN}.']" \
  --output json
```

Do not proceed if the hostname already contains unrelated production records.

### Step 3 — Generate Route 53 Alias Change

```bash
jq -n \
  --arg name "$CUSTOM_DOMAIN" \
  --arg target "$REGIONAL_DOMAIN" \
  --arg zone "$REGIONAL_ZONE_ID" \
  '{
    Changes: [
      {
        Action: "CREATE",
        ResourceRecordSet: {
          Name: $name,
          Type: "A",
          AliasTarget: {
            HostedZoneId: $zone,
            DNSName: $target,
            EvaluateTargetHealth: false
          }
        }
      }
    ]
  }' > lab10-dns-create.json
```

### Step 4 — Apply DNS Record

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file://lab10-dns-create.json
```

### Alternative DNS Provider

If your DNS is not hosted in Route 53, create a CNAME record for the controlled subdomain:

| Setting | Value |
|---|---|
| Record | `api.yourdomain.com` |
| Type | CNAME |
| Target | API Gateway Regional domain |

### Step 5 — Verify Resolution

```bash
dig +short "$CUSTOM_DOMAIN"
```

### Step 6 — Test HTTPS

```bash
curl -i "https://${CUSTOM_DOMAIN}/orders"
```

Expected after DNS propagation and successful setup:

```http
HTTP/2 200
```

---

## 24. Verify Successful Recovery

### Step 1 — Verify TLS Certificate

```bash
openssl s_client \
  -connect "${CUSTOM_DOMAIN}:443" \
  -servername "$CUSTOM_DOMAIN" \
  -verify_hostname "$CUSTOM_DOMAIN" \
  -verify_return_error \
  </dev/null
```

Expected:

```text
Verify return code: 0 (ok)
```

### Step 2 — Inspect Certificate Details

```bash
openssl s_client \
  -connect "${CUSTOM_DOMAIN}:443" \
  -servername "$CUSTOM_DOMAIN" \
  </dev/null 2>/dev/null |
openssl x509 \
  -noout \
  -subject \
  -issuer \
  -dates \
  -ext subjectAltName
```

### Step 3 — Verify ACM Certificate

```bash
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --query 'Certificate.{
    Domain:DomainName,
    Status:Status,
    NotAfter:NotAfter,
    InUseBy:InUseBy
  }' \
  --output json \
  --region "$AWS_REGION"
```

### Step 4 — Save Recovered HTTP Response

```bash
curl -sS \
  -D recovered-headers.txt \
  -o recovered-response.json \
  -w 'HTTP Status: %{http_code}\n' \
  "https://${CUSTOM_DOMAIN}/orders"
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

print("SUCCESS: Custom domain API recovered")
PY
```

### Recovery Comparison

| Component | Broken | Recovered |
|---|---|---|
| Default API Endpoint | HTTP 200 | HTTP 200 |
| Custom Domain DNS | Missing / incorrect | Correct |
| ACM Certificate | Must be valid | ISSUED |
| TLS Hostname | May mismatch | Matches |
| API Mapping | Investigated | Correct |
| Custom HTTPS | Failed | Successful |
| Lambda Backend | Healthy | Healthy |
| Custom API Response | Connection/TLS failure | HTTP 200 |

---

## 25. Investigate CloudWatch and API Configuration

### Step 1 — Inspect Lambda Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 30m \
  --region "$AWS_REGION"
```

Successful requests may show:

```text
LAB10_ORDER_REQUEST

LAB10_ORDER_SUCCESS
```

### Step 2 — Save Lambda Evidence

```bash
aws logs filter-log-events \
  --log-group-name "$LOG_GROUP" \
  --output json \
  --region "$AWS_REGION" \
  > lab10-cloudwatch-evidence.json
```

### Step 3 — Inspect API Mapping

For Path B:

```bash
aws apigateway get-base-path-mappings \
  --domain-name "$CUSTOM_DOMAIN" \
  --region "$AWS_REGION"
```

### Step 4 — Inspect Regional Domain

```bash
aws apigateway get-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --region "$AWS_REGION"
```

### Important Observation

DNS and TLS failures generally occur before the API request reaches Lambda.

Therefore, a failed HTTPS connection may produce no corresponding Lambda application log.

A healthy Lambda function does not guarantee that the custom hostname is reachable.

---

## 26. Root Cause Analysis

### Path A Root Cause

The TLS certificate was checked against a hostname it did not cover.

This produced a controlled hostname-verification failure.

The default API endpoint and AWS certificate remained healthy.

### Path B Root Cause

The custom domain did not have the required application DNS record pointing to API Gateway's Regional endpoint.

The API mapping and backend could be healthy, but public clients could not resolve the expected API destination.

### Root Cause Diagram

```text
Custom Domain Request
        |
        v
DNS Resolution
        |
        +---------------------+
        |                     |
        v                     v
Missing Record         Valid DNS Target
        |                     |
        v                     v
DNS Failure            TLS Handshake
                              |
                              v
                      Certificate Check
                              |
                       +------+------+
                       |             |
                       v             v
                  Mismatch         Valid
                       |             |
                       v             v
                  TLS Failure    API Mapping
                                     |
                                     v
                                 REST API
                                     |
                                     v
                                  Lambda
                                     |
                                     v
                                 HTTP 200
```

### Five Whys — Missing DNS Incident

**Why 1 — Why was the custom API unavailable?**

Clients could not resolve the custom hostname to the intended API Gateway endpoint.

**Why 2 — Why did DNS resolution fail?**

The application DNS record was missing.

**Why 3 — Why was the record missing?**

The custom-domain deployment was incomplete.

**Why 4 — Why was the incomplete configuration not detected?**

A post-deployment custom-domain connectivity test was not performed.

**Why 5 — How can this incident be prevented?**

Manage DNS, certificates, custom domains, and API mappings with Infrastructure as Code and automated deployment verification.

### Root Cause Summary

| Item | Finding |
|---|---|
| Incident | INC-APIGW-010 |
| Primary Failure Area | Custom-domain connectivity |
| Backend State | Healthy |
| Path A Fault | TLS hostname mismatch |
| Path B Fault | Missing application DNS record |
| Certificate Requirement | Valid hostname and trusted chain |
| API Mapping Requirement | Correct REST API and stage |
| Primary Remediation | Correct DNS or certificate configuration |
| Expected Recovery | HTTPS HTTP 200 |

---

## 27. Cloud Security Engineering Considerations

### Protect TLS Verification

Never use `curl -k` as a production fix.

Disabling certificate verification removes an important security check and can expose clients to impersonation risks.

### Certificate Ownership

Request certificates only for domains you control.

ACM DNS validation demonstrates control of the domain.

### Certificate Region

Regional API Gateway custom domains require certificates in the relevant AWS Region.

### Certificate Expiration

Monitor expiration and renewal status.

Use approved monitoring and alerting processes so certificate problems are identified before they affect applications.

### DNS Security

Protect access to DNS management systems.

Unauthorized DNS changes can redirect clients to unintended infrastructure.

### Least Privilege

Restrict IAM permissions for:

- ACM certificate management.
- API Gateway domain management.
- API mappings.
- Route 53 record changes.
- Lambda integration configuration.

### Change Management

Review certificate, DNS, and API mapping changes through approved deployment workflows.

### Infrastructure as Code

Relevant resources include:

```text
AWS::CertificateManager::Certificate

AWS::ApiGateway::DomainName

AWS::ApiGateway::BasePathMapping

AWS::Route53::RecordSet

AWS::ApiGateway::RestApi

AWS::ApiGateway::Deployment

AWS::ApiGateway::Stage
```

### Security Principle

**A secure API requires both a healthy backend and a correctly configured DNS/TLS entry point.**

---

## 28. Cost Management and Cleanup

### Potential AWS Charges

| Service | Cost Consideration |
|---|---|
| API Gateway REST API | Requests |
| API Gateway Custom Domain | Applicable custom-domain charges |
| ACM | Charges depend on certificate type and use |
| Route 53 | Hosted zone and DNS charges |
| Domain Registrar | Domain registration or renewal |
| Lambda | Invocations and execution |
| CloudWatch | Logs and applicable metrics |

### Path A Cleanup

Path A does not create an ACM certificate, custom domain, or DNS record.

Delete only the REST API, Lambda function, IAM role, and CloudWatch log group created for this lab.

### Path B — Delete Base-Path Mapping

```bash
aws apigateway delete-base-path-mapping \
  --domain-name "$CUSTOM_DOMAIN" \
  --base-path '(none)' \
  --region "$AWS_REGION"
```

### Path B — Delete Custom Domain

```bash
aws apigateway delete-domain-name \
  --domain-name "$CUSTOM_DOMAIN" \
  --region "$AWS_REGION"
```

### Path B — Remove Lab DNS Alias

If you created the Route 53 alias using `lab10-dns-create.json`, generate its deletion request:

```bash
jq '.Changes[0].Action = "DELETE"' \
  lab10-dns-create.json \
  > lab10-dns-delete.json
```

After verifying that the record still matches the exact lab-created record:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file://lab10-dns-delete.json
```

If you used another DNS provider, remove only the record created for this lab.

Do not delete pre-existing domain records.

### Path B — Delete ACM Certificate

Delete the certificate only if it was created exclusively for this lab and is no longer in use:

```bash
aws acm delete-certificate \
  --certificate-arn "$CERT_ARN" \
  --region "$AWS_REGION"
```

Preserve shared certificate validation CNAME records when they are needed for other certificates or renewals.

### Delete REST API

```bash
aws apigateway delete-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

### Delete Lambda

```bash
aws lambda delete-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Delete IAM Role

```bash
aws iam detach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam delete-role \
  --role-name "$ROLE_NAME"
```

### Delete CloudWatch Logs

```bash
aws logs delete-log-group \
  --log-group-name "$LOG_GROUP" \
  --region "$AWS_REGION"
```

If the log group does not exist, AWS may return `ResourceNotFoundException`.

### Cleanup Verification

```bash
aws apigateway get-rest-api \
  --rest-api-id "$API_ID" \
  --region "$AWS_REGION"
```

Expected: `NotFoundException`.

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

Expected: `ResourceNotFoundException`.

```bash
aws iam get-role \
  --role-name "$ROLE_NAME"
```

Expected: `NoSuchEntity`.

---

## 29. Interview Questions and Answers

### Q1. What is an API Gateway custom domain?

A custom domain allows clients to access API Gateway using an organization-controlled hostname.

### Q2. Why might the default API Gateway endpoint work while the custom domain fails?

Because DNS, TLS certificate validation, and API mappings are additional components that can fail independently.

### Q3. What is AWS Certificate Manager?

ACM manages TLS certificates for supported AWS services.

### Q4. Why is DNS validation required?

DNS validation allows ACM to verify that the certificate requester controls the domain.

### Q5. What is a certificate hostname mismatch?

It occurs when the certificate does not cover the hostname the client is verifying.

### Q6. What are Subject Alternative Names?

They identify DNS names or other identities covered by a certificate.

### Q7. Where must the ACM certificate be located for a Regional custom domain?

In the same AWS Region as the Regional API Gateway custom domain.

### Q8. What is a Regional API Gateway domain name?

It is an AWS-managed endpoint that receives traffic for a Regional API Gateway custom domain.

### Q9. What is an API base-path mapping?

It connects a custom-domain URL path to a REST API and deployment stage.

### Q10. Why does `/dev` disappear from the custom-domain URL?

Because a root base-path mapping can direct the custom domain to the `dev` stage automatically.

### Q11. How do you investigate DNS resolution?

Use `dig` to inspect the hostname's DNS records and compare them with the expected API Gateway target.

### Q12. How do you inspect the presented TLS certificate?

Use `openssl s_client` with the appropriate server hostname and verification options.

### Q13. Should you use `curl -k` to fix certificate problems?

No. It disables certificate verification and hides the trust or hostname problem.

### Q14. Why might Lambda have no logs during a custom-domain incident?

DNS or TLS failures can prevent requests from reaching API Gateway and Lambda.

### Q15. What is the difference between a TLS failure and HTTP 403?

A TLS failure can prevent the HTTPS connection from being established. HTTP 403 is a response returned after an HTTP request has been processed sufficiently to generate that status.

### Q16. How can you test a custom domain before public DNS is ready?

Use curl's `--connect-to` option to connect to the API Gateway Regional endpoint while preserving the intended custom hostname.

### Q17. How do you prevent certificate-related outages?

Monitor certificate validity, use ACM-managed renewal where applicable, validate DNS records, and verify the custom domain after infrastructure changes.

### Q18. How would you explain this lab in an interview?

I deployed an Amazon API Gateway REST API integrated with a Python Lambda backend.

I first verified that the default API Gateway endpoint returned HTTP 200.

Then I investigated how a custom domain introduces additional DNS, certificate, and API mapping dependencies.

For the no-domain troubleshooting path, I used OpenSSL to inspect the AWS endpoint certificate and intentionally verified it against an unrelated hostname.

The TLS hostname verification failed, demonstrating how clients reject certificates that do not cover the requested hostname.

For the domain-owned workflow, I documented requesting and validating an ACM certificate, configuring a Regional API Gateway custom domain, and mapping it to the REST API stage.

I then investigated a missing application DNS record.

I used DNS diagnostics and curl's `--connect-to` option to distinguish DNS problems from API Gateway backend problems.

The remediation involved configuring DNS correctly and verifying HTTPS certificate validity, API mapping, and HTTP 200 responses.

Finally, I reviewed certificate security, IAM least privilege, DNS protection, and resource cleanup.

---

## 30. Repository Structure, Lessons Learned, and Final Outcome

### Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-api-returns-403/
├── 02-api-returns-404/
├── 03-api-returns-500/
├── 04-api-gateway-lambda-integration-failure/
├── 05-cors-error/
├── 06-missing-authorization-token/
├── 07-api-key-usage-plan-misconfiguration/
├── 08-api-throttling-429/
├── 09-api-timeout-504/
│
└── 10-custom-domain-certificate-failure/
    ├── README.md
    ├── .gitignore
    ├── lambda_function.py
    ├── lambda-trust-policy.json
    ├── function.zip
    ├── lab10-resources.env
    ├── baseline-headers.txt
    ├── baseline-response.json
    ├── lab10-healthy-tls.txt
    ├── lab10-hostname-mismatch.txt
    ├── lab10-dns-create.json
    ├── lab10-dns-delete.json
    ├── recovered-headers.txt
    ├── recovered-response.json
    └── lab10-cloudwatch-evidence.json
```

Some files are generated only when the optional real-domain path is completed.

### Recommended Public GitHub Structure

```text
10-custom-domain-certificate-failure/
├── README.md
├── .gitignore
├── lambda_function.py
└── lambda-trust-policy.json
```

### Recommended Root `.gitignore`

```gitignore
# API Gateway Lab 10
10-custom-domain-certificate-failure/function.zip
10-custom-domain-certificate-failure/lab10-resources.env
10-custom-domain-certificate-failure/lab10-*.json
10-custom-domain-certificate-failure/lab10-*.txt
10-custom-domain-certificate-failure/*-headers.txt
10-custom-domain-certificate-failure/*-response.json

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

### Lessons Learned

This lab demonstrates how an API Gateway custom domain can fail even when the underlying REST API and Lambda backend are healthy.

We deployed a REST API and verified that the default execute-api endpoint returned HTTP 200.

We investigated TLS certificate hostname validation using OpenSSL and reproduced a controlled hostname mismatch.

We also documented a real custom-domain workflow using ACM, API Gateway, and DNS.

The domain-owned workflow demonstrates how a missing application DNS record can prevent clients from accessing an otherwise healthy API.

We used DNS diagnostics, OpenSSL, AWS CLI, and curl to identify which component was responsible.

The remediation focused on correcting the DNS or certificate configuration rather than changing healthy Lambda code.

### Skills Demonstrated

- Amazon API Gateway REST APIs
- Regional custom domains
- AWS Certificate Manager
- TLS and HTTPS troubleshooting
- Certificate hostname verification
- Subject Alternative Names
- DNS CNAME records
- Route 53 alias records
- API base-path mappings
- OpenSSL diagnostics
- curl connection troubleshooting
- AWS CLI v2
- Linux Bash
- Lambda proxy integration
- IAM execution roles
- CloudWatch Logs
- Root cause analysis
- TLS security
- DNS security
- Cloud Security Engineering
- AWS resource cleanup

### Final Outcome

| Item | Expected Result |
|---|---|
| Incident | INC-APIGW-010 |
| Scenario | Custom Domain / Certificate Failure |
| REST API | api-lab10-custom-domain |
| Resource | /orders |
| Method | GET |
| Stage | dev |
| Lambda | api-lab10-order-handler |
| Default Endpoint | HTTP 200 |
| Path A Failure | TLS hostname mismatch |
| Path A Recovery | Correct hostname verification |
| Path B Failure | Missing application DNS |
| Path B Recovery | Correct DNS and HTTPS |
| ACM Certificate | ISSUED for Path B |
| API Mapping | Correct for Path B |
| Custom HTTPS | HTTP 200 after successful Path B recovery |
| Cleanup | Temporary AWS resources removed |
| Incident Status | Resolved upon successful verification |

**Key Takeaway:** A healthy API backend does not guarantee a healthy custom-domain endpoint. Production troubleshooting must examine DNS resolution, certificate validity, TLS hostname verification, API Gateway custom-domain configuration, and API mappings separately.

---

## Official AWS Documentation

- [Set Up a Regional Custom Domain in API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-regional-api-custom-domain-create.html)
- [Custom Domain Names for REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html)
- [API Gateway Base-Path Mappings](https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mappings.html)
- [AWS Certificate Manager DNS Validation](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html)
- [Troubleshoot ACM DNS Validation](https://docs.aws.amazon.com/acm/latest/userguide/troubleshooting-DNS-validation.html)
- [AWS CLI — Create Domain Name](https://docs.aws.amazon.com/cli/latest/reference/apigateway/create-domain-name.html)
- [AWS CLI — Get Domain Name](https://docs.aws.amazon.com/cli/latest/reference/apigateway/get-domain-name.html)
- [AWS CLI — Create Base-Path Mapping](https://docs.aws.amazon.com/cli/latest/reference/apigateway/create-base-path-mapping.html)
- [Amazon Route 53 Documentation](https://docs.aws.amazon.com/route53/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)