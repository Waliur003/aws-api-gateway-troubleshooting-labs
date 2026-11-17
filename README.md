# AWS API Gateway Troubleshooting Labs

**Production-Style AWS API Gateway Troubleshooting Using AWS CLI, Linux, Lambda, and CloudWatch**

## Overview

This repository contains 10 hands-on troubleshooting labs focused on Amazon API Gateway and real-world production API failures.

The purpose of this repository is to develop practical Cloud Engineering, DevOps Engineering, and Cloud Security Engineering skills by investigating common failures involving API endpoints, HTTP methods, authorization, backend integrations, CORS, throttling, timeouts, and custom domains.

Amazon API Gateway is a managed AWS service used to create, publish, secure, monitor, and manage APIs.

In production, API Gateway frequently acts as an entry point for applications that communicate with AWS Lambda and other backend services.

When an API experiences errors, engineers must determine whether the problem originates from API Gateway configuration, client requests, IAM permissions, authentication, Lambda integration, backend application code, or networking.

These labs demonstrate how to reproduce failures safely, collect diagnostic evidence, identify root causes, apply targeted remediation, verify recovery, and remove temporary AWS resources.

The exercises primarily use API Gateway REST APIs, AWS Lambda, AWS CLI, Linux Bash, and Amazon CloudWatch.

The repository is designed around practical troubleshooting rather than deploying a fully working API without explaining how failures occur.

---

## 1. Repository Objectives

The main objectives are to:

- Understand Amazon API Gateway architecture.
- Troubleshoot common HTTP error responses.
- Diagnose API Gateway REST API routing problems.
- Investigate API authentication and authorization failures.
- Understand API Gateway resource policies.
- Troubleshoot Lambda proxy integrations.
- Investigate backend application errors.
- Diagnose CORS configuration problems.
- Understand API keys and usage plans.
- Troubleshoot API throttling and quotas.
- Investigate API integration timeouts.
- Understand custom domains and TLS certificates.
- Use AWS CLI for API inspection and troubleshooting.
- Analyze CloudWatch execution and access logs.
- Practice AWS security best practices.
- Perform production-style root cause analysis.
- Verify successful remediation.
- Clean up temporary AWS resources.

---

## 2. Technologies and Tools

| Technology | Purpose |
|---|---|
| Amazon API Gateway | Create and manage REST API endpoints |
| AWS Lambda | Backend application processing |
| AWS IAM | Access control and authorization |
| Amazon CloudWatch Logs | API execution and application troubleshooting |
| Amazon CloudWatch Metrics | API error, latency, and throttling analysis |
| AWS Certificate Manager | TLS certificate management |
| Amazon Route 53 | DNS configuration for custom domains when required |
| AWS CLI v2 | Provisioning, inspection, and remediation |
| Linux Bash | Command-line operations and automation |
| Python 3 | Lambda application and test scripts |
| curl | HTTP request testing |
| jq | JSON response inspection |
| OpenSSL | TLS and certificate troubleshooting |
| Git | Version control |
| GitHub | Lab documentation and portfolio |

### Operating Environment

```text
Operating System: WSL2 Ubuntu
AWS CLI: Version 2
AWS Region: us-east-1
Shell: Bash
Primary API Type: REST API
Backend Runtime: Python 3.13
HTTP Testing: curl
```

---

## 3. Understanding API Gateway Architecture

### Standard API Gateway–Lambda Architecture

```text
                   API Client
                       |
                       v
                 HTTPS Request
                       |
                       v
                Amazon API Gateway
                       |
              +--------+---------+
              |                  |
              v                  v
          API Routes         Authorization
              |                  |
              +--------+---------+
                       |
                       v
                API Integration
                       |
                       v
                   AWS Lambda
                       |
                       v
                Python Handler
                       |
                       v
                Business Logic
                       |
                       v
                  HTTP Response
                       |
                       v
                Amazon API Gateway
                       |
                       v
                    API Client
```

### Production Observability

