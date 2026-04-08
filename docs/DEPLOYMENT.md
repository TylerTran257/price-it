# Deployment Guide

## Infrastructure

| Component | Service | Purpose |
|-----------|---------|---------|
| Compute | AWS Lambda | Serverless API execution |
| API Gateway | REST API | HTTP endpoint, auth, rate limiting |
| Cache | ElastiCache (Redis) or DynamoDB | Response caching |
| Secrets | AWS Secrets Manager | MLS credentials storage |
| Logging | CloudWatch Logs | Structured logs |
| Monitoring | CloudWatch Alarms | Error rate, latency alerts |

## Project Structure (Deployment)

```
price-it/
├── sam.yaml              # AWS SAM template
├── requirements.txt      # Python dependencies
├── src/                  # Application code
└── tests/                # Test suite
```

## AWS SAM Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Price-It API - MLS-based price range estimation

Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues:
      - staging
      - production

Globals:
  Function:
    Timeout: 30
    MemorySize: 256
    Runtime: python3.12
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        CACHE_TTL_SECONDS: 86400
        COMPS_RADIUS_MILES: 1.0
        SOLD_LOOKBACK_DAYS: 180
        PRICE_PERCENTILE_LOW: 25
        PRICE_PERCENTILE_HIGH: 75

Resources:
  PriceItApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: !Ref Environment
      TracingEnabled: true
      Cors:
        AllowMethods: "'POST,OPTIONS'"
        AllowHeaders: "'Content-Type,x-api-key'"
        AllowOrigin: "'*'"

  PriceItFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: src/
      Handler: api.app.handler
      Policies:
        - AWSLambdaBasicExecutionRole
        - SecretsManagerReadWrite
        - DynamoDBReadWritePolicy  # If using DynamoDB for cache
      Events:
        PriceEndpoint:
          Type: Api
          Properties:
            RestApiId: !Ref PriceItApi
            Path: /v1/price
            Method: POST
        HealthEndpoint:
          Type: Api
          Properties:
            RestApiId: !Ref PriceItApi
            Path: /health
            Method: GET
      Environment:
        Variables:
          MLS_RESO_URL: !Sub '{{resolve:secretsmanager:price-it/mls:SecretString:reso_url}}'
          MLS_OAUTH_TOKEN_URL: !Sub '{{resolve:secretsmanager:price-it/mls:SecretString:oauth_url}}'
          MLS_CLIENT_ID: !Sub '{{resolve:secretsmanager:price-it/mls:SecretString:client_id}}'
          MLS_CLIENT_SECRET: !Sub '{{resolve:secretsmanager:price-it/mls:SecretString:client_secret}}'
          GEOCODING_API_KEY: !Sub '{{resolve:secretsmanager:price-it/geocoding:SecretString:api_key}}'

Outputs:
  ApiUrl:
    Description: API Gateway endpoint URL
    Value: !Sub https://${PriceItApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/
```

## Deployment Steps

### Prerequisites

```bash
# Install AWS SAM CLI
brew install aws-sam-cli

# Configure AWS credentials
aws configure

# Login to ECR (if using container image)
aws ecr get-login-password | docker login --username AWS --password-stdin {account}.dkr.ecr.{region}.amazonaws.com
```

### Deploy

```bash
# Build
sam build

# Test locally
sam local start-api

# Deploy (first time)
sam deploy --guided

# Deploy (subsequent)
sam deploy
```

### Environment Variables

```bash
# .env (local development)
MLS_RESO_URL=https://api.reso.org/
MLS_OAUTH_TOKEN_URL=https://auth.reso.org/token
MLS_CLIENT_ID=your_client_id
MLS_CLIENT_SECRET=your_client_secret
GEOCODING_PROVIDER=google
GEOCODING_API_KEY=your_geocoding_key
CACHE_TTL_SECONDS=86400
COMPS_RADIUS_MILES=1.0
SOLD_LOOKBACK_DAYS=180
PRICE_PERCENTILE_LOW=25
PRICE_PERCENTILE_HIGH=75
SQFT_TOLERANCE_PCT=20
BEDROOM_TOLERANCE=1
```

### Secrets Manager Setup

```bash
# Store MLS credentials
aws secretsmanager create-secret \
  --name price-it/mls \
  --secret-string '{"reso_url":"...","oauth_url":"...","client_id":"...","client_secret":"..."}'

# Store geocoding API key
aws secretsmanager create-secret \
  --name price-it/geocoding \
  --secret-string '{"api_key":"..."}'
```

## Cold Start Optimization

Lambda cold starts are acceptable for on-demand usage. To optimize:

1. **Provisioned Concurrency**: Keep 1-2 instances warm for production
2. **Minimize package size**: Use `--use-container` for clean builds
3. **Lazy initialization**: Defer MLS client creation until first request

## Monitoring

### CloudWatch Alarms

```yaml
  HighErrorRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: price-it-high-error-rate
      MetricName: Errors
      Namespace: AWS/Lambda
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
```

### Key Metrics

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error rate | > 5% per 5min | Page on-call |
| Latency (p95) | > 5s | Investigate MLS API |
| Throttles | > 0 | Increase concurrency limit |
| Cache hit rate | < 50% | Review TTL/config |

## CI/CD (Optional)

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS Lambda
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest
      - uses: aws-actions/setup-sam@v2
      - run: sam build
      - run: sam deploy --no-confirm-changeset
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```
