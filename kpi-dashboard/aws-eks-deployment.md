# AWS EKS Deployment Guide

## Overview
Amazon EKS provides managed Kubernetes service for enterprise-grade container orchestration. Best for complex, multi-tenant applications.

## Prerequisites
- AWS CLI configured
- kubectl installed
- eksctl installed
- Docker images in ECR

## Step 1: Create EKS Cluster

```bash
# Create cluster with eksctl
eksctl create cluster \
  --name kpi-dashboard-cluster \
  --region us-east-1 \
  --nodegroup-name workers \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Update kubeconfig
aws eks update-kubeconfig --region us-east-1 --name kpi-dashboard-cluster
```

## Step 2: Create Kubernetes Manifests

### Backend Deployment
```yaml
# k8s-backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kpi-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kpi-backend
  template:
    metadata:
      labels:
        app: kpi-backend
    spec:
      containers:
      - name: backend
        image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-backend:latest
        ports:
        - containerPort: 5059
        env:
        - name: FLASK_ENV
          value: "production"
        - name: SQLALCHEMY_DATABASE_URI
          value: "sqlite:///instance/kpi_dashboard.db"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: kpi-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: kpi-backend-service
spec:
  selector:
    app: kpi-backend
  ports:
  - port: 5059
    targetPort: 5059
  type: ClusterIP
```

### Frontend Deployment
```yaml
# k8s-frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kpi-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: kpi-frontend
  template:
    metadata:
      labels:
        app: kpi-frontend
    spec:
      containers:
      - name: frontend
        image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/kpi-dashboard-frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: kpi-frontend-service
spec:
  selector:
    app: kpi-frontend
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Ingress Configuration
```yaml
# k8s-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: kpi-dashboard-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
spec:
  rules:
  - http:
      paths:
      - path: /api/*
        pathType: Prefix
        backend:
          service:
            name: kpi-backend-service
            port:
              number: 5059
      - path: /
        pathType: Prefix
        backend:
          service:
            name: kpi-frontend-service
            port:
              number: 80
```

## Step 3: Deploy to EKS

```bash
# Create secrets
kubectl create secret generic kpi-secrets \
  --from-literal=openai-api-key=your-openai-api-key

# Deploy applications
kubectl apply -f k8s-backend-deployment.yaml
kubectl apply -f k8s-frontend-deployment.yaml
kubectl apply -f k8s-ingress.yaml

# Check status
kubectl get pods
kubectl get services
kubectl get ingress
```

## Step 4: Configure Auto-scaling

```yaml
# k8s-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kpi-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kpi-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kpi-frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kpi-frontend
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Cost Estimate
- EKS Cluster: ~$72/month (control plane)
- Worker nodes (t3.medium): ~$60-120/month
- ALB: ~$20/month
- Total: ~$152-212/month

## Benefits
- ✅ Full Kubernetes ecosystem
- ✅ Advanced orchestration features
- ✅ Multi-tenant support
- ✅ Service mesh capabilities
- ✅ Enterprise-grade security