```text
                    API Client
                        |
                        v
                  API Gateway
                        |
              +---------+---------+
              |                   |
              v                   v
          AWS Lambda         CloudWatch Logs
              |                   |
              v                   v
       Application Logs     API Access Logs
              |
              v
       CloudWatch Metrics
              |
              v
       Engineer Investigation
```

### Main Components

**API Client:** A web application, mobile application, service, or command-line tool sending HTTP requests.

**API Gateway:** The managed service receiving requests, evaluating API configuration, and forwarding authorized requests to integrations.

**API Resource:** The URL path associated with a REST API.

**HTTP Method:** The operation such as GET, POST, PUT, or DELETE.

**API Stage:** A deployed API environment, such as `dev`, `test`, or `prod`.

**Integration:** The connection between API Gateway and a backend.

**Lambda Backend:** A function processing API events and returning responses.

**Authorizer:** A component that evaluates authentication or authorization before a request reaches the backend.

**CloudWatch:** The monitoring and logging service used to investigate errors and latency.

---

## 4. Troubleshooting Labs

| Lab | Troubleshooting Scenario | Primary Focus |
|---|---|---|
| 01 | API Returns 403 | Access denied and authorization |
| 02 | API Returns 404 | Incorrect route or resource |
| 03 | API Returns 500 | Internal server or integration error |
| 04 | API Gateway–Lambda Integration Failure | Integration configuration and Lambda permissions |
| 05 | CORS Error | Browser cross-origin request handling |
| 06 | Missing Authorization Token | Incorrect endpoint, stage, resource, or HTTP method |
| 07 | API Key / Usage Plan Misconfiguration | API key validation and usage plans |
| 08 | API Throttling — 429 | Request-rate and burst limits |
| 09 | API Timeout — 504 | Backend latency and integration timeout |
| 10 | Custom Domain / Certificate Failure | DNS, ACM, TLS, and domain configuration |

### Lab 01 — API Returns 403

**Scenario:** An API client receives `403 Forbidden` when attempting to access a protected API.

**Investigation focus:**

- REST API endpoint configuration.
- Authorization type.
- IAM authorization.
- API Gateway resource policies.
- Access-denied gateway responses.
- CloudWatch access logs.

**Expected remediation:** Identify and correct the specific authorization or access policy misconfiguration.

**Directory:** `01-api-returns-403/`

### Lab 02 — API Returns 404

**Scenario:** An API request returns HTTP 404 because the requested resource or route cannot be found.

**Investigation focus:**

- API resource paths.
- HTTP methods.
- API deployments.
- Stage configuration.
- Incorrect route mappings.
- Backend-generated 404 responses.

**Expected remediation:** Correct the missing or mismatched resource, route, stage, or backend mapping.

**Directory:** `02-api-returns-404/`

### Lab 03 — API Returns 500

**Scenario:** API Gateway returns an internal server error while processing an API request.

**Investigation focus:**

- CloudWatch execution logs.
- Gateway-generated error responses.
- Backend exceptions.
- Integration configuration.
- Lambda response formats.
- Difference between HTTP 500 and HTTP 502.

**Expected remediation:** Identify whether the error originates in API Gateway or its backend and correct the cause.

**Directory:** `03-api-returns-500/`

### Lab 04 — API Gateway–Lambda Integration Failure

**Scenario:** API Gateway cannot successfully invoke or communicate with the configured Lambda backend.

**Investigation focus:**

- Lambda function ARN.
- Integration URI.
- Lambda resource-based permissions.
- AWS service principal authorization.
- Lambda proxy integration.
- Function configuration.
- CloudWatch diagnostics.

**Expected remediation:** Correct the integration or invocation permission and verify that API Gateway receives a valid backend response.

**Directory:** `04-api-gateway-lambda-integration-failure/`

### Lab 05 — CORS Error

**Scenario:** A browser application cannot access an API because of incorrect Cross-Origin Resource Sharing configuration.

**Investigation focus:**

