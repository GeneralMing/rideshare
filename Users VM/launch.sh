#!/bin/bash
sudo ufw allow 5000
alias python='python3'
cd ~/users
apt install docker-compose -y
docker container prune -f
docker build -t users .
docker run  --name users -p 8080:80 users

