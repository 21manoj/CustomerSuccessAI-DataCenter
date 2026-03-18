# Egress Proxy and Custom Domain for CS Pulse / MCP

If your network blocks the default CloudFront domain (`d2oqfugrb2ltg9.cloudfront.net`), you have two options.

---

## Option 1: Allowlist the CloudFront domain (quick fix)

Ask your proxy / firewall admin to allowlist:

| Purpose | Allowlist |
|--------|-----------|
| **This app only** | `d2oqfugrb2ltg9.cloudfront.net` |
| **Any CloudFront** (if policy allows) | `*.cloudfront.net` |

Ensure **HTTPS (443)** to that host is allowed. For MCP/SSE, the client may also need **long-lived HTTPS connections** (no mid-stream blocking).

**MCP connector URL (HTTPS):**  
`https://d2oqfugrb2ltg9.cloudfront.net/mcp`

---

## Option 2: Use a custom domain (recommended if proxy won’t allow CloudFront)

Use a domain you control (e.g. `mcp.yourcompany.com` or `cspulse.yourcompany.com`). You then allowlist that domain in the egress proxy instead of CloudFront.

### Prerequisites

- A domain you manage (e.g. `yourcompany.com`).
- DNS for that domain (Route 53, Cloudflare, etc.).
- AWS CLI and `jq` installed.

### Steps

1. **Request an ACM certificate (us-east-1)**  
   Certificate must be in **us-east-1** for CloudFront.

   ```bash
   aws acm request-certificate \
     --domain-name mcp.yourcompany.com \
     --validation-method DNS \
     --region us-east-1
   ```

   Note the certificate ARN. Validate the cert (add the CNAME records ACM gives you to your DNS).

2. **Add the custom domain to CloudFront**  
   From the repo root:

   ```bash
   CUSTOM_DOMAIN=mcp.yourcompany.com \
   ACM_CERT_ARN=arn:aws:acm:us-east-1:822824391150:certificate/xxxxx \
   ./scripts/update-cloudfront-custom-domain.sh
   ```

   This adds your domain as an alias and attaches the ACM certificate.

3. **Point DNS to CloudFront**  
   In your DNS provider, add a **CNAME**:

   - **Name:** `mcp` (or whatever subdomain you used in step 1).
   - **Value / Target:** `d2oqfugrb2ltg9.cloudfront.net`

   Wait for DNS propagation (often 5–30 minutes).

4. **Use the new URL**  
   MCP connector URL:

   `https://mcp.yourcompany.com/mcp`

   Allowlist `mcp.yourcompany.com` (or your chosen hostname) in the egress proxy.

### Re-run after adding the cert

If you didn’t have the ACM cert when you first ran the script, after the cert is issued and validated run:

```bash
CUSTOM_DOMAIN=mcp.yourcompany.com \
ACM_CERT_ARN=arn:aws:acm:us-east-1:YOUR_ACCOUNT:certificate/YOUR_CERT_ID \
./scripts/update-cloudfront-custom-domain.sh
```

---

## Summary

| Approach | Who does it | Result |
|----------|-------------|--------|
| **Allowlist** | Proxy/firewall admin | Allow `d2oqfugrb2ltg9.cloudfront.net` (or `*.cloudfront.net`) for HTTPS. |
| **Custom domain** | You (DNS + ACM + script) | Use e.g. `https://mcp.yourcompany.com/mcp` and allowlist that domain. |