- Origin headers.
- OPTIONS preflight requests.
- Access-Control-Allow-Origin.
- Access-Control-Allow-Methods.
- Access-Control-Allow-Headers.
- Lambda proxy response headers.
- Browser behavior compared with curl.

**Expected remediation:** Configure the required CORS headers and preflight behavior for the intended application origin.

**Directory:** `05-cors-error/`

### Lab 06 — Missing Authorization Token

**Scenario:** An API client receives a response containing:

```json
{
  "message": "Missing Authentication Token"
}
```

**Investigation focus:**

- Incorrect API endpoint.
- Missing stage name.
- Unsupported HTTP method.
- Incorrect resource path.
- Deployment configuration.
- Authentication requirements.

**Expected remediation:** Correct the request URL, method, deployment, or actual authorization configuration.

**Important:** Despite its wording, this error does not always mean that a JWT or authorization header is missing. For REST APIs, it can also occur when the requested resource or method does not exist.

**Directory:** `06-missing-authorization-token/`

### Lab 07 — API Key / Usage Plan Misconfiguration

**Scenario:** API clients cannot access methods requiring API keys because of missing or incorrect usage plan configuration.

**Investigation focus:**

- API key existence and status.
- `x-api-key` request header.
- API key requirement settings.
- Usage plan association.
- API stage association.
- Request quotas and throttling.
- 403 responses involving invalid API keys.

**Expected remediation:** Correct the API key, method configuration, and usage plan association.

**Security note:** API keys are not a replacement for authentication and authorization.

**Directory:** `07-api-key-usage-plan-misconfiguration/`

### Lab 08 — API Throttling — 429

**Scenario:** API clients experience `429 Too Many Requests` during bursts of traffic.

**Investigation focus:**

- API Gateway throttling.
- Request rate limits.
- Burst limits.
- Usage plan throttling.
- Stage-level throttling.
- CloudWatch 4XX metrics.
- Controlled load testing.

**Expected remediation:** Identify the specific throttling configuration and adjust capacity or client behavior appropriately.

**Directory:** `08-api-throttling-429/`

### Lab 09 — API Timeout — 504

**Scenario:** API Gateway returns a gateway timeout while waiting for a backend integration to respond.

**Investigation focus:**

- Lambda execution duration.
- API Gateway integration timeout.
- IntegrationLatency.
- Backend performance.
- CloudWatch execution logs.
- Difference between Lambda timeout and API Gateway timeout.

**Expected remediation:** Correct the timeout or backend performance issue and verify successful API responses.

**Directory:** `09-api-timeout-504/`

### Lab 10 — Custom Domain / Certificate Failure

**Scenario:** A custom API domain does not work because of an incorrect TLS certificate, DNS record, domain mapping, or related configuration.

**Investigation focus:**

- AWS Certificate Manager.
- Certificate validation.
- API Gateway custom domain settings.
- DNS resolution.
- Route 53.
- TLS certificate hostname matching.
- Certificate expiration.
- API mappings and stages.
- OpenSSL and curl diagnostics.

**Expected remediation:** Correct the certificate, DNS, or API mapping configuration and verify secure HTTPS connectivity.

**Directory:** `10-custom-domain-certificate-failure/`

---

## 5. HTTP Status Codes in API Gateway

| Status | Meaning | Common Investigation |
|---|---|---|
| 200 | Successful request | Application response |
| 201 | Resource created | Backend behavior |
| 400 | Bad request | Validation and request format |
| 401 | Unauthorized | Authentication |
| 403 | Forbidden | IAM, resource policies, API keys, WAF |
| 404 | Not found | Resource, route, or backend |
| 429 | Too many requests | Throttling or quota |
| 500 | Internal server error | API processing or integration |
| 502 | Bad gateway | Invalid or failed backend integration |
| 503 | Service unavailable | Service or backend availability |
| 504 | Gateway timeout | Integration timeout |

The actual status code depends on the API type, integration, response mappings, authorization configuration, and failure source.

### Troubleshooting Principle

