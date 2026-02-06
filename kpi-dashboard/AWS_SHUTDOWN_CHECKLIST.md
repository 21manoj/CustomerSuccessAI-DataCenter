# AWS Shutdown Checklist – Stop All Services to Avoid Charges

**Your repo deploys or references these AWS services.** Use this checklist to find and stop everything.

**Region used in this project:** `us-east-1`

---

## Your cost breakdown (what to shut down first)

From your bill, these are the main cost drivers. **Shut them down in this order** to stop charges:

| Service | Your cost (approx) | What to do |
|---------|--------------------|------------|
| **EC2-Instances** | **~$47** (last period) / $146 total | **#1 priority.** Stop or terminate all EC2 instances (V2/V3 host `i-05d943311f6c90fdf` and any other `kpi-dashboard`). |
| **Elastic Load Balancing** | **~$35** (last period) / $44 total | **#2.** Delete load balancer(s). Console: [EC2 → Load Balancing → Load Balancers](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#LoadBalancers:). Delete each (targets must be gone first). |
| **VPC** | **~$29** (last period) / $52 total | **#3.** Often **NAT Gateway** (~$32/mo + data). Delete NAT Gateway(ies): [VPC → NAT Gateways](https://us-east-1.console.aws.amazon.com/vpc/home?region=us-east-1#NatGateways:). Then you can delete unused VPCs if desired. |
| **Elastic Container Service (ECS)** | **~$13** (last period) / $17 total | **#4.** Scale ECS services to 0 or delete cluster. [ECS → Clusters](https://us-east-1.console.aws.amazon.com/ecs/home?region=us-east-1#/clusters) → select cluster → Services → Update service → Desired count **0**; then Delete service. Delete cluster when empty. |
| **EC2-Other** | ~$2 (EBS, Elastic IPs, etc.) | Stop instances first (reduces EBS charges for attached volumes). Release any **unassociated Elastic IPs**: [EC2 → Elastic IPs](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Addresses:). |
| **Key Management Service** | ~$1 | Optional: delete customer keys if no longer needed. |
| **Secrets Manager** | ~$1.68 | Optional: delete secrets if not needed. |
| **ECR, S3** | &lt;$1 | Optional: delete repos/buckets to avoid storage. |

**Rough total you can eliminate:** ~\$129/month (EC2 + ELB + VPC + ECS + EC2-Other).

**Recommended order (so dependencies don’t block you):**  
1) **ECS** – set desired count to 0, delete services, then delete cluster.  
2) **EC2** – stop or terminate all instances (V2/V3 host and any kpi-dashboard).  
3) **Load balancers** – delete (after ECS/EC2 targets are gone).  
4) **NAT Gateways** – delete (in VPC → NAT Gateways).  
5) **Elastic IPs** – release any unassociated.

---

## V2 and V3 deployments (what you deployed)

From your scripts and docs, **V2 and V3** were deployed like this:

| Deployment | Where it runs | Port / path |
|------------|----------------|-------------|
| **V1** | Same EC2 as below | Backend **5059**, frontend 3000 |
| **V2** | Same EC2 (`deploy-v2-aws.sh`) | Backend **5060**, path `/home/ec2-user/kpi-dashboard-v2` |
| **V3** | Same EC2 (`deploy-v3-final.sh`, V3_DEPLOYMENT_*) | Path `/home/ec2-user/kpi-dashboard-v3`, Docker backend 5059, frontend |

- **One EC2 instance** was used for all of them:
  - **Instance ID (V2 script):** `i-05d943311f6c90fdf`
  - **Public IP (in docs):** `3.84.178.121`
  - **SSH key (in docs):** `kpi-dashboard-key.pem`
- So **one running EC2** = V1 + V2 + V3 on the same box. If you see that instance (or IP) still **running**, stopping/terminating it stops billing for all three.

You may also have created **another** EC2 via `deploy-to-ec2.sh` (tag **Name** = `kpi-dashboard`). Check for **all** running instances in us-east-1 and stop/terminate any that are kpi-dashboard related.

---

## 1. EC2 instances (very common source of charges)

**Console:** [EC2 → Instances](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Instances:)

- Filter by **Running**.
- This repo references:
  - **Instance ID** `i-05d943311f6c90fdf` (V2/V3 host in `deploy-v2-aws.sh`)
  - **Public IP** `3.84.178.121` (V2_DEPLOYMENT_SUCCESS, V3_DEPLOYMENT_GUIDE – same instance)
  - **Name tag** `kpi-dashboard` (from `deploy-to-ec2.sh`)
- **Stop (to keep disk, pay storage only):** Select instance → **Instance state** → **Stop instance**.
- **Terminate (delete and stop most charges):** **Instance state** → **Terminate instance**.

**CLI – list running instances:**
```bash
aws ec2 describe-instances --region us-east-1 \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,PublicIpAddress,Tags[?Key==`Name`].Value|[0],State.Name]' --output table
```

