#!/bin/bash

# 安装依赖
python3 -m pip install -r requirements.txt

# 获取SSL证书（首次运行时需要）
sudo certbot certonly --nginx -d h5.studyreport --agree-tos --email your-email@example.com

# 配置Nginx
sudo cp nginx.conf /etc/nginx/sites-available/h5.studyreport
sudo ln -sf /etc/nginx/sites-available/h5.studyreport /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# 启动Gunicorn
gunicorn --bind 127.0.0.1:8000 --workers 4 --threads 4 wsgi:app