A status code alone does not establish the root cause.

For example, `403 Forbidden` can result from more than one authorization mechanism.

Similarly, a client-visible `500` may originate from a different component than a backend-generated application response.

Production troubleshooting requires checking the actual response, logs, configuration, and request path.

---

## 6. Standard Production Troubleshooting Workflow

Every lab follows an incident investigation process.

### Step 1 — Identify the Incident

Record the API endpoint, HTTP method, response status, and observed behavior.

### Step 2 — Verify the Environment

Confirm AWS account, Region, API ID, stage, and target backend.

### Step 3 — Reproduce the Failure

Use AWS CLI and curl to generate a controlled request.

### Step 4 — Collect Evidence

Inspect:

- HTTP response status.
- Response headers and body.
- API Gateway configuration.
- CloudWatch logs.
- Backend Lambda logs.
- CloudWatch metrics.
- Relevant IAM or resource policies.

### Step 5 — Isolate the Cause

Determine whether the failure originates from:

- The API client.
- API resource or HTTP method.
- Deployment or stage.
- Authorization configuration.
- API Gateway integration.
- Lambda backend.
- Network or DNS.
- TLS certificate.
- Throttling configuration.

### Step 6 — Apply Targeted Remediation

Correct only the configuration or application behavior responsible for the failure.

### Step 7 — Verify Recovery

Repeat the original request.

Confirm the expected HTTP status and application behavior.

### Step 8 — Clean Up

Delete temporary AWS resources and verify cleanup.

---

## 7. AWS CLI Troubleshooting Commands

### Verify AWS Identity

```bash
aws sts get-caller-identity
```

### Configure Region

```bash
export AWS_REGION="us-east-1"
export AWS_PAGER=""
```

### List REST APIs

```bash
aws apigateway get-rest-apis \
  --region "$AWS_REGION"
```

### Inspect API Resources

```bash
aws apigateway get-resources \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Inspect an API Method

```bash
aws apigateway get-method \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Inspect Lambda Integration

```bash
aws apigateway get-integration \
  --rest-api-id "$REST_API_ID" \
  --resource-id "$RESOURCE_ID" \
  --http-method GET \
  --region "$AWS_REGION"
```

### Inspect API Deployments

```bash
aws apigateway get-deployments \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Inspect API Stages

```bash
aws apigateway get-stages \
  --rest-api-id "$REST_API_ID" \
  --region "$AWS_REGION"
```

### Inspect Usage Plans

```bash
aws apigateway get-usage-plans \
  --region "$AWS_REGION"
```

### Inspect API Keys Without Returning Values

```bash
aws apigateway get-api-keys \
  --region "$AWS_REGION"
```

### Inspect Lambda Configuration

```bash
aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Inspect Lambda Resource-Based Policy

```bash
aws lambda get-policy \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

### Inspect CloudWatch Logs

```bash
aws logs tail "$LOG_GROUP" \
  --since 15m \
  --region "$AWS_REGION"
```

### Send HTTP Requests

```bash
curl -i "$API_URL"
```

### Inspect HTTP Status

```bash
curl -s -o /dev/null \
  -w 'HTTP Status: %{http_code}\n' \
  "$API_URL"
```

### Test a POST Endpoint

```bash
curl -i -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

### Verify DNS

```bash
dig example.com
```

### Inspect TLS Certificate

```bash
openssl s_client \
  -connect example.com:443 \
  -servername example.com
```

The exact variables and resource identifiers are configured separately within each lab.

---

## 8. CloudWatch Monitoring

API Gateway production troubleshooting frequently requires reviewing API Gateway metrics and Lambda backend logs together.

### Important Metrics

| Metric | Meaning |
|---|---|
| Count | API request count |
| 4XXError | Client-side error responses |
| 5XXError | Server-side error responses |
| Latency | Total time observed by API Gateway |
| IntegrationLatency | Time spent waiting on the backend integration |
| Lambda Invocations | Lambda invocation activity |
| Lambda Errors | Lambda execution failures |
| Lambda Throttles | Lambda invocation throttling |

