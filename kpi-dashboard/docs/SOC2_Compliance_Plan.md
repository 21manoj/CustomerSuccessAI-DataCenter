# CS Pulse Platform -- SOC 2 Compliance Plan

**Document Version:** 1.0
**Date:** March 22, 2026
**Classification:** Internal -- Confidential
**Owner:** Engineering / Security
**Status:** Planning (Post-Demo Phase)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Trust Service Criteria Assessment](#2-trust-service-criteria-assessment)
3. [Gap Analysis -- Priority Matrix](#3-gap-analysis--priority-matrix)
4. [Technical Controls Needed](#4-technical-controls-needed)
5. [Policy Documents Required](#5-policy-documents-required)
6. [LLM-Specific Considerations](#6-llm-specific-considerations)
7. [Vendor Assessment](#7-vendor-assessment)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Cost Estimate](#9-cost-estimate)
10. [Appendix](#10-appendix)

---

## 1. Executive Summary

### What is SOC 2?

SOC 2 (System and Organization Controls 2) is an auditing framework developed by the AICPA that evaluates an organization's information systems against five Trust Service Criteria: Security, Availability, Processing Integrity, Confidentiality, and Privacy. For B2B SaaS platforms handling customer data, SOC 2 compliance is increasingly table-stakes -- enterprise buyers require it during procurement.

### Why CS Pulse Needs SOC 2

CS Pulse is an AI-native Customer Success platform that processes sensitive customer data including:

- **Revenue data** (ARR, expansion/contraction, contract values)
- **Health scores and KPI measurements** (operational metrics tied to business outcomes)
- **Stakeholder information** (names, roles, engagement patterns, decision-maker maps)
- **Qualitative signals** (sentiment analysis, support tickets, NPS data)
- **Context graph intelligence** (causal chains linking signals to revenue outcomes)

Our buyers are CROs, CFOs, and VP-level Customer Success leaders at PE-backed portfolio companies. These buyers will require SOC 2 compliance before signing enterprise contracts. Without it, CS Pulse will be blocked at procurement for any deal above $50K ARR.

Additionally, CS Pulse integrates with LLM providers (Anthropic Claude API) to process customer data for AI-powered insights. This third-party data processing adds scrutiny during buyer security reviews and requires clear data handling documentation.

### Type I vs Type II

| Aspect | Type I | Type II |
|--------|--------|---------|
| **What it proves** | Controls are designed and in place at a point in time | Controls are operating effectively over a period (typically 6-12 months) |
| **Audit duration** | 2-4 weeks of auditor engagement | 6-12 month observation period + 4-6 weeks auditor engagement |
| **Buyer perception** | Sufficient for initial enterprise deals; shows commitment | Gold standard; required by larger enterprises and PE due diligence |
| **Cost** | $20K-$50K | $30K-$80K |

### Target Timeline

| Milestone | Target Date | Notes |
|-----------|-------------|-------|
| Gap remediation begins | Month 1 (target: May 2026) | Policy creation, encryption, access controls |
| Type I readiness | Month 6 (target: October 2026) | All controls designed and implemented |
| Type I audit | Month 7 (target: November 2026) | Engage auditor for point-in-time assessment |
| Type II observation begins | Month 8 (target: December 2026) | Start 6-month evidence collection period |
| Type II audit complete | Month 14 (target: June 2027) | Full Type II report available for buyers |

---

## 2. Trust Service Criteria Assessment

### 2a. Security (Common Criteria -- CC1 through CC9)

The Security criterion is the foundation of SOC 2. All SOC 2 audits must include Security; the other four criteria are optional.

#### CC1: Control Environment

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Organizational structure | Small engineering team; no dedicated security role | No formal security organization | Designate a security lead (can be part-time for a startup); document reporting structure |
| Security policies | None documented | No Information Security Policy | Draft and ratify Information Security Policy (see Section 5) |
| Board/management oversight | No formal risk oversight process | No risk committee or security review cadence | Establish quarterly security review meetings with leadership |
| Code of conduct | No formal employee security expectations | Missing employee security agreement | Create acceptable use policy; require signed acknowledgment from all team members |

#### CC2: Communication and Information

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Internal communication | Ad-hoc Slack/meetings | No formal security communication channel | Establish #security channel; monthly security updates to team |
| External communication | No security page or status page | No way for customers to learn about security practices | Create public security practices page; publish status page |
| Incident notification | No process | Customers have no way to learn about incidents | Define incident communication SOP; create customer notification templates |

#### CC3: Risk Assessment

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Risk identification | Informal/ad-hoc | No formal risk register | Create risk register with likelihood/impact scoring; review quarterly |
| Risk assessment process | None | No documented methodology | Adopt a lightweight framework (NIST CSF or ISO 27005) |
| Change-related risks | Docker rebuilds, EC2 deployments | No change risk assessment process | Add risk assessment step to change management workflow |
| Fraud risk | API key access model | No fraud risk consideration | Document fraud risk scenarios (API key abuse, data exfiltration) |

#### CC4: Monitoring Activities

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Ongoing monitoring | Basic Flask logging; `activity_logging.py` tracks admin actions and logins | No centralized log aggregation; no alerting | Implement CloudWatch Logs + CloudWatch Alarms; consider a SIEM tool |
| Deficiency evaluation | Informal bug tracking | No formal process to evaluate and remediate control deficiencies | Create security issue tracking workflow with SLAs |
| Internal audit | None | No internal audit function | Engage fractional internal auditor or assign quarterly self-assessments |

#### CC5: Control Activities

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Logical access | Flask-Login session auth; password hashing (`password_hash` column); API keys SHA-256 hashed (`key_hash` column with `key_prefix` for identification) | No MFA; no SSO; no password complexity policy; no session timeout enforcement | Implement MFA (TOTP or WebAuthn); add SSO (SAML/OIDC); enforce password policy; add session timeouts |
| Access provisioning | Admin API creates users; RBAC fields exist (`role`, `allowed_account_ids`, `allowed_customer_ids`, `is_contractor`, `expires_at`) | No formal provisioning/deprovisioning process; no access reviews | Document access provisioning SOP; implement quarterly access reviews; automate contractor expiry enforcement |
| Infrastructure access | SSH to EC2 (presumably key-based) | No bastion host; no audit trail of infrastructure access; no principle of least privilege documentation | Deploy bastion host or use AWS SSM Session Manager; enable CloudTrail; document access matrix |
| Technology controls | Docker containers with nginx reverse proxy | No WAF; no network segmentation within VPC; no intrusion detection | Deploy AWS WAF on CloudFront; implement VPC security groups; enable GuardDuty |

#### CC6: Logical and Physical Access Controls

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Authentication | Password-based login; API key authentication | No MFA; default dev secret key in docker-compose (`SECRET_KEY` defaults to `cspulse-dev-secret-key-min-32-chars`) | Enforce MFA; require strong SECRET_KEY in production; rotate credentials |
| Authorization | Multi-tenant isolation via `customer_id` foreign keys; RBAC fields on User model; API key scopes (`read` by default); `allowed_account_ids` for row-level filtering | No formal authorization matrix documented; Partner API scoping is code-level only | Document authorization matrix; add integration tests for tenant isolation; formalize partner access boundaries |
| Network access | CloudFront HTTPS termination; ports 80, 5059, 8001 exposed in docker-compose | Port 5059 (Flask direct) exposed to host; port 8001 (MCP) exposed; no VPC private subnets | Remove unnecessary port exposure in production; move backend to private subnet; restrict MCP port access |
| Physical access | AWS manages physical infrastructure | N/A (inherited from AWS) | Document reliance on AWS physical controls |

#### CC7: System Operations

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Change management | Git-based development; Docker image builds | No formal change management policy; no approval workflow; no separation of duties | Implement PR review requirements; add deployment approval gates; document change management policy |
| System monitoring | Basic application logging | No infrastructure monitoring; no uptime monitoring; no performance baselines | Deploy CloudWatch monitoring; set up uptime checks; establish performance baselines |
| Incident management | No process | No incident response plan; no on-call rotation; no severity classification | Create incident response plan (see Section 5); establish on-call rotation |
| Vulnerability management | No scanning | No vulnerability scanning; no dependency auditing; no penetration testing | Implement Dependabot/Snyk for dependency scanning; schedule annual penetration test; run OWASP ZAP scans |

#### CC8: Change Management

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Change authorization | Informal (developer pushes, rebuilds EC2) | No formal change approval process | Require PR approvals; implement deployment checklists |
| Change testing | Manual testing; some E2E tests | No staging environment; no automated regression suite | Create staging environment mirroring production; build CI/CD pipeline with automated tests |
| Emergency changes | Ad-hoc hotfixes directly to EC2 | No emergency change procedure | Document emergency change process with post-mortem requirement |

#### CC9: Risk Mitigation

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Risk mitigation strategies | API keys are hashed (SHA-256); RBAC fields exist; tenant isolation via `customer_id` | No formal risk treatment plans; no risk acceptance documentation | Create risk treatment plans for all high/critical risks; document accepted risks with business justification |
| Vendor risk | AWS and Anthropic are key vendors | No vendor risk assessments | Perform vendor risk assessments (see Section 7) |

---

### 2b. Availability

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| SLA definition | No SLA defined | No availability commitment to customers | Define 99.9% uptime SLA; document in customer contracts |
| Uptime monitoring | None | No monitoring of service availability | Implement external uptime monitoring (e.g., Datadog, Pingdom, or UptimeRobot) |
| Redundancy | Single EC2 instance; single-container deployment | Single point of failure; no horizontal scaling; no load balancing | Migrate to ECS/EKS or multi-instance behind ALB; enable auto-scaling |
| Disaster recovery | No DR plan; no documented backup procedures | No DR plan; RPO/RTO undefined | Define RPO/RTO targets; implement cross-region DR capability; document DR plan |
| Backup | PostgreSQL on Docker volume (`pgdata`); no documented backup process | No automated backups; no backup verification; no point-in-time recovery | Migrate to RDS with automated backups; enable point-in-time recovery; test restores monthly |
| Capacity planning | No formal process | No capacity monitoring or forecasting | Monitor resource utilization; set capacity alerts; plan for growth |
| Incident communication | No status page | Customers cannot see service status | Deploy status page (e.g., Statuspage.io, Instatus) |

---

### 2c. Processing Integrity

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Data accuracy | Health scores calculated via weighted KPI rollup (L1 -> L2 -> L3 -> L4); weights loaded from hierarchy (CustomerConfig DB -> bootstrap_weights_config.json -> kpi_definitions.py) | No formal data validation framework; no reconciliation checks | Implement data validation on ingestion (CSV upload); add reconciliation checks between calculated and stored scores; log all calculation parameters |
| Error handling | Flask error handlers; basic try/catch patterns | No structured error classification; no error rate monitoring | Implement structured error logging; monitor error rates; set alerting thresholds |
| Input validation | CSV schema validation (`config/csv_schemas.json`); dry_run mode for uploads | No comprehensive input sanitization across all API endpoints | Audit all API endpoints for input validation; implement request schema validation (e.g., marshmallow or pydantic) |
| Data processing completeness | Wizard pipeline (A -> B -> C) with process_data orchestration; two paths (DB-native vs fresh CSV) | No checksums or completion verification; pipeline failures may leave partial state | Add pipeline transaction boundaries; implement idempotent processing; log completion status per step |
| Output accuracy | KPI scoring engine (`calculate_kpi_health`); ROI engine (`outcome_roi_engine.py`); Power-of-1 calculations | No automated accuracy testing; no regression baselines for calculations | Create golden dataset with known-correct outputs; run regression tests on every deploy |

---

### 2d. Confidentiality

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| Data classification | No classification scheme | Customer data, system data, and public data not formally classified | Define data classification policy (Public, Internal, Confidential, Restricted) |
| Encryption at rest | PostgreSQL on Docker volume -- no encryption at rest | Database contents stored unencrypted on disk | Migrate to RDS with encryption enabled (AES-256); or enable LUKS on EBS volumes |
| Encryption in transit | HTTPS via CloudFront TLS termination | Traffic between CloudFront and EC2 origin may be HTTP; internal container traffic is unencrypted | Enable HTTPS between CloudFront and origin; consider mTLS between containers |
| Field-level encryption | API keys: SHA-256 hashed (`key_hash`); OpenAI key: encrypted (`openai_api_key_encrypted`); n8n keys: encrypted (`n8n_api_key_encrypted`, `webhook_secret_encrypted`) | Passwords are hashed but PII fields (email, phone, names) are stored in plaintext | Implement field-level encryption for PII columns; use AWS KMS for key management |
| Access controls | Multi-tenant isolation via `customer_id`; RBAC fields; API key scopes | No formal access control policy; no regular access reviews | Document access control policy; implement quarterly access reviews; add audit logging for data access |
| Data disposal | No data retention or disposal policy | No process for securely deleting customer data on contract termination | Define data retention periods; implement secure deletion procedures; document in privacy policy |
| Secrets management | API keys in `.env` file; `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SECRET_KEY`, `POSTGRES_PASSWORD` passed as environment variables in docker-compose | Secrets stored in `.env` files; default passwords in docker-compose; no secrets rotation | Migrate to AWS Secrets Manager or HashiCorp Vault; eliminate default credentials; implement rotation policy |

---

### 2e. Privacy

| Area | Current State | Gap | Remediation |
|------|---------------|-----|-------------|
| PII inventory | User model: `email`, `user_name`, `last_login`, `last_used_ip`; Customer model: `email`, `phone`, `customer_name`, `domain`; Stakeholder data in context graph | No formal PII inventory or data map | Create comprehensive PII data map (see Appendix C); classify all PII fields |
| Consent management | No consent mechanism | No user consent for data collection or processing | Implement consent management; update privacy policy; add consent tracking |
| Data retention | No retention policy | Data retained indefinitely | Define retention periods per data class; implement automated purging |
| Data subject rights | No mechanism for data access/deletion requests | Cannot fulfill GDPR/CCPA requests | Build data export and deletion APIs; document DSR process |
| Cross-border transfers | AWS region not documented; Anthropic API calls route to US data centers | No data residency documentation; no DPA with Anthropic | Document data residency; execute DPA with Anthropic; consider EU region deployment for EU customers |
| Privacy policy | None published | No external privacy policy | Draft and publish privacy policy; make accessible from application |
| LLM data processing | Customer data (health scores, signals, KPI data, stakeholder info, revenue figures) sent to Claude API for RAG queries, daily actions, ROI narratives | No documentation of what data goes to LLM; no opt-out mechanism; no data minimization | Document LLM data flows (see Section 6); implement opt-out toggles; minimize data sent to LLM; add audit trail |
| Third-party sharing | Data shared with Anthropic (Claude API), potentially OpenAI (legacy `openai_api_key_encrypted` field) | No third-party data processing agreements | Execute DPAs with all data processors; document in privacy policy |

---

## 3. Gap Analysis -- Priority Matrix

### Critical (Must Fix Before Type I Audit)

These gaps would cause an automatic audit failure. Target remediation: Months 1-3.

| # | Gap | TSC | Effort | Description |
|---|-----|-----|--------|-------------|
| C1 | No encryption at rest | Security, Confidentiality | Medium | Migrate PostgreSQL to RDS with AES-256 encryption enabled; or encrypt EBS volumes |
| C2 | No MFA | Security | Medium | Implement TOTP-based MFA for all user accounts; enforce for admin roles |
| C3 | Default/hardcoded secrets | Security | Low | Remove default `SECRET_KEY` and `POSTGRES_PASSWORD` from docker-compose; require production secrets via Secrets Manager |
| C4 | No Information Security Policy | Security (CC1) | Medium | Draft, approve, and distribute comprehensive security policy |
| C5 | No access control policy | Security (CC5/CC6) | Medium | Document authorization matrix; formalize provisioning/deprovisioning; implement access reviews |
| C6 | No vulnerability scanning | Security (CC7) | Low | Enable Dependabot for Python and JS dependencies; run OWASP ZAP baseline scan |
| C7 | No change management process | Security (CC8) | Low | Require PR reviews; implement deployment approval workflow; document change management policy |
| C8 | No incident response plan | Security (CC7) | Medium | Draft IRP with severity levels, escalation paths, communication templates |
| C9 | Exposed ports in production | Security (CC6) | Low | Remove port 5059 and restrict port 8001 access in production docker-compose |
| C10 | No formal risk assessment | Security (CC3) | Medium | Create risk register; perform initial risk assessment; establish review cadence |

### High (Fix Within 3 Months)

These gaps represent significant control weaknesses. Target remediation: Months 2-4.

| # | Gap | TSC | Effort | Description |
|---|-----|-----|--------|-------------|
| H1 | No centralized logging/SIEM | Security (CC4), Availability | High | Deploy CloudWatch Logs aggregation; implement alerting; consider lightweight SIEM |
| H2 | No backup/recovery procedures | Availability | Medium | Implement automated DB backups (RDS snapshots or pg_dump cron); test restores; document RPO/RTO |
| H3 | No monitoring or uptime checks | Availability | Medium | Deploy CloudWatch metrics; external uptime monitoring; set up PagerDuty or similar |
| H4 | No staging environment | Security (CC8), Processing Integrity | High | Create staging environment mirroring production; implement CI/CD pipeline |
| H5 | Single point of failure (single EC2) | Availability | High | Migrate to multi-instance deployment behind ALB; implement health checks |
| H6 | No data classification policy | Confidentiality | Low | Define classification scheme; label all data stores; document handling procedures per class |
| H7 | No vendor risk assessments | Security (CC9) | Medium | Assess AWS, Anthropic, and any other vendors; document in vendor management policy |
| H8 | No penetration test | Security (CC7) | Medium | Engage third-party penetration tester; schedule annual recurrence |
| H9 | LLM data handling undocumented | Privacy, Confidentiality | Medium | Document what data goes to Claude API; implement data minimization; add audit trail |
| H10 | No data retention policy | Privacy, Confidentiality | Low | Define retention periods; implement automated purging; document in privacy policy |

### Medium (Fix Within 6 Months)

These gaps should be addressed before the Type I audit but are not immediate blockers. Target remediation: Months 3-6.

| # | Gap | TSC | Effort | Description |
|---|-----|-----|--------|-------------|
| M1 | No SSO | Security (CC5) | High | Implement SAML/OIDC SSO integration (planned per RBAC doc) |
| M2 | No formal privacy policy | Privacy | Medium | Draft and publish privacy policy; implement consent management |
| M3 | No business continuity plan | Availability | Medium | Draft BCP covering disaster recovery, communication, and failover procedures |
| M4 | No data subject rights mechanism | Privacy | Medium | Build data export API and deletion workflow for GDPR/CCPA compliance |
| M5 | No WAF | Security (CC5) | Medium | Deploy AWS WAF on CloudFront with OWASP core rule set |
| M6 | No secrets rotation policy | Security, Confidentiality | Medium | Implement automated secrets rotation via Secrets Manager; document rotation schedule |
| M7 | Input validation gaps | Processing Integrity | Medium | Audit all API endpoints; implement schema validation library (pydantic/marshmallow) |
| M8 | No processing integrity regression tests | Processing Integrity | Medium | Create golden dataset; automated regression tests for health score calculations |
| M9 | Field-level PII encryption | Confidentiality, Privacy | High | Encrypt PII fields (email, phone, stakeholder names) with application-level encryption and KMS |
| M10 | No employee security training | Security (CC1) | Low | Develop security awareness training; require annual completion |

### Low (Ongoing / Continuous Improvement)

These items enhance the security posture but are not audit blockers. Target: ongoing post-Type I.

| # | Gap | TSC | Effort | Description |
|---|-----|-----|--------|-------------|
| L1 | No internal audit function | Security (CC4) | Medium | Establish quarterly self-assessment process; consider fractional internal auditor |
| L2 | No security champions program | Security (CC1) | Low | Train developers on secure coding practices; designate security champions |
| L3 | No automated compliance monitoring | All | High | Implement continuous compliance monitoring tool (Vanta, Drata, or Secureframe) |
| L4 | Cross-region DR | Availability | High | Implement cross-region database replication and failover capability |
| L5 | Container security scanning | Security | Medium | Implement container image scanning (Trivy, Snyk Container) in CI pipeline |
| L6 | Network micro-segmentation | Security (CC6) | Medium | Implement VPC private subnets; restrict inter-service communication |

---

## 4. Technical Controls Needed

### 4.1 Infrastructure Security

#### VPC and Network Architecture

```
Current:  EC2 (public subnet) <-- CloudFront
Target:
  Public Subnet:   ALB, NAT Gateway
  Private Subnet:  ECS/EC2 (Flask), RDS PostgreSQL
  CloudFront --> ALB --> Private Subnet
  All outbound via NAT Gateway
```

**Required changes:**
- Move application servers to private subnets (no direct internet access)
- Deploy Application Load Balancer in public subnet
- Configure Security Groups: ALB accepts 443 only; app servers accept traffic from ALB only; RDS accepts traffic from app servers only
- Enable VPC Flow Logs for network traffic auditing
- Remove direct SSH access; use AWS Systems Manager Session Manager instead

#### WAF (Web Application Firewall)

- Deploy AWS WAF on CloudFront distribution
- Enable AWS Managed Rules: Core Rule Set (CRS), Known Bad Inputs, SQL Injection, Linux OS
- Configure rate limiting: 2000 requests/5 minutes per IP
- Log all WAF actions to CloudWatch

#### Encryption at Rest

- **Database**: Migrate to RDS PostgreSQL with encryption enabled (AES-256 via AWS KMS)
- **EBS volumes**: Enable EBS encryption for all EC2 instances
- **S3 buckets** (if any): Enable SSE-S3 or SSE-KMS
- **Docker volumes**: If remaining on EC2, use encrypted EBS volumes for `pgdata`, `uploads`, `verticals_data`

### 4.2 Application Security

#### Input Validation

- Implement request schema validation on all API endpoints using pydantic or marshmallow
- CSV upload validation: enforce column schemas from `config/csv_schemas.json`; reject malformed data; sanitize string fields
- Parameterized queries: verify all database queries use SQLAlchemy ORM (no raw SQL string concatenation)
- File upload restrictions: validate MIME types, enforce size limits, scan for malware

#### CSRF Protection

- Verify Flask-WTF CSRF protection is enabled on all state-changing endpoints
- Ensure CSRF tokens are validated on form submissions
- API endpoints using API key auth are exempt (stateless authentication)

#### XSS Prevention

- React frontend provides automatic XSS protection via JSX escaping
- Audit for `dangerouslySetInnerHTML` usage; replace with sanitized rendering
- Implement Content Security Policy (CSP) headers via nginx
- Add X-Content-Type-Options, X-Frame-Options, X-XSS-Protection headers

#### SQL Injection Prevention

- SQLAlchemy ORM usage provides parameterized queries by default
- Audit for any raw SQL execution (`db.engine.execute`, `text()` without bound parameters)
- Enable SQLAlchemy query logging in development for review

#### Session Security

- Enforce secure session configuration: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`
- Implement session timeout (30 minutes idle, 8 hours absolute)
- Invalidate sessions on password change
- Store sessions server-side (Flask-Session with PostgreSQL backend -- already in use)

### 4.3 Data Security

#### Database Encryption

- **At rest**: RDS encryption (transparent, AES-256)
- **Field-level**: Application-layer encryption for PII columns using AWS KMS envelope encryption
  - Target fields: `users.email`, `customers.email`, `customers.phone`, `ContextNode` fields containing stakeholder PII
  - Implementation: encrypt on write, decrypt on read, store encrypted blob + KMS key ID
- **Backup encryption**: RDS automated backups inherit instance encryption

#### Data Masking

- Implement data masking for non-production environments
- Staging and development databases must use anonymized data
- Log redaction: ensure PII is not written to application logs

### 4.4 Monitoring and Observability

#### CloudWatch Integration

- **Metrics**: CPU, memory, disk, network for all EC2/ECS instances
- **Application metrics**: request latency (p50/p95/p99), error rates, active sessions, API key usage
- **Custom metrics**: health score calculation duration, wizard execution time, MCP tool call latency
- **Alarms**: CPU > 80%, error rate > 1%, disk > 85%, zero healthy hosts, 5xx spike

#### Log Aggregation

- Ship all logs to CloudWatch Logs: nginx access/error logs, Flask application logs, PostgreSQL logs
- Implement structured JSON logging in Flask (replace print statements)
- Retain logs for 90 days in CloudWatch; archive to S3 for 1 year
- Enable CloudTrail for all AWS API calls

#### Alerting

- Configure CloudWatch Alarms with SNS notifications
- Set up PagerDuty or Opsgenie for on-call rotation
- Define alert severity levels aligned with incident response plan

### 4.5 Backup and Recovery

#### Automated Database Backups

- **RDS automated backups**: enable with 7-day retention (minimum)
- **Point-in-time recovery**: enabled by default with RDS; verify WAL archiving
- **Cross-region replication** (Phase 2): set up read replica in secondary region for DR
- **Backup verification**: monthly automated restore test to verify backup integrity

#### Application State Backup

- Customer vertical data (`verticals/customerN-dc2_s/`) backed up to S3 daily
- Configuration files (`bootstrap_weights_config.json`, `kpi_catalog.json`) version-controlled in Git
- Docker images tagged and stored in ECR with immutable tags

### 4.6 Secrets Management

#### Current State (Problematic)

```yaml
# docker-compose.cspulse.yml -- current
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-cspulse_dev}    # Default password!
SECRET_KEY: ${SECRET_KEY:-cspulse-dev-secret-key-min-32-chars}  # Default key!
OPENAI_API_KEY: ${OPENAI_API_KEY:-}
ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
```

#### Target State

- All secrets stored in AWS Secrets Manager
- Application retrieves secrets at startup via AWS SDK (IAM role-based, no static credentials)
- No secrets in `.env` files, docker-compose files, or source code
- Automated rotation: database credentials every 90 days; API keys every 180 days
- Secret access logged via CloudTrail

---

## 5. Policy Documents Required

The following formal policy documents must be drafted, approved by leadership, and distributed to all team members. Each policy must include: purpose, scope, roles and responsibilities, policy statements, exceptions process, and review schedule.

### 5.1 Information Security Policy

**Purpose**: Establish the organization's commitment to information security and define the overarching security framework.

**Key sections**:
- Security objectives and principles
- Organizational security roles (Security Lead, Data Protection Officer)
- Asset management and classification
- Risk management approach
- Compliance requirements
- Policy review schedule (annual minimum)

### 5.2 Access Control Policy

**Purpose**: Define how access to systems, data, and facilities is managed.

**Key sections**:
- Principle of least privilege
- User provisioning and deprovisioning procedures
- Authentication requirements (MFA, password complexity, session management)
- Authorization model (RBAC roles: admin, CSM, viewer, partner, contractor)
- API key lifecycle (creation, scoping, rotation, revocation)
- Multi-tenant isolation requirements
- Quarterly access review procedures
- Privileged access management (infrastructure, database, admin panel)

### 5.3 Incident Response Plan

**Purpose**: Define procedures for detecting, responding to, and recovering from security incidents.

**Key sections**:
- Incident classification (Severity 1-4)
  - **Sev 1**: Data breach, service outage affecting all customers
  - **Sev 2**: Partial service degradation, unauthorized access detected
  - **Sev 3**: Vulnerability discovered, minor security event
  - **Sev 4**: Policy violation, informational alert
- Detection and reporting procedures
- Escalation matrix and on-call rotation
- Containment, eradication, and recovery steps
- Customer notification procedures and timelines (72 hours for GDPR-relevant incidents)
- Post-incident review and lessons learned process
- Evidence preservation requirements
- External reporting obligations (law enforcement, regulators)

### 5.4 Business Continuity Plan

**Purpose**: Ensure CS Pulse can continue operating during and after a disruptive event.

**Key sections**:
- Business impact analysis (BIA) for each service component
- RPO and RTO targets:
  - **Database**: RPO = 1 hour, RTO = 4 hours
  - **Application**: RPO = 0 (stateless), RTO = 1 hour
  - **MCP Server**: RPO = 0, RTO = 2 hours
- Disaster recovery procedures (region failover, database restore)
- Communication plan during outages
- Testing schedule (DR drill every 6 months)
- Dependencies and single points of failure

### 5.5 Data Retention Policy

**Purpose**: Define how long different categories of data are retained and how they are disposed of.

**Key sections**:
- Retention periods by data category:
  - **Customer account data**: Duration of contract + 90 days
  - **KPI measurements and health scores**: Duration of contract + 30 days
  - **Context graph data (signals, decisions, outcomes)**: Duration of contract + 30 days
  - **User activity logs**: 1 year
  - **Application logs**: 90 days
  - **Backups**: 30 days (automated), 1 year (monthly archives)
  - **LLM interaction logs**: 90 days
- Secure deletion procedures (crypto-shredding for encrypted data, PostgreSQL VACUUM for DB)
- Customer data export on contract termination
- Legal hold procedures

### 5.6 Vendor Management Policy

**Purpose**: Define how third-party vendors are assessed, onboarded, and monitored.

**Key sections**:
- Vendor risk classification (Critical, High, Medium, Low)
- Security assessment requirements per tier
- Required contractual provisions (DPA, SLA, security obligations, breach notification)
- Ongoing monitoring and annual reassessment
- Vendor inventory:
  - **AWS** (Critical): Infrastructure provider; SOC 2 Type II certified
  - **Anthropic** (Critical): LLM provider; processes customer data for AI features
  - **n8n** (Medium): Workflow automation; potential integration connector
  - **CloudFront** (Critical): CDN; TLS termination (part of AWS)

### 5.7 Change Management Policy

**Purpose**: Define how changes to production systems are requested, reviewed, approved, and deployed.

**Key sections**:
- Change classification (Standard, Normal, Emergency)
- Change request and approval workflow
- Required artifacts: PR with description, test evidence, rollback plan
- Separation of duties (developer cannot approve own PR and deploy)
- Production deployment procedures (Docker build, EC2 deployment, database migrations)
- Emergency change procedures with mandatory post-mortem
- Change log maintenance

### 5.8 Employee Security Awareness Training

**Purpose**: Ensure all team members understand security responsibilities and threats.

**Key sections**:
- Onboarding security training (within first week)
- Annual refresher training
- Topics: phishing, social engineering, data handling, incident reporting, secure coding, credential management
- Training completion tracking and compliance reporting
- Role-specific training (developers: OWASP Top 10; admins: infrastructure security)

---

## 6. LLM-Specific Considerations

### 6.1 Data Sent to Claude API

CS Pulse sends customer data to Anthropic's Claude API for several features. The following data categories are transmitted:

| Feature | Data Sent | Sensitivity |
|---------|-----------|-------------|
| RAG Queries (`/api/rag-query`) | Account health scores, KPI measurements, qualitative signals, stakeholder names/roles, revenue figures | High -- contains customer PII and financial data |
| CSM Daily Actions | Account names, health scores, risk indicators, playbook recommendations | Medium -- contains business intelligence |
| ROI Narratives | Revenue data, health score history, improvement projections, context graph events | High -- contains financial data |
| Account Journey Timeline | Chronological signals, decisions, outcomes with revenue impact | High -- contains operational and financial data |
| Playbook Recommendations | Account health breakdown, signal history, stakeholder engagement | Medium -- contains business intelligence |
| Power-of-1 Calculations | ARR, metric values, improvement projections | High -- contains financial data |

### 6.2 Anthropic's Data Handling

Key questions to resolve with Anthropic:

- **Data retention**: Does Anthropic retain API request/response data? For how long?
- **Training exclusion**: Confirm that API data is not used for model training (Anthropic's commercial API terms should exclude this, but verify in writing)
- **Data residency**: Where are API requests processed? Can we ensure US-only processing?
- **Subprocessors**: Does Anthropic use subprocessors that may access the data?
- **Breach notification**: What is Anthropic's breach notification timeline?
- **SOC 2 report**: Request Anthropic's SOC 2 Type II report (if available)
- **DPA**: Execute a Data Processing Agreement with Anthropic

### 6.3 Data Minimization Strategies

To reduce risk exposure through LLM processing:

1. **Anonymize before sending**: Replace customer/account names with identifiers; strip email addresses and phone numbers from context sent to LLM
2. **Aggregate where possible**: Send summary statistics rather than individual data points when the use case permits
3. **Scope limiting**: Only send data relevant to the specific query; do not send entire account histories for simple questions
4. **PII stripping**: Implement a pre-processing pipeline that removes or redacts PII before LLM API calls
5. **Token budget**: Limit context window usage to minimize data exposure per request

### 6.4 Opt-Out Mechanisms

Implement customer-level controls for LLM data processing:

- **Feature toggle**: Per-customer flag to disable all LLM-powered features (use existing `feature_toggles.py` pattern)
- **Granular controls**: Allow customers to opt out of specific LLM features while keeping others
- **Data residency override**: Allow customers to specify that their data must not leave a specific region
- **Notification**: Inform customers in the UI when a feature sends data to an external LLM

### 6.5 Audit Trail for LLM Queries

Implement comprehensive logging of all LLM interactions:

- **Log fields**: timestamp, customer_id, account_id, user_id, feature/endpoint, prompt template used, data categories included, response summary (not full response), token count, model version
- **Storage**: Dedicated `llm_audit_log` table in PostgreSQL
- **Retention**: 90 days in database; archived to S3 for 1 year
- **Access**: Queryable via admin API; exportable for audit evidence
- **Do NOT log**: Full prompts or responses containing customer data (to avoid creating a secondary data store)

---

## 7. Vendor Assessment

### 7.1 AWS (Amazon Web Services)

| Aspect | Status | Notes |
|--------|--------|-------|
| SOC 2 Type II | Certified | AWS publishes SOC 2 Type II reports via AWS Artifact; covers infrastructure controls |
| Inherited controls | Applicable | Physical security, environmental controls, network infrastructure are inherited from AWS |
| Shared responsibility | Understood | AWS secures the cloud; CS Pulse secures what runs in the cloud (OS, app, data, access) |
| DPA | Available | AWS Data Processing Addendum is part of the service terms |
| Data residency | Configurable | Select specific AWS regions; currently deployed in a single region |
| Compliance reports | Available | SOC 1, SOC 2, SOC 3, ISO 27001, PCI DSS, HIPAA BAA -- all available via AWS Artifact |

**Action items**:
- Download latest AWS SOC 2 Type II report from AWS Artifact
- Document which AWS services are in scope (EC2, RDS, CloudFront, S3, CloudWatch, KMS, Secrets Manager)
- Map AWS inherited controls to CS Pulse's SOC 2 control matrix

### 7.2 Anthropic (Claude API)

| Aspect | Status | Notes |
|--------|--------|-------|
| SOC 2 Type II | Verify | Anthropic may have SOC 2; request their report or security documentation |
| Data processing terms | Review needed | Review Anthropic's commercial API terms for data retention, training exclusion, and subprocessors |
| DPA | Needed | Execute a Data Processing Agreement; ensure it covers GDPR requirements if serving EU customers |
| Security practices | Review needed | Request Anthropic's security whitepaper or questionnaire responses |
| Breach notification | Clarify | Confirm breach notification timeline and procedures |
| Data residency | US-based | Confirm API processing occurs in US data centers |

**Action items**:
- Request Anthropic's SOC 2 report or security documentation
- Execute DPA with Anthropic
- Document data flows between CS Pulse and Anthropic
- Add Anthropic to vendor risk register with annual reassessment

### 7.3 n8n / Integration Partners

| Aspect | Status | Notes |
|--------|--------|-------|
| n8n integration | Planned | `N8nIntegration` model exists in `models.py` with encrypted API keys and webhook secrets |
| Data exposure | Medium | Workflow automation may process customer data through third-party nodes |
| Security assessment | Not done | Need to assess n8n's security posture before production use |

**Action items**:
- Assess n8n's security posture and SOC 2 status before enabling in production
- Document which data flows through n8n workflows
- Ensure webhook secrets are properly rotated (rotation fields exist: `webhook_secret_rotated_at`, `webhook_secret_grace_period_until`)
- Evaluate self-hosted vs cloud n8n for data residency control

### 7.4 Other Vendors to Assess

Any future vendors must be assessed before onboarding. Candidates may include:
- SIEM provider (if not using CloudWatch natively)
- Uptime monitoring service
- Compliance automation platform (Vanta, Drata, Secureframe)
- Email/notification service for incident communication
- Penetration testing firm

---

## 8. Implementation Roadmap

### Month 1-2: Foundation (Policies, Encryption, Access Controls)

**Policy work:**
- [ ] Draft Information Security Policy
- [ ] Draft Access Control Policy
- [ ] Draft Change Management Policy
- [ ] Create risk register and perform initial risk assessment
- [ ] Define data classification scheme
- [ ] Designate Security Lead

**Technical work:**
- [ ] Migrate PostgreSQL to RDS with encryption enabled
- [ ] Implement AWS Secrets Manager; remove all default credentials from docker-compose
- [ ] Implement MFA for user authentication (TOTP)
- [ ] Remove exposed ports (5059) in production configuration
- [ ] Enable Dependabot/Snyk for dependency vulnerability scanning
- [ ] Configure VPC with private subnets; move application to private subnet
- [ ] Enable CloudTrail for AWS API logging
- [ ] Implement structured JSON logging in Flask application

**Vendor work:**
- [ ] Request Anthropic's SOC 2 report and security documentation
- [ ] Execute DPA with Anthropic
- [ ] Download AWS SOC 2 report from AWS Artifact

### Month 3-4: Monitoring, Incident Response, Backup

**Policy work:**
- [ ] Draft Incident Response Plan
- [ ] Draft Business Continuity Plan
- [ ] Draft Data Retention Policy
- [ ] Draft Vendor Management Policy

**Technical work:**
- [ ] Deploy CloudWatch Logs aggregation for all services
- [ ] Set up CloudWatch Alarms and SNS notifications
- [ ] Implement external uptime monitoring
- [ ] Configure automated RDS backups with 7-day retention
- [ ] Perform first backup restore test
- [ ] Deploy AWS WAF on CloudFront with managed rule sets
- [ ] Create staging environment mirroring production
- [ ] Implement CI/CD pipeline with automated testing
- [ ] Set up on-call rotation (PagerDuty or equivalent)
- [ ] Conduct first penetration test (engage third-party firm)

**LLM-specific work:**
- [ ] Document all data flows to Claude API (Section 6 detail)
- [ ] Implement LLM audit logging (`llm_audit_log` table)
- [ ] Build PII stripping pre-processor for LLM API calls
- [ ] Implement per-customer LLM opt-out feature toggle

### Month 5-6: Audit Prep and Type I Readiness

**Policy work:**
- [ ] Draft Employee Security Awareness Training program
- [ ] Draft Privacy Policy (external-facing)
- [ ] Complete all policy reviews and obtain leadership sign-off
- [ ] Distribute policies and collect signed acknowledgments

**Technical work:**
- [ ] Implement field-level PII encryption (email, phone, stakeholder names)
- [ ] Implement SSO (SAML/OIDC) integration
- [ ] Build data subject request (DSR) workflow for export/deletion
- [ ] Create processing integrity regression test suite (golden dataset)
- [ ] Implement session timeout enforcement
- [ ] Complete input validation audit across all API endpoints
- [ ] Implement quarterly access review process (first review)

**Audit preparation:**
- [ ] Select SOC 2 auditor (obtain quotes from 2-3 firms)
- [ ] Compile evidence package: policies, screenshots, configurations, logs
- [ ] Perform internal readiness assessment against all CC criteria
- [ ] Remediate any findings from readiness assessment
- [ ] Complete vendor risk assessments for all critical vendors

### Month 7: Type I Audit

- [ ] Engage auditor for Type I examination
- [ ] Provide auditor access to evidence and personnel
- [ ] Support auditor walkthroughs and testing
- [ ] Review draft report and remediate any findings
- [ ] Receive final Type I report

### Month 8-12: Type II Evidence Period

- [ ] Begin continuous evidence collection
- [ ] Maintain all controls consistently (this is what Type II proves)
- [ ] Conduct quarterly access reviews (Q2, Q3, Q4)
- [ ] Perform second penetration test (month 10)
- [ ] Conduct DR drill (month 9)
- [ ] Complete second backup restore test (month 10)
- [ ] Continue security awareness training (ongoing)
- [ ] Perform vendor reassessments (annual cycle)
- [ ] Maintain change management log with all production changes
- [ ] Document and review all incidents per IRP

### Month 13-14: Type II Audit

- [ ] Engage auditor for Type II examination
- [ ] Provide 6-month evidence package
- [ ] Support auditor testing of control operating effectiveness
- [ ] Remediate any findings
- [ ] Receive final Type II report
- [ ] Publish SOC 2 badge on website and share report with prospects

---

## 9. Cost Estimate

### 9.1 Auditor Fees

| Item | Estimated Cost | Notes |
|------|----------------|-------|
| Type I audit | $20,000 - $50,000 | Point-in-time; simpler scope for a startup |
| Type II audit | $30,000 - $80,000 | 6-month observation period; more extensive testing |
| Pre-audit readiness assessment | $5,000 - $15,000 | Optional but recommended; identifies gaps before formal audit |
| **Subtotal** | **$55,000 - $145,000** | Over 14-month period |

### 9.2 Infrastructure Upgrades

| Item | Monthly Cost | Annual Cost | Notes |
|------|-------------|-------------|-------|
| RDS PostgreSQL (db.t3.medium, encrypted) | $70 - $150 | $840 - $1,800 | Replaces Docker PostgreSQL |
| ALB (Application Load Balancer) | $25 + usage | $300 - $600 | Required for multi-instance deployment |
| AWS WAF | $5 + $1/M requests | $100 - $300 | CloudFront WAF integration |
| AWS Secrets Manager | $0.40/secret/month | $50 - $100 | ~10-15 secrets |
| CloudWatch Logs + Alarms | $50 - $200 | $600 - $2,400 | Log storage + custom metrics + alarms |
| AWS KMS | $1/key + $0.03/10K requests | $50 - $200 | For field-level encryption |
| VPC NAT Gateway | $32 + data processing | $400 - $600 | Required for private subnet internet access |
| **Subtotal** | **$250 - $700/mo** | **$3,000 - $8,400/yr** | |

### 9.3 Tools and Services

| Item | Annual Cost | Notes |
|------|-------------|-------|
| Compliance automation (Vanta/Drata/Secureframe) | $10,000 - $25,000 | Automates evidence collection; highly recommended |
| Vulnerability scanning (Snyk/Dependabot) | $0 - $5,000 | Free tier may suffice initially; paid for advanced features |
| Uptime monitoring (Datadog/Pingdom) | $0 - $2,000 | Free tier available for basic monitoring |
| On-call/alerting (PagerDuty/Opsgenie) | $0 - $2,000 | Free tier for small teams |
| Penetration testing (annual) | $5,000 - $20,000 | Third-party engagement; scope-dependent |
| **Subtotal** | **$15,000 - $54,000/yr** | |

### 9.4 Staff Time

| Activity | Estimated Hours | Notes |
|----------|-----------------|-------|
| Policy drafting and review | 80 - 120 hours | Can be parallelized across team |
| Technical remediation (encryption, MFA, monitoring) | 160 - 240 hours | Engineering effort over 6 months |
| Audit preparation (evidence collection) | 40 - 60 hours | Significantly reduced with compliance automation tool |
| Audit support (auditor interaction) | 20 - 40 hours | Interviews, walkthroughs, Q&A |
| Ongoing compliance maintenance | 5 - 10 hours/month | Access reviews, log reviews, policy updates |
| **Total first year** | **350 - 550 hours** | ~2-3 months FTE equivalent |

### 9.5 Total First-Year Cost Summary

| Category | Low Estimate | High Estimate |
|----------|-------------|---------------|
| Auditor fees | $55,000 | $145,000 |
| Infrastructure upgrades | $3,000 | $8,400 |
| Tools and services | $15,000 | $54,000 |
| Staff time (at $100/hr blended) | $35,000 | $55,000 |
| **Total** | **$108,000** | **$262,400** |

**Recommendation**: Target the lower end by using a startup-friendly auditor (e.g., Johanson Group, Prescient Assurance), leveraging free tool tiers, and using a compliance automation platform to reduce staff time. Realistic budget: **$120,000 - $160,000** for the first 14 months through Type II completion.

---

## 10. Appendix

### Appendix A: Current Architecture Reference

```
                    Internet
                       |
                  CloudFront (HTTPS/TLS)
                       |
                   EC2 Instance
                       |
                +------+------+
                |   Docker    |
                |  Compose    |
                |             |
          +-----+-----+------+-----+
          |           |            |
        nginx       Flask       PostgreSQL
       (port 80)  (port 5059)  (port 5432)
          |           |            |
          |     +-----+-----+     |
          |     |           |     |
          |   App Routes  MCP Server
          |  (REST API)  (port 8001)
          |     |           |
          |     +-----------+
          |           |
          |     Anthropic Claude API
          |     (external, HTTPS)
          |
     React SPA
    (static files)
```

**Key infrastructure components:**
- **CloudFront**: CDN and HTTPS termination (TLS 1.2+)
- **EC2**: Single instance running Docker Compose
- **nginx**: Reverse proxy, serves React static files, proxies `/api/` to Flask, proxies `/mcp` to MCP server
- **Flask (Gunicorn)**: Backend API server (4 workers, 120s timeout)
- **PostgreSQL**: Primary data store (Docker volume, no encryption at rest)
- **MCP Server**: Streamable HTTP transport on port 8001 for Claude.ai integration

### Appendix B: Data Flow Diagram

```
Customer Data Sources          CS Pulse Platform              External Services
====================          ==================              =================

CSV Upload (manual)  ------>  Onboarding API
                              (validation, ingestion)
                                    |
Load Driver (automated) --->  REST API (/api/dc2s/*)
                                    |
                                    v
                              PostgreSQL Database
                              (accounts, KPIs, health
                               scores, signals, context
                               graph, stakeholders,
                               revenue data)
                                    |
                              +-----+-----+
                              |           |
                              v           v
                         Health Score   Context Graph
                         Calculator    Intelligence
                              |           |
                              +-----+-----+
                                    |
                              +-----+-----+
                              |           |
                              v           v
                         REST API     MCP Server
                         (Flask)     (port 8001)
                              |           |
                              v           v
                         React UI     Claude.ai
                        (browser)    (remote MCP)
                              |
                              v
                     RAG Query (/api/rag-query)
                              |
                              v
                     Anthropic Claude API  ------>  Anthropic Servers
                     (HTTPS, external)              (US data centers)
                              |
                     Data sent to Claude:
                     - Account names, health scores
                     - KPI measurements and trends
                     - Qualitative signals (sentiment)
                     - Stakeholder names and roles
                     - Revenue figures (ARR, at-risk)
                     - Context graph events
                              |
                              v
                     Response returned to user
                     (not stored by Anthropic
                      per commercial API terms --
                      VERIFY with Anthropic)
```

### Appendix C: PII Fields in Database

The following database columns contain or may contain personally identifiable information (PII):

#### Definite PII

| Table | Column | Data Type | Description | Encryption Status |
|-------|--------|-----------|-------------|-------------------|
| `customers` | `email` | String | Customer admin email | Plaintext |
| `customers` | `phone` | String | Customer phone number | Plaintext |
| `customers` | `customer_name` | String | Company name (may contain individual names for sole proprietors) | Plaintext |
| `users` | `email` | String | User login email | Plaintext |
| `users` | `user_name` | String | User display name | Plaintext |
| `users` | `password_hash` | String(128) | Hashed password | Hashed (acceptable) |
| `users` | `last_login` | DateTime | Last login timestamp | Plaintext |
| `customer_api_keys` | `last_used_ip` | String(45) | IP address of last API call | Plaintext |

#### Potential PII (Context Graph / Stakeholder Data)

| Table | Column | Data Type | Description | Encryption Status |
|-------|--------|-----------|-------------|-------------------|
| `context_nodes` | `title` | String | May contain stakeholder names (node_type=STAKEHOLDER) | Plaintext |
| `context_nodes` | `description` | Text | May contain names, roles, contact info in narrative text | Plaintext |
| `context_nodes` | `metadata` | JSON | May contain stakeholder details, email addresses | Plaintext |
| `qualitative_signals` | `signal_text` | Text | May reference individuals by name in signal descriptions | Plaintext |
| `engagement_events` (if exists) | Various | Various | Stakeholder engagement data may include names and roles | Plaintext |

#### Sensitive Business Data (Not PII but Confidential)

| Table | Column | Data Type | Description |
|-------|--------|-----------|-------------|
| `accounts` | `revenue` | Numeric | Account ARR -- highly sensitive financial data |
| `context_nodes` | `revenue_impact` | Numeric | Revenue at risk/protected/expansion amounts |
| `health_scores` | `overall_score` | Numeric | Account health -- competitive intelligence |
| `dc2s_kpi` | Various measurement columns | Numeric | Operational KPI data -- customer proprietary |
| `customer_configs` | `openai_api_key_encrypted` | Text | Third-party API credential | Encrypted (acceptable) |
| `n8n_integrations` | `n8n_api_key_encrypted` | String | Integration credential | Encrypted (acceptable) |
| `n8n_integrations` | `webhook_secret_encrypted` | String | Webhook authentication secret | Encrypted (acceptable) |

#### Recommended Encryption Priority

1. **Immediate** (Month 1): `users.email`, `customers.email`, `customers.phone`, `customer_api_keys.last_used_ip`
2. **Short-term** (Month 3): `context_nodes.metadata` (for STAKEHOLDER type nodes), `qualitative_signals.signal_text` (or implement PII scrubbing on ingestion)
3. **Medium-term** (Month 5): Evaluate field-level encryption for `accounts.revenue` and `context_nodes.revenue_impact` based on customer requirements

---

*This document should be reviewed and updated quarterly. The next review is scheduled for June 2026.*

*Prepared by the CS Pulse Engineering Team. For questions, contact the designated Security Lead.*
