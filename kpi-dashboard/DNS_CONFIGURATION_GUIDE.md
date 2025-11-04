# DNS Configuration Guide for V2

## Quick Setup Instructions

### Required DNS Record

Add this A record to your DNS provider for `triadpartners.ai`:

```
Type:  A
Name:  customervaluesystem
Value: 3.84.178.121
TTL:   Auto (or 300 seconds)
```

### Common DNS Providers

#### AWS Route 53
1. Go to Route 53 Console
2. Select Hosted Zone: `triadpartners.ai`
3. Click "Create Record"
4. Record name: `customervaluesystem`
5. Record type: `A`
6. Value: `3.84.178.121`
7. TTL: `300`
8. Click "Create records"

#### GoDaddy
1. Log into GoDaddy
2. My Products → DNS
3. Select domain: `triadpartners.ai`
4. Add → A Record
5. Name: `customervaluesystem`
6. Value: `3.84.178.121`
7. TTL: `1 Hour`
8. Save

#### Cloudflare
1. Log into Cloudflare
2. Select domain: `triadpartners.ai`
3. DNS → Add record
4. Type: `A`
5. Name: `customervaluesystem`
6. IPv4 address: `3.84.178.121`
7. Proxy status: DNS only (gray cloud)
8. Save

#### Namecheap
1. Log into Namecheap
2. Domain List → Manage → Advanced DNS
3. Add New Record
4. Type: `A Record`
5. Host: `customervaluesystem`
6. Value: `3.84.178.121`
7. TTL: `Automatic`
8. Save

### Verification

After adding the DNS record, wait 5-30 minutes and verify:

```bash
# Check DNS resolution
dig +short customervaluesystem.triadpartners.ai

# Should return:
# 3.84.178.121
```

Or use online tools:
- https://www.whatsmydns.net/#A/customervaluesystem.triadpartners.ai
- https://dnschecker.org/#A/customervaluesystem.triadpartners.ai

### Next Steps

Once DNS is verified (returns `3.84.178.121`):

1. SSH into server:
   ```bash
   ssh -i kpi-dashboard-key.pem ec2-user@3.84.178.121
   ```

2. Run SSL setup script:
   ```bash
   ./setup-v2-ssl.sh
   ```

3. Access V2:
   ```
   https://customervaluesystem.triadpartners.ai
   ```

### Current Status

- ✅ Server configured and running
- ✅ Nginx configured for domain
- ✅ SSL setup script ready
- ⏳ DNS record (you need to add this)
- ⏳ SSL certificate (automatic after DNS)

### Example DNS Record in Different Formats

**BIND Format:**
```
customervaluesystem  300  IN  A  3.84.178.121
```

**Simple Format:**
```
customervaluesystem.triadpartners.ai.  IN  A  3.84.178.121
```

**GUI Format:**
```
Hostname: customervaluesystem
Type: A
Points to: 3.84.178.121
```

---

**Need Help?** The DNS record should point:
- `customervaluesystem.triadpartners.ai` → `3.84.178.121`

That's it! 🎯