### Important Logging Sources

**API Gateway access logs:** Useful for examining request IDs, methods, paths, status codes, and request latency.

**API Gateway execution logs:** Useful for REST API request-processing and integration troubleshooting where supported and enabled.

**Lambda CloudWatch Logs:** Useful for identifying handler errors, missing dependencies, timeout failures, and application exceptions.

**CloudTrail:** Useful for investigating management and configuration changes.

### Observability Best Practices

- Enable appropriate API access logging.
- Avoid exposing credentials or sensitive request data in logs.
- Correlate API Gateway request IDs with backend execution information where possible.
- Monitor 4XX and 5XX error rates.
- Monitor latency and throttling.
- Set appropriate CloudWatch log retention.
- Use alarms for meaningful production failure conditions.

---

## 9. Cloud Security Engineering Considerations

### Authentication and Authorization

Production APIs should use suitable authentication and authorization mechanisms.

Depending on the API architecture, these may include IAM authorization, Amazon Cognito, JWT authorizers, Lambda authorizers, and resource policies.

### API Keys

API keys help identify clients and apply usage-plan settings.

They should not be treated as a standalone authentication mechanism.

### Least Privilege

Grant API Gateway and Lambda only the permissions required for their specific integrations.

### Encryption

Use HTTPS for API communication.

Use AWS Certificate Manager to manage supported TLS certificates for custom API domains.

### Network Protection

Use AWS WAF and other appropriate protections when the selected API type and endpoint configuration support them.

### Monitoring

Investigate unusual 403 responses, unexpected 5XX increases, throttling patterns, and suspicious request activity.

### Input Validation

Validate user input and avoid exposing internal errors or sensitive backend details in HTTP responses.

### Cost Protection

Use appropriate throttling, AWS Budgets, monitoring, and application controls.

Usage plan throttling and quotas are best-effort targets, not guaranteed spending controls.

---

## 10. Safety and Cost Management

All troubleshooting labs use dedicated, temporary AWS resources.

### Safety Rules

- Never run intentional failures against production APIs.
- Use dedicated API Gateway REST APIs.
- Use dedicated Lambda functions.
- Apply least-privilege IAM permissions.
- Keep load tests controlled.
- Do not publish real API key values.
- Do not publish credentials or secrets.
- Avoid exposing unnecessary public endpoints.
- Verify resource ownership before cleanup.
- Delete temporary resources after each lab.

### Potential AWS Charges

| Resource | Potential Charge |
|---|---|
| API Gateway | API requests |
| AWS Lambda | Invocations and execution duration |
| CloudWatch Logs | Log ingestion and storage |
| AWS Certificate Manager | Depends on certificate type |
| Route 53 | Hosted zones and DNS queries where used |
| AWS WAF | Web ACL and request-related charges if used |

Some labs may require resources that have charges outside standard free usage.

Each practical lab should include cost notes and a cleanup procedure.

---

## 11. Repository Structure

```text
aws-api-gateway-troubleshooting-labs/
│
├── README.md
├── .gitignore
│
├── 01-api-returns-403/
│   └── README.md
│
├── 02-api-returns-404/
│   └── README.md
│
├── 03-api-returns-500/
│   └── README.md
│
├── 04-api-gateway-lambda-integration-failure/
│   └── README.md
│
├── 05-cors-error/
│   └── README.md
│
├── 06-missing-authorization-token/
│   └── README.md
│
├── 07-api-key-usage-plan-misconfiguration/
│   └── README.md
│
├── 08-api-throttling-429/
│   └── README.md
│
├── 09-api-timeout-504/
│   └── README.md
│
└── 10-custom-domain-certificate-failure/
    └── README.md
```

Each lab folder contains its own production scenario, setup instructions, troubleshooting commands, investigation findings, remediation, verification, cleanup procedures, and interview questions.

The folder structure can also include Python source files, IAM policies, JSON payloads, and other reusable configuration artifacts required for the lab.

