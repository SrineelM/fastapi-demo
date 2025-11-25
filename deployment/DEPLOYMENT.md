# Deployment Guide

This guide provides step-by-step instructions for deploying the FastAPI application to various environments.

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [AWS Deployment](#aws-deployment)
- [Production Best Practices](#production-best-practices)

## Local Development

### Prerequisites
- Python 3.11 or higher
- pip or poetry
- 8GB RAM minimum

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fastapi
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   # Development mode with hot-reload
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Or using Python directly
   python -m app.main
   ```

6. **Access the application**
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Docker Deployment

### Quick Start with Docker Compose

1. **Build and run with Docker Compose**
   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

2. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs

3. **View logs**
   ```bash
   docker-compose logs -f api
   ```

4. **Stop the application**
   ```bash
   docker-compose down
   ```

### Production Docker Build

1. **Build production image**
   ```bash
   docker build -f deployment/docker/Dockerfile -t fastapi-guide:latest .
   ```

2. **Run production container**
   ```bash
   docker run -d \
     --name fastapi-app \
     -p 8000:8000 \
     -e ENVIRONMENT=production \
     -e SECRET_KEY=your-secret-key \
     fastapi-guide:latest
   ```

3. **Health check**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

## Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (EKS, GKE, AKS, or local like Minikube)
- kubectl configured
- Docker image pushed to container registry

### Deployment Steps

1. **Update image in deployment.yaml**
   ```yaml
   # deployment/kubernetes/deployment.yaml
   spec:
     containers:
     - name: fastapi
       image: your-registry/fastapi-guide:latest
   ```

2. **Create namespace (optional)**
   ```bash
   kubectl create namespace fastapi
   ```

3. **Deploy application**
   ```bash
   kubectl apply -f deployment/kubernetes/deployment.yaml
   ```

4. **Deploy ingress (optional)**
   ```bash
   kubectl apply -f deployment/kubernetes/ingress.yaml
   ```

5. **Check deployment status**
   ```bash
   kubectl get deployments
   kubectl get pods
   kubectl get services
   ```

6. **Access logs**
   ```bash
   kubectl logs -f deployment/fastapi-guide
   ```

7. **Port forward for testing**
   ```bash
   kubectl port-forward service/fastapi-service 8000:80
   ```

### Scaling

**Manual scaling:**
```bash
kubectl scale deployment fastapi-guide --replicas=5
```

**Auto-scaling is configured via HorizontalPodAutoscaler in deployment.yaml**

## AWS Deployment

### Option 1: ECS with Fargate (Recommended)

1. **Create ECR repository**
   ```bash
   aws ecr create-repository --repository-name fastapi-guide
   ```

2. **Build and push image**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
   
   # Build image
   docker build -f deployment/docker/Dockerfile -t fastapi-guide:latest .
   
   # Tag image
   docker tag fastapi-guide:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/fastapi-guide:latest
   
   # Push image
   docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/fastapi-guide:latest
   ```

3. **Deploy using CloudFormation**
   ```bash
   aws cloudformation create-stack \
     --stack-name fastapi-guide-stack \
     --template-body file://deployment/aws/cloudformation-template.yaml \
     --parameters ParameterKey=Environment,ParameterValue=production \
     --capabilities CAPABILITY_IAM
   ```

4. **Check stack status**
   ```bash
   aws cloudformation describe-stacks --stack-name fastapi-guide-stack
   ```

5. **Get ALB URL**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name fastapi-guide-stack \
     --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerURL'].OutputValue" \
     --output text
   ```

### Option 2: EC2 with Auto Scaling

1. **Launch EC2 instances**
   - Use Amazon Linux 2 or Ubuntu
   - Install Docker
   - Configure security groups (allow port 8000)

2. **Deploy application**
   ```bash
   # SSH into EC2 instance
   ssh ec2-user@your-instance-ip
   
   # Pull and run Docker container
   docker pull your-registry/fastapi-guide:latest
   docker run -d -p 8000:8000 your-registry/fastapi-guide:latest
   ```

3. **Setup Application Load Balancer**
   - Create target group
   - Register EC2 instances
   - Configure health checks to /api/v1/health

4. **Configure Auto Scaling Group**
   - Min: 2 instances
   - Max: 10 instances
   - Scaling policies based on CPU/Memory

## Production Best Practices

### Security

1. **Environment Variables**
   - Never commit .env files
   - Use AWS Secrets Manager or Kubernetes Secrets
   - Rotate credentials regularly

2. **HTTPS/TLS**
   ```bash
   # Use AWS Certificate Manager for ALB
   # Or Let's Encrypt for Kubernetes Ingress
   ```

3. **Rate Limiting**
   - Configure in application settings
   - Use WAF (Web Application Firewall) for additional protection

4. **API Keys**
   - Implement proper authentication
   - Use OAuth2 or JWT tokens for production

### Monitoring

1. **Application Logs**
   - AWS CloudWatch Logs
   - Kubernetes: Fluentd/ELK stack
   - Structured JSON logging enabled

2. **Metrics**
   - Prometheus for Kubernetes
   - CloudWatch Metrics for AWS
   - Application metrics at /api/v1/metrics

3. **Alerting**
   - Set up alerts for:
     - High error rates
     - Slow response times
     - High memory/CPU usage
     - Failed health checks

4. **Distributed Tracing**
   - OpenTelemetry integration included
   - Connect to Jaeger or AWS X-Ray

### Performance

1. **Resource Allocation**
   - CPU: 1-2 cores per instance
   - Memory: 2-4GB per instance
   - Adjust based on load testing

2. **Caching**
   - Redis for distributed caching
   - In-memory cache for single instance

3. **Load Testing**
   ```bash
   # Using Apache Bench
   ab -n 10000 -c 100 http://your-api/api/v1/health
   
   # Using hey
   hey -n 10000 -c 100 http://your-api/api/v1/users
   ```

4. **Database Connection Pooling**
   - Configure pool size based on expected load
   - Monitor connection usage

### High Availability

1. **Multi-AZ Deployment**
   - Deploy across multiple availability zones
   - Minimum 2 AZs for production

2. **Health Checks**
   - Liveness: /api/v1/live
   - Readiness: /api/v1/ready
   - Health: /api/v1/health

3. **Graceful Shutdown**
   - Handle SIGTERM signals
   - Complete in-flight requests
   - 30-second grace period configured

4. **Backup Strategy**
   - Database backups (if using external DB)
   - Configuration backups
   - Disaster recovery plan

### CI/CD Pipeline

Example GitHub Actions workflow:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ --cov=app
      
      - name: Build Docker image
        run: docker build -t fastapi-guide:${{ github.sha }} .
      
      - name: Push to registry
        run: |
          docker push your-registry/fastapi-guide:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/fastapi-guide \
            fastapi=your-registry/fastapi-guide:${{ github.sha }}
```

### Cost Optimization

1. **AWS**
   - Use Fargate Spot for non-critical workloads
   - Right-size EC2 instances
   - Use Reserved Instances for predictable workloads

2. **Kubernetes**
   - Use cluster autoscaler
   - Implement pod autoscaling (HPA)
   - Set resource requests and limits

3. **Monitoring**
   - Track costs with AWS Cost Explorer
   - Set up billing alerts

## Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check logs
   docker logs fastapi-app
   kubectl logs deployment/fastapi-guide
   
   # Verify environment variables
   # Check port availability
   ```

2. **High memory usage**
   ```bash
   # Check metrics
   curl http://localhost:8000/api/v1/metrics
   
   # Reduce worker count
   # Investigate memory leaks
   ```

3. **Slow response times**
   ```bash
   # Check database connections
   # Review cache hit rates
   # Profile slow endpoints
   ```

4. **Health check failures**
   ```bash
   # Test health endpoint directly
   curl http://localhost:8000/api/v1/health
   
   # Check application logs
   # Verify dependencies
   ```

## Support

For issues and questions:
- Check application logs
- Review metrics at /api/v1/metrics
- Consult Architecture.md for system design
- See Guidelines.md for development practices
