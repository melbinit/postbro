# Backend Deployment Guide - Hetzner Server

## Quick Deployment Plan

### Phase 1: Server Setup (15 min)

```bash
# SSH into Hetzner server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y
apt install -y git curl wget ufw fail2ban

# Create deployment user (optional)
adduser deploy
usermod -aG sudo deploy
su - deploy

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

### Phase 2: Install Docker & Docker Compose (10 min)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version
```

---

### Phase 3: Clone Repository & Setup (10 min)

```bash
cd ~
git clone https://github.com/yourusername/postbro.git
cd postbro/postbro_backend

# Create .env file
nano .env
```

**Required .env variables:**
```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com,yourdomain.com

SUPABASE_DB_URL=postgresql://user:password@host:port/dbname
CLERK_SECRET_KEY=your-clerk-secret-key
CLERK_PUBLISHABLE_KEY=your-clerk-publishable-key
CLERK_FRONTEND_URL=https://yourdomain.com

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-key
SUPABASE_SECRET_KEY=your-secret-key

GEMINI_API_KEY=your-gemini-key
REDIS_URL=redis://postbro_redis:6379/0

CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
FRONTEND_URL=https://yourdomain.com

DODO_API_KEY=your-dodo-key
DODO_WEBHOOK_SECRET=your-webhook-secret
```

---

### Phase 4: Domain DNS Setup (10 min)

**In your domain registrar:**
```
Type: A
Name: api (or @ for root)
Value: your-hetzner-server-ip
TTL: 3600
```

**Verify DNS:**
```bash
dig api.yourdomain.com
```

---

### Phase 5: Install & Configure Nginx (15 min)

```bash
sudo apt install -y nginx
sudo nano /etc/nginx/sites-available/postbro-backend
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /var/www/postbro/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/postbro/media/;
        expires 7d;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/postbro-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Phase 6: SSL Certificate (10 min)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
# Follow prompts, choose redirect HTTP to HTTPS

# Test auto-renewal
sudo certbot renew --dry-run
```

---

### Phase 7: Update docker-compose.yml for Production

**Modify backend service:**
```yaml
backend:
  ports:
    - "127.0.0.1:8000:8000"  # Only localhost
  # Remove development volume: - .:/app
```

---

### Phase 8: Build & Start Services (10 min)

```bash
cd ~/postbro/postbro_backend
docker compose build
docker compose up -d

# Check logs
docker compose logs -f backend

# Verify health
curl http://localhost:8000/health/
curl https://api.yourdomain.com/health/
```

---

### Phase 9: Post-Deployment (10 min)

```bash
# Create superuser (if needed)
docker compose exec backend python manage.py createsuperuser

# Verify all services
docker compose ps

# Test API
curl https://api.yourdomain.com/health/
curl https://api.yourdomain.com/api/accounts/plans/
```

---

## Quick Reference Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f backend

# Restart backend
docker compose restart backend

# Update code
git pull
docker compose build backend
docker compose up -d backend

# Check status
docker compose ps

# Django shell
docker compose exec backend python manage.py shell
```

---

## Troubleshooting

**Can't access API:**
- Check firewall: `sudo ufw status`
- Check nginx: `sudo nginx -t && sudo systemctl status nginx`
- Check docker: `docker compose ps`
- Check logs: `docker compose logs backend`

**SSL certificate errors:**
- Verify DNS: `dig api.yourdomain.com`
- Check certbot: `sudo certbot certificates`
- Renew: `sudo certbot renew`

**Database connection errors:**
- Verify SUPABASE_DB_URL in .env
- Check network connectivity

---

## Security Checklist

- [ ] `DEBUG=False` in production .env
- [ ] `SECRET_KEY` set (no fallback)
- [ ] `ALLOWED_HOSTS` includes your domain
- [ ] Firewall configured (ufw)
- [ ] SSL certificate installed
- [ ] Nginx configured correctly
- [ ] Docker containers only expose to localhost
- [ ] Environment variables secured

---

**Total Estimated Time: ~90 minutes**

