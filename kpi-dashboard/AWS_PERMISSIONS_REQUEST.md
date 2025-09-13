# AWS Permissions Request for KPI Dashboard Deployment

## 📋 **Request Summary**
User: `manojgupta321`  
Account: `822824391150`  
Purpose: Deploy KPI Dashboard application on EC2 (Free Tier)

## 🔑 **Required Permissions**

Please attach these AWS managed policies to user `manojgupta321`:

### **1. EC2 Full Access**
- **Policy ARN**: `arn:aws:iam::aws:policy/AmazonEC2FullAccess`
- **Purpose**: Launch and manage EC2 instances, security groups, key pairs

### **2. IAM Read Only Access** 
- **Policy ARN**: `arn:aws:iam::aws:policy/IAMReadOnlyAccess`
- **Purpose**: Read IAM roles and policies for EC2 instance roles

### **3. ECR Full Access** (Already have this ✅)
- **Policy ARN**: `arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess`
- **Purpose**: Push/pull Docker images

## 🎯 **Alternative: Custom Policy**

If you prefer a custom policy, here's the minimal required permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:RunInstances",
                "ec2:TerminateInstances",
                "ec2:DescribeInstances",
                "ec2:DescribeImages",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeSecurityGroups",
                "ec2:CreateSecurityGroup",
                "ec2:DeleteSecurityGroup",
                "ec2:AuthorizeSecurityGroupIngress",
                "ec2:RevokeSecurityGroupIngress",
                "ec2:CreateKeyPair",
                "ec2:DeleteKeyPair",
                "ec2:ImportKeyPair",
                "ec2:CreateTags",
                "ec2:DescribeTags"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:GetRole",
                "iam:ListRoles"
            ],
            "Resource": "*"
        }
    ]
}
```

## 💰 **Cost Impact**
- **EC2 t2.micro**: FREE (750 hours/month for 12 months)
- **EBS Storage**: FREE (30 GB for 12 months)
- **Data Transfer**: FREE (15 GB out per month for 12 months)
- **Total Monthly Cost**: $0

## 🚀 **Deployment Process**
Once permissions are granted, the deployment will:

1. Create security group with web access (ports 80, 443, 22, 5059)
2. Create SSH key pair for secure access
3. Launch t2.micro EC2 instance (free tier)
4. Install Docker and Docker Compose
5. Deploy KPI Dashboard application
6. Configure nginx reverse proxy
7. Provide public URL for access

## 📞 **Contact**
Please grant these permissions and I'll proceed with the automated deployment.

**Expected deployment time**: 10-15 minutes  
**Application URL**: Will be provided after deployment
