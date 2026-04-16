# Deployment Guide — SSAI POC

This guide covers deploying the SSAI FastAPI server on a Linux server (Ubuntu/Debian) using **Supervisor** to keep the process running.

---

## 1. Prerequisites

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg supervisor git
```

Verify FFmpeg has libx264:

```bash
ffmpeg -version | grep libx264
```

Verify Python:

```bash
python3 --version   # must be 3.11+
```

---

## 2. Clone the Repository

```bash
git clone <your-repo-url> /srv/ssai
cd /srv/ssai
```

---

## 3. Create the Virtual Environment

```bash
cd /srv/ssai/ssai-poc
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Prepare Live Stream Storage

The stitcher reads HLS playlists from a directory you configure via `LIVE_DIR`.

If you are running FFmpeg on the same server, create the output directory:

```bash
mkdir -p /srv/ssai/ffmpeg-outputs
```

Run FFmpeg to generate live HLS (adjust the RTMP source URL):

```bash
ffmpeg -y -i rtmp://localhost:1935/live/livestream \
  -map 0:v:0 -map 0:a:0 -s:v:0 426x240   -c:v:0 libx264 -b:v:0 192k  -b:a:0 72k \
  -map 0:v:0 -map 0:a:0 -s:v:1 854x480   -c:v:1 libx264 -b:v:1 500k  -b:a:1 128k \
  -map 0:v:0 -map 0:a:0 -s:v:2 1280x720  -c:v:2 libx264 -b:v:2 1000k -b:a:2 128k \
  -c:a aac -ar 44100 -ac 2 \
  -preset ultrafast -hls_list_size 0 -f hls -tune zerolatency \
  -hls_playlist_type event -hls_time 6 -g 48 -keyint_min 48 -sc_threshold 0 \
  -hls_flags independent_segments+program_date_time \
  -r 24 \
  -master_pl_name "video.m3u8" \
  -var_stream_map "v:0,a:0,name:240p v:1,a:1,name:480p v:2,a:2,name:720p" \
  /srv/ssai/ffmpeg-outputs/video-%v.m3u8
```

> You can also run FFmpeg as a separate Supervisor program (see optional section at the end).

---

## 5. Verify the Application Starts Manually

Before handing off to Supervisor, confirm the app runs cleanly:

```bash
cd /srv/ssai/ssai-poc

LIVE_DIR=/srv/ssai/ffmpeg-outputs \
  /srv/ssai/ssai-poc/.venv/bin/python -m uvicorn main:app \
  --host 0.0.0.0 --port 8000

# Should print: INFO: Application startup complete.
# Visit http://localhost:8000/health => {"status":"ok"}
# Ctrl+C to stop before continuing to next step.
```

---

## 6. Configure Supervisor

Create the Supervisor config file:

```bash
sudo nano /etc/supervisor/conf.d/ssai.conf
```

Paste the following (update paths if you installed elsewhere):

```ini
[program:ssai]
command=/srv/ssai/ssai-poc/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
directory=/srv/ssai/ssai-poc
user=www-data
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
redirect_stderr=true
stdout_logfile=/var/log/ssai/app.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=LIVE_DIR="/srv/ssai/ffmpeg-outputs"
```

Create the log directory:

```bash
sudo mkdir -p /var/log/ssai
sudo chown www-data:www-data /var/log/ssai
```

> If you are not using `www-data`, replace `user=www-data` with your own user (`whoami`).

---

## 7. Start the Service

Load and start the Supervisor program:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ssai
```

Check status:

```bash
sudo supervisorctl status ssai
# Expected: ssai    RUNNING   pid 12345, uptime 0:00:05
```

Check the logs:

```bash
sudo tail -f /var/log/ssai/app.log
```

---

## 8. Verify It Is Running

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"SSAI POC","version":"..."}
```

Open the UI in a browser:

```
http://<your-server-ip>:8000/
```

You should see the **SSAI Control Room** dashboard.

---

## 9. Common Supervisor Commands

| Command | Purpose |
|---------|---------|
| `sudo supervisorctl status` | Show all programs and their states |
| `sudo supervisorctl restart ssai` | Restart after a code change |
| `sudo supervisorctl stop ssai` | Stop the service |
| `sudo supervisorctl tail -f ssai` | Live log output |

After any code change:

```bash
cd /srv/ssai
git pull
sudo supervisorctl restart ssai
```

---

## 10. Optional: Firewall (UFW)

If you want teammates on the same network to reach the server:

```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

Or proxy behind Nginx on port 80/443 (recommended for production).

---

## 11. Optional: Nginx Reverse Proxy

Install Nginx:

```bash
sudo apt-get install -y nginx
```

Create a site config:

```bash
sudo nano /etc/nginx/sites-available/ssai
```

```nginx
server {
    listen 80;
    server_name your-server.example.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

Enable site and reload:

```bash
sudo ln -s /etc/nginx/sites-available/ssai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 12. Optional: Run FFmpeg Under Supervisor

If FFmpeg is also running on the same server, you can manage it alongside the stitcher:

```ini
[program:ssai-ffmpeg]
command=ffmpeg -y -i rtmp://localhost:1935/live/livestream \
  -map 0:v:0 -map 0:a:0 -s:v:0 426x240   -c:v:0 libx264 -b:v:0 192k \
  -map 0:v:0 -map 0:a:0 -s:v:1 854x480   -c:v:1 libx264 -b:v:1 500k \
  -map 0:v:0 -map 0:a:0 -s:v:2 1280x720  -c:v:2 libx264 -b:v:2 1000k \
  -c:a aac -ar 44100 -ac 2 -preset ultrafast -hls_list_size 0 -f hls \
  -hls_playlist_type event -hls_time 6 -g 48 -keyint_min 48 -sc_threshold 0 \
  -hls_flags independent_segments+program_date_time -r 24 \
  -master_pl_name "video.m3u8" \
  -var_stream_map "v:0,a:0,name:240p v:1,a:1,name:480p v:2,a:2,name:720p" \
  /srv/ssai/ffmpeg-outputs/video-%v.m3u8
directory=/srv/ssai
user=www-data
autostart=true
autorestart=true
startsecs=3
redirect_stderr=true
stdout_logfile=/var/log/ssai/ffmpeg.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=3
```

Then reload Supervisor:

```bash
sudo supervisorctl reread && sudo supervisorctl update
sudo supervisorctl start ssai-ffmpeg
```

---

## 13. Troubleshooting

### Service won't start

```bash
sudo supervisorctl tail ssai stderr
sudo tail -50 /var/log/ssai/app.log
```

### Port 8000 already in use

```bash
sudo lsof -i :8000
sudo supervisorctl stop ssai
# kill conflicting process, then:
sudo supervisorctl start ssai
```

### LIVE_DIR has no manifests

```bash
ls /srv/ssai/ffmpeg-outputs/*.m3u8
# If empty, FFmpeg is not writing there yet — check ssai-ffmpeg logs
```

### Permission denied writing to storage/ads

```bash
sudo chown -R www-data:www-data /srv/ssai/ssai-poc/storage
```