---

## 12. Lab Documentation Format

Each individual lab README follows a consistent structure:

1. Overview
2. Lab Information
3. Production Incident Scenario
4. AWS Architecture — Broken and Recovered
5. Understanding the Failure
6. Prerequisites and Safety
7. Environment Preparation
8. AWS Resource Deployment
9. Fault Injection
10. Reproduce the Error
11. Investigation Using AWS CLI
12. CloudWatch Diagnostics
13. Root Cause Analysis
14. Remediation
15. Recovery Verification
16. Production Troubleshooting Best Practices
17. Cloud Security Engineering Considerations
18. Cost Management
19. AWS Resource Cleanup
20. Interview Questions and Answers
21. Lessons Learned

Documentation includes working examples and expected outcomes. Actual recovery should be verified through the practical lab before claiming an incident was successfully resolved.

---

## 13. Cloud Engineering Skills Demonstrated

This repository develops practical experience with:

- Amazon API Gateway REST APIs
- HTTP and HTTPS
- HTTP response status codes
- REST API resources and methods
- API stages and deployments
- Lambda proxy integrations
- AWS IAM
- API resource policies
- Authentication and authorization
- API keys and usage plans
- CORS configuration
- API throttling
- Backend timeouts
- AWS Certificate Manager
- DNS troubleshooting
- TLS certificate validation
- Amazon CloudWatch
- AWS CLI v2
- Linux Bash
- Python
- curl
- jq
- OpenSSL
- Root cause analysis
- Incident remediation
- Production observability
- Cloud security practices
- AWS resource cleanup

---

## 14. Interview Preparation

These labs help prepare for common Cloud Engineering and Cloud Security Engineering interview questions.

Examples include:

- Why does API Gateway return HTTP 403?
- What causes HTTP 404 for a REST API?
- How do you investigate API Gateway 500 errors?
- What causes API Gateway–Lambda integration failures?
- How do you troubleshoot missing Lambda invocation permission?
- What is the difference between API Gateway 500 and 502?
- Why can an API work in curl but fail in a browser?
- How do CORS preflight requests work?
- What does Missing Authentication Token mean?
- What is the purpose of API Gateway usage plans?
- Why are API keys not sufficient for authentication?
- How do you troubleshoot API throttling?
- What is the difference between Lambda Duration and IntegrationLatency?
- What causes API Gateway 504 errors?
- How do you investigate a custom domain TLS certificate failure?
- How do you inspect API Gateway using AWS CLI?
- How do you correlate API Gateway and Lambda CloudWatch logs?
- How do you secure a production REST API?

---

## 15. Troubleshooting Philosophy

The purpose of troubleshooting is not simply to make an API return HTTP 200.

A Cloud Engineer should understand:

1. What failed.
2. Where the failure occurred.
3. Why the failure occurred.
4. What evidence confirms the root cause.
5. Which remediation corrects the problem.
6. How to verify that the original request now works.
7. How to reduce the likelihood of recurrence.

This repository emphasizes repeatable investigations, controlled fault injection, clear root cause explanations, and practical AWS CLI remediation.

---

## Official AWS Documentation

- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)
- [API Gateway Gateway Responses](https://docs.aws.amazon.com/apigateway/latest/developerguide/supported-gateway-response-types.html)
- [API Gateway Lambda Proxy Integrations](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- [API Gateway API Keys and Usage Plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [API Gateway Request Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html)
- [API Gateway Monitoring](https://docs.aws.amazon.com/apigateway/latest/developerguide/monitoring-cloudwatch.html)
- [AWS CLI — API Gateway](https://docs.aws.amazon.com/cli/latest/reference/apigateway/)
- [Amazon API Gateway Pricing](https://aws.amazon.com/api-gateway/pricing/)

---

**Repository Goal:** Build hands-on experience troubleshooting production-style AWS API Gateway failures and strengthen practical skills for Cloud Engineer, DevOps Engineer, and Cloud Security Engineer roles.
