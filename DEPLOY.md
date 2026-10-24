# 部署指南 — XMUM 校园市集（Streamlit）

## 线上环境

| 项 | 值 |
| --- | --- |
| 服务器 | Ubuntu 24.04 LTS（美国 VPS，4 核 / 2.4G 内存 / 50G 磁盘） |
| 应用目录 | `/var/www/xmum-market` |
| 运行用户 | `app`（系统用户，无登录 shell） |
| 服务 | systemd `xmum-market`（`streamlit run app.py`，监听 `127.0.0.1:8501`） |
| 反向代理 | Nginx（80/443 → `127.0.0.1:8501`，含 WebSocket 升级） |
| 演示地址 | `https://cummy.top` |

## systemd 单元

`/etc/systemd/system/xmum-market.service`：

```ini
[Unit]
Description=XMUM campus market (Streamlit)
After=network.target

[Service]
Type=simple
User=app
Group=app
WorkingDirectory=/var/www/xmum-market
EnvironmentFile=/etc/xmum-market.env
Environment=HOME=/var/www/xmum-market
Environment=PYTHONUNBUFFERED=1
ExecStart=/var/www/xmum-market/.venv/bin/streamlit run 首页.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

## Nginx 站点

`/etc/nginx/sites-available/xmum-market`：

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
```

## 更新部署

```bash
# 本地：打包应用目录（排除缓存）
tar -czf xmum-market.tgz -C 403-forbbiden-qiusiqian --exclude=__pycache__ .

# 上传并解压
scp xmum-market.tgz root@<vps>:deploy/
ssh root@<vps>
tar -xzf deploy/xmum-market.tgz -C /var/www/xmum-market
chown -R app:app /var/www/xmum-market
systemctl restart xmum-market
```

依赖有变化时先执行：

```bash
runuser -u app -- /var/www/xmum-market/.venv/bin/pip install -r /var/www/xmum-market/requirements.txt
```

## HTTPS（cummy.top）

1. DNS 添加 A 记录（Cloudflare 代理需改为 DNS only）：
   - `cummy.top` → VPS IP
   - `www.cummy.top` → VPS IP（可选）
2. 安装并签发证书：

   ```bash
   apt-get install -y certbot python3-certbot-nginx
   certbot --nginx -d cummy.top -d www.cummy.top --redirect --agree-tos -m <email>
   ```

3. 自动续期检查：`systemctl status certbot.timer`、`certbot renew --dry-run`

## 安全基线（已配置）

- **SSH**：仅密钥登录；禁用密码登录；root 仅密钥（`PermitRootLogin prohibit-password`）；`MaxAuthTries 3`；关闭 X11 与 TCP 转发
- **fail2ban**：`sshd` jail（3 次失败封禁 2 小时）
- **防火墙**：ufw 仅放行 22 / 80 / 443；Streamlit 8501 只监听 `127.0.0.1`
- **自动更新**：`unattended-upgrades` 已启用
- **Nginx**：`server_tokens off`
- **应用沙箱**：非 root 用户 + systemd `NoNewPrivileges` / `ProtectSystem=full` / `ProtectHome` / `PrivateTmp`

## 邮箱验证

线上使用真实 SMTP 发信。密钥放在 `/etc/xmum-market.env`（权限 600，root 所有，**不要提交到 git**）：

```ini
EMAIL_VERIFY_MODE=smtp
SCHOOL_EMAIL_DOMAIN=xmu.edu.my
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USER=<QQ 邮箱>
SMTP_PASSWORD=<QQ 邮箱 SMTP 授权码>
SMTP_FROM=<QQ 邮箱>
```

systemd 通过 `EnvironmentFile=/etc/xmum-market.env` 加载。QQ 邮箱需在设置中开启 SMTP，并使用授权码（不是登录密码）。

如需现场无邮箱演示，可临时把 `EMAIL_VERIFY_MODE` 改为 `dev`（验证码显示在页面上），演示结束后切回 `smtp` 并重启服务。
