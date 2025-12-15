# Nginx with UserService Deployment Guide

## What is Nginx?

Nginx is a high-performance reverse proxy server that:
- ✅ Forwards requests to your FastAPI application
- ✅ Handles SSL/HTTPS certificates
- ✅ Provides caching and compression
- ✅ Rate limiting and security headers
- ✅ Better performance and stability

## Files Included

- `docker-compose.nginx.yml` - Docker Compose with Nginx + UserService
- `nginx.conf` - Main Nginx configuration
- `nginx/conf.d/default.conf` - Site configuration

## Quick Deploy with Nginx

### Option 1: HTTP Only (No HTTPS)

```bash
# Connect to EC2
aws ssm start-session --target i-0b2393deedd3748d3

# In SSM session:
cd /home/ubuntu/userservice

# Deploy with Nginx
docker-compose -f docker-compose.nginx.yml build
docker-compose -f docker-compose.nginx.yml up -d

# Check status
docker ps
docker-compose -f docker-compose.nginx.yml logs -f nginx
```

**Access in browser:**
```
http://<YOUR_EC2_PUBLIC_IP>/docs
http://<YOUR_EC2_PUBLIC_IP>/health
```

### Option 2: HTTP + HTTPS (With Let's Encrypt)

#### Step 1: Deploy HTTP first
```bash
cd /home/ubuntu/userservice
docker-compose -f docker-compose.nginx.yml up -d
```

#### Step 2: Get SSL Certificate with Certbot
```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (replace your-domain.com with your actual domain)
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates to nginx folder
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /home/ubuntu/userservice/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /home/ubuntu/userservice/nginx/ssl/key.pem

# Fix permissions
sudo chown -R $(whoami):$(whoami) /home/ubuntu/userservice/nginx/ssl/
```

#### Step 3: Enable HTTPS in Nginx config
```bash
# Edit the nginx configuration
nano /home/ubuntu/userservice/nginx/conf.d/default.conf

# Uncomment the HTTPS section and HTTP redirect
# Update "your-domain.com" to your actual domain
```

#### Step 4: Restart Nginx
```bash
docker-compose -f docker-compose.nginx.yml restart nginx
```

**Access with HTTPS:**
```
https://your-domain.com/docs
https://your-domain.com/health
```

---

## Configuration Files Explained

### docker-compose.nginx.yml

```yaml
services:
  userservice:     # Your FastAPI app (port 8001 internal)
    ...

  nginx:           # Reverse proxy (port 80/443)
    image: nginx:1.24-alpine
    ports:
      - "80:80"     # HTTP
      - "443:443"   # HTTPS (optional)
```

### nginx.conf

- `worker_processes auto` - Auto-detect CPU cores
- `client_max_body_size 20M` - Max upload size
- `gzip on` - Enable compression
- Rate limiting zones (general & api)

### default.conf

**HTTP Server Block:**
- Proxy to userservice:8001
- Security headers (X-Frame-Options, CSP, etc.)
- Rate limiting (10 req/s general, 100 req/s for /api/)
- Health check endpoint (no rate limit)

**HTTPS Server Block (commented out):**
- SSL certificates from Let's Encrypt
- Redirect HTTP to HTTPS
- HSTS header for browser security

---

## Common Tasks

### View Nginx Logs
```bash
docker-compose -f docker-compose.nginx.yml logs -f nginx
```

### View UserService Logs
```bash
docker-compose -f docker-compose.nginx.yml logs -f userservice
```

### Restart Nginx (After Config Changes)
```bash
docker-compose -f docker-compose.nginx.yml restart nginx
```

### Stop All Services
```bash
docker-compose -f docker-compose.nginx.yml down
```

### Test Nginx Configuration
```bash
docker exec -it nginx-reverse-proxy nginx -t
```

---

## Security Features

✅ Rate limiting (prevents DDoS)
✅ Security headers (X-Frame-Options, CSP, etc.)
✅ HTTPS/SSL support (Let's Encrypt)
✅ Gzip compression (reduces bandwidth)
✅ Proxy buffer limits
✅ Request timeout limits

---

## Performance Optimizations

✅ Gzip compression enabled
✅ Keepalive connections
✅ Proxy buffering
✅ Worker process auto-tuning
✅ Cache support

---

## Port Mapping

| Service | Internal | External |
|---------|----------|----------|
| Nginx | - | 80 (HTTP), 443 (HTTPS) |
| UserService | 8001 | Not exposed (behind Nginx) |

---

## Security Group Configuration

When using Nginx, your Security Group should allow:

- **Port 80** (HTTP) - Source: 0.0.0.0/0
- **Port 443** (HTTPS) - Source: 0.0.0.0/0 (if using HTTPS)
- **Port 8001** - NOT exposed (optional for internal only)

---

## Troubleshooting

### Nginx won't start
```bash
docker logs nginx-reverse-proxy
docker exec -it nginx-reverse-proxy nginx -t
```

### Can't reach the service
```bash
# Check Nginx can reach UserService
docker exec -it nginx-reverse-proxy curl http://user-service:8001/health

# Check if UserService is running
docker ps | grep user-service
```

### SSL Certificate issues
```bash
# Check certificate files exist
ls -la /home/ubuntu/userservice/nginx/ssl/

# Check Nginx logs
docker-compose -f docker-compose.nginx.yml logs nginx
```

### Rate limit errors (429)
Edit `nginx/conf.d/default.conf` and increase rate limits:
```
limit_req zone=general burst=50 nodelay;  # Increase from 20
limit_req zone=api burst=100 nodelay;     # Increase from 50
```

---

## Comparison: With vs Without Nginx

| Feature | Direct (Port 8001) | With Nginx |
|---------|-------------------|-----------|
| HTTP/HTTPS | HTTP only | Both |
| Compression | No | Yes |
| Rate limiting | No | Yes |
| Security headers | No | Yes |
| Caching | No | Yes |
| Multiple apps | No | Yes |
| Performance | Good | Better |

---

## Next Steps

1. **Choose deployment method:**
   - Simple HTTP: Use `docker-compose.nginx.yml`
   - With HTTPS: Use `docker-compose.nginx.yml` + Let's Encrypt

2. **Deploy:**
   ```bash
   docker-compose -f docker-compose.nginx.yml up -d
   ```

3. **Configure Security Group:**
   - Port 80 (and 443 if HTTPS)

4. **Test:**
   ```bash
   http://<YOUR_IP>/docs
   ```

---

**Need HTTPS?** Follow the "HTTP + HTTPS" section above.

**Want to keep it simple?** Use HTTP with port 80 - it's easier to set up.
