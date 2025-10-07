# Deployment Guide

## Overview

This guide covers deploying the Authenticity Ratio (AR) tool in different environments, from local development to production AWS infrastructure.

## Prerequisites

### Required Software
- Python 3.9+
- AWS CLI v2
- Docker (optional)
- Git

### AWS Services
- S3 buckets for data storage
- Athena for analytics
- IAM roles and policies
- CloudWatch for logging

## Local Development Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd AR
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp env.example .env
# Edit .env with your API keys and configuration
```

### 5. AWS Configuration
```bash
aws configure
# Enter your AWS credentials and region
```

### 6. Test Installation
```bash
python -m pytest tests/
python scripts/run_pipeline.py --brand-id test --keywords "test" --dry-run
```

## AWS Infrastructure Setup

### 1. S3 Buckets
Create the required S3 buckets:

```bash
# Raw data bucket
aws s3 mb s3://ar-ingestion-raw

# Normalized data bucket  
aws s3 mb s3://ar-ingestion-normalized

# Athena results bucket
aws s3 mb s3://ar-athena-result
```

### 2. IAM Roles
Create IAM roles with the provided policies:

```bash
# Analyst role (read-only)
aws iam create-role --role-name AR-Analyst-Role --assume-role-policy-document file://ar-analyst-role.json

# Pipeline role (read-write)
aws iam create-role --role-name AR-Pipeline-Role --assume-role-policy-document file://ar-pipeline-role.json
```

### 3. Athena Workgroup
```sql
CREATE WORKGROUP AR-MVP
WITH (
    description = 'AR MVP workgroup',
    state = 'ENABLED',
    result_configuration = {
        output_location = 's3://ar-athena-result/AR-MVP/',
        encryption_configuration = {
            encryption_option = 'SSE_S3'
        }
    }
);
```

### 4. Database Schema
Execute the DDL statements from the schema file:

```bash
aws athena start-query-execution \
    --query-string "$(cat schema.sql)" \
    --work-group AR-MVP
```

## Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scripts/run_pipeline.py"]
```

### 2. Build and Run
```bash
docker build -t ar-tool .
docker run -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
           -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
           ar-tool --brand-id test --keywords "test"
```

## Production Deployment

### 1. EC2 Deployment
```bash
# Launch EC2 instance with appropriate IAM role
# Install dependencies
sudo yum update -y
sudo yum install python3 python3-pip git -y

# Clone and setup
git clone <repository-url>
cd AR
pip3 install -r requirements.txt

# Setup systemd service
sudo cp ar-tool.service /etc/systemd/system/
sudo systemctl enable ar-tool
sudo systemctl start ar-tool
```

### 2. Lambda Deployment
For serverless deployment:

```bash
# Package for Lambda
pip install -r requirements.txt -t ./package
zip -r ar-tool-lambda.zip package/ *.py

# Deploy to Lambda
aws lambda create-function \
    --function-name ar-tool \
    --runtime python3.9 \
    --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
    --handler main.lambda_handler \
    --zip-file fileb://ar-tool-lambda.zip
```

### 3. ECS Deployment
Create ECS task definition:

```json
{
  "family": "ar-tool",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/AR-Pipeline-Role",
  "containerDefinitions": [
    {
      "name": "ar-tool",
      "image": "your-account.dkr.ecr.region.amazonaws.com/ar-tool:latest",
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ar-tool",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Monitoring and Logging

### 1. CloudWatch Logs
```bash
# Create log group
aws logs create-log-group --log-group-name /ar-tool

# Setup log retention
aws logs put-retention-policy \
    --log-group-name /ar-tool \
    --retention-in-days 30
```

### 2. CloudWatch Alarms
```bash
# Create alarm for high error rate
aws cloudwatch put-metric-alarm \
    --alarm-name "AR-Tool-High-Error-Rate" \
    --alarm-description "Alert when error rate is high" \
    --metric-name Errors \
    --namespace AR-Tool \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold
```

### 3. Health Checks
Create health check endpoint:

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })
```

## Security Best Practices

### 1. Network Security
- Use VPC for network isolation
- Configure security groups with minimal required access
- Enable VPC Flow Logs for monitoring

### 2. Data Encryption
- Enable S3 server-side encryption
- Use AWS KMS for key management
- Encrypt data in transit with TLS

### 3. Access Control
- Use IAM roles instead of access keys
- Implement least privilege principle
- Enable AWS CloudTrail for audit logging

### 4. Secrets Management
- Use AWS Secrets Manager for API keys
- Rotate credentials regularly
- Never commit secrets to version control

## Scaling Considerations

### 1. Horizontal Scaling
- Use ECS/Fargate for auto-scaling
- Implement queue-based processing
- Use SQS for task distribution

### 2. Performance Optimization
- Implement caching for frequently accessed data
- Use batch processing for large datasets
- Optimize database queries

### 3. Cost Optimization
- Use Spot instances for batch processing
- Implement data lifecycle policies
- Monitor and optimize resource usage

## Troubleshooting

### Common Issues

#### 1. Athena Query Failures
```bash
# Check query execution status
aws athena get-query-execution --query-execution-id QUERY_ID

# Repair table partitions
aws athena start-query-execution \
    --query-string "MSCK REPAIR TABLE ar_mvp.ar_content_normalized_v2" \
    --work-group AR-MVP
```

#### 2. S3 Access Issues
```bash
# Test S3 access
aws s3 ls s3://ar-ingestion-normalized/

# Check IAM permissions
aws iam simulate-principal-policy \
    --policy-source-arn arn:aws:iam::ACCOUNT:role/AR-Pipeline-Role \
    --action-names s3:PutObject \
    --resource-arns arn:aws:s3:::ar-ingestion-normalized/*
```

#### 3. API Rate Limits
```bash
# Check API quotas
aws service-quotas get-service-quota \
    --service-code lambda \
    --quota-code L-B99A9384
```

### Log Analysis
```bash
# View recent logs
aws logs describe-log-streams --log-group-name /ar-tool
aws logs get-log-events --log-group-name /ar-tool --log-stream-name STREAM_NAME
```

## Backup and Recovery

### 1. Data Backup
```bash
# Backup S3 data
aws s3 sync s3://ar-ingestion-normalized/ s3://ar-backup/normalized/
aws s3 sync s3://ar-athena-result/ s3://ar-backup/results/
```

### 2. Configuration Backup
```bash
# Export IAM policies
aws iam get-role-policy --role-name AR-Pipeline-Role --policy-name AR-Pipeline-Policy

# Export Athena queries
aws athena list-query-executions --work-group AR-MVP
```

### 3. Disaster Recovery
- Implement cross-region replication for S3
- Maintain infrastructure as code (Terraform/CloudFormation)
- Document recovery procedures
- Test recovery processes regularly