**CLI – stop V2/V3 host (instance from deploy-v2-aws.sh):**
```bash
aws ec2 stop-instances --instance-ids i-05d943311f6c90fdf --region us-east-1
```

**CLI – terminate (permanent):**
```bash
aws ec2 terminate-instances --instance-ids i-05d943311f6c90fdf --region us-east-1
```

**CLI – stop ALL running instances in us-east-1 (use with care):**
```bash
# List first
aws ec2 describe-instances --region us-east-1 --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].InstanceId' --output text
# Then stop each (replace with your instance IDs)
aws ec2 stop-instances --instance-ids i-05d943311f6c90fdf <other-id-if-any> --region us-east-1
```

---

## 2. RDS (database – often $30–100+/month if left on)

**Console:** [RDS → Databases](https://us-east-1.console.aws.amazon.com/rds/home?region=us-east-1#databases:)

- Any **Available** or **Running** DB is billing.
- **Stop (temporary, not all types):** Select DB → **Actions** → **Stop** (if available).
- **Delete:** **Actions** → **Delete** (take a snapshot first if you need data).

**CLI – list DB instances:**
```bash
aws rds describe-db-instances --region us-east-1 \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,DBInstanceStatus]' --output table
```

---

## 3. App Runner (container services – ~$50–100+/month)

**Console:** [App Runner → Services](https://us-east-1.console.aws.amazon.com/apprunner/home?region=us-east-1#/services)

- Repo uses names like **kpi-backend**, **kpi-frontend**.
- **Pause or delete:** Select service → **Actions** → **Pause** or **Delete**.

**CLI – list services:**
```bash
aws apprunner list-services --region us-east-1 --output table
```

---

## 4. ECS (Fargate / EC2 cluster – ~$85–145+/month)

**Console:** [ECS → Clusters](https://us-east-1.console.aws.amazon.com/ecs/home?region=us-east-1#/clusters)

- Repo uses cluster name **kpi-dashboard** or **kpi-dashboard-cluster**.
- For each cluster:
  - Open cluster → **Services** tab → set each service to **Desired count = 0** (stops tasks).
  - Or **Delete** the service.
- To stop all billing for the cluster: delete all services, then **Delete** the cluster (and optionally the task definitions).

**CLI – list clusters and services:**
```bash
aws ecs list-clusters --region us-east-1 --output text
aws ecs list-services --cluster kpi-dashboard-cluster --region us-east-1 --output text
# Scale service to 0
aws ecs update-service --cluster kpi-dashboard-cluster --service kpi-service --desired-count 0 --region us-east-1
```

---

## 5. EKS (Kubernetes – control plane ~$73/month even with 0 nodes)

**Console:** [EKS → Clusters](https://us-east-1.console.aws.amazon.com/eks/home?region=us-east-1#/clusters)

- If you have any EKS cluster, **delete the cluster** (and node groups) to stop the ~$73/month control plane charge.

**CLI – list clusters:**
```bash
aws eks list-clusters --region us-east-1 --output text
```

---

## 6. Elastic IPs (small charge if not attached)

**Console:** [EC2 → Elastic IPs](https://us-east-1.console.aws.amazon.com/ec2/home?region=us-east-1#Addresses:)

- **Unassociated** Elastic IPs cost money. **Release** any you don’t need.

---

## 7. ECR (storage – usually small)

**Console:** [ECR → Repositories](https://us-east-1.console.aws.amazon.com/ecr/repositories?region=us-east-1)

- Repo uses **kpi-dashboard-backend**, **kpi-dashboard-frontend**.
- Storage is cheap; delete repos only if you want to remove images (e.g. **Delete repository**).

---

## 8. Other regions

- Repeat the same checks in **other regions** (e.g. **us-west-2**, **eu-west-1**) if you ever deployed there.
- **Console region** dropdown (top right) → switch region → EC2, RDS, App Runner, ECS, EKS.

---

## 9. See what’s costing money (Cost Explorer)

**Console:** [Billing → Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer)

- **View:** **Cost by service** (or **By linked account** if you have multiple).
- **Time range:** Last month or current month.
- This shows which services (EC2, RDS, App Runner, ECS, etc.) are driving the **$129** so you can target shutdown there first.

---

## 10. Quick “nuclear” list (if you want everything off)

Run these **after** you’ve confirmed you don’t need the resources (replace IDs/names with what you see in the console):

1. **EC2:** Stop or terminate all running instances in us-east-1 (and other regions).
2. **RDS:** Stop or delete all DB instances.
3. **App Runner:** Pause or delete all services.
4. **ECS:** Set desired count to 0 for all services, then delete services and clusters.
5. **EKS:** Delete all clusters (and node groups).
6. **Elastic IPs:** Release unassociated addresses.

---

**Note:** This repo does **not** have access to your AWS account. The checklist above is based on the deployment scripts and docs in this project (EC2, App Runner, ECS, EKS, RDS, us-east-1). Your **$129** bill may come from one or more of these; use **Cost Explorer** to see the exact services, then use the matching section above to shut them down.
