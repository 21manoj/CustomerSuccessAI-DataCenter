# V2 Domain Setup Guide

## 🌐 Domain Configuration for V2

**New Domain:** `https://customervaluesystem.triadpartners.ai`  
**Server IP:** `3.84.178.121`  
**Ports:** Frontend: 3001, Backend: 8080

---

## ✅ Completed Steps

### 1. Nginx Configuration
- ✅ Created nginx config at `/etc/nginx/conf.d/customervaluesystem.conf`
- ✅ Configured HTTP proxy to V2 frontend (port 3001)
- ✅ Configured API proxy to V2 backend (port 8080)
- ✅ Set up Let's Encrypt challenge location
- ✅ Nginx configuration tested and reloaded

### 2. SSL Setup Script
- ✅ Created automated SSL setup script at `/home/ec2-user/setup-v2-ssl.sh`
- ✅ Script includes DNS verification
- ✅ Script handles Let's Encrypt certificate request
- ✅ Script configures HTTPS redirect

---

## 📋 Required Steps (Manual)

### Step 1: Configure DNS A Record

You need to add a DNS A record in your domain registrar/DNS provider:

**DNS Record Details:**
```
Type:  A
Name:  customervaluesystem
Host:  customervaluesystem.triadpartners.ai
Value: 3.84.178.121
TTL:   300 (or Auto)
```

**Where to configure:**
- Log into your DNS provider (e.g., GoDaddy, Cloudflare, Route53, etc.)
- Go to DNS management for `triadpartners.ai`
- Add a new A record with the details above

### Step 2: Wait for DNS Propagation

After adding the DNS record:
- Wait 5-30 minutes for DNS propagation
- Verify DNS is working:
  ```bash
  dig +short customervaluesystem.triadpartners.ai
  # Should return: 3.84.178.121
  ```

### Step 3: Run SSL Setup Script

Once DNS is confirmed working, SSH into the server and run:

```bash
ssh -i kpi-dashboard-key.pem ec2-user@3.84.178.121
cd /home/ec2-user
./setup-v2-ssl.sh
```

The script will:
1. ✅ Verify DNS points to correct IP
2. ✅ Request Let's Encrypt SSL certificate
3. ✅ Configure HTTPS with auto-redirect
4. ✅ Set up certificate auto-renewal
5. ✅ Reload nginx

---

## 🎯 Final URLs

### After SSL Setup:

**V2 (Customer Value System):**
- HTTPS: `https://customervaluesystem.triadpartners.ai` ✅
- HTTP: `http://customervaluesystem.triadpartners.ai` (redirects to HTTPS)

**V1 (Customer Success AI) - Unchanged:**
- HTTPS: `https://customersuccessai.triadpartners.ai` ✅
- HTTP: `http://customersuccessai.triadpartners.ai` (redirects to HTTPS)

**Direct Access (No SSL):**
- V2: `http://3.84.178.121:3001`
- V1: `http://3.84.178.121:3000`

---

## 📊 Current Status

| Component | Status | URL |
|-----------|--------|-----|
| V2 Nginx Config | ✅ Complete | - |
| V2 SSL Script | ✅ Ready | `/home/ec2-user/setup-v2-ssl.sh` |
| DNS A Record | ⏳ Pending | customervaluesystem.triadpartners.ai → 3.84.178.121 |
| SSL Certificate | ⏳ Pending | Waiting for DNS |
| HTTPS Access | ⏳ Pending | Waiting for SSL |

---

## 🔧 Troubleshooting

### DNS Not Propagating?

Check DNS from different locations:
```bash
# Google DNS
dig @8.8.8.8 customervaluesystem.triadpartners.ai

# Cloudflare DNS
dig @1.1.1.1 customervaluesystem.triadpartners.ai

# Local
nslookup customervaluesystem.triadpartners.ai
```

### SSL Certificate Failed?

1. Verify port 80 is open:
   ```bash
   curl http://customervaluesystem.triadpartners.ai
   ```

2. Check nginx logs:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. Check certbot logs:
   ```bash
   sudo tail -f /var/log/letsencrypt/letsencrypt.log
   ```

### Test HTTP Access (Before SSL)

```bash
curl -H "Host: customervaluesystem.triadpartners.ai" http://3.84.178.121:3001/
```

---

## 🔐 Security Notes

- SSL certificate is free via Let's Encrypt
- Certificate auto-renews every 90 days
- HTTPS enforced via automatic redirect
- TLS 1.2 and 1.3 enabled
- Secure cipher suites configured

---

## 📝 Next Steps Summary

1. **YOU:** Add DNS A record (`customervaluesystem.triadpartners.ai` → `3.84.178.121`)
2. **WAIT:** 5-30 minutes for DNS propagation
3. **VERIFY:** `dig +short customervaluesystem.triadpartners.ai` returns `3.84.178.121`
4. **RUN:** `ssh ec2-user@3.84.178.121` then `./setup-v2-ssl.sh`
5. **DONE:** Access V2 at `https://customervaluesystem.triadpartners.ai` 🎉

---

## 📞 Support

If you encounter issues:
1. Check nginx status: `sudo systemctl status nginx`
2. Check V2 containers: `sudo docker ps | grep v2`
3. Review nginx config: `cat /etc/nginx/conf.d/customervaluesystem.conf`
4. Test SSL script: `./setup-v2-ssl.sh` (it will show detailed error messages)

---

**Created:** October 15, 2025  
**Status:** Awaiting DNS Configuration  
**Server:** EC2 `3.84.178.121`  
**Region:** `us-east-1`

