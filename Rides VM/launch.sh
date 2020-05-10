#!/bin/bash
sudo ufw allow 5000
alias python='python3'
cd ~/rides
apt install docker-compose -y
docker container prune -f
docker build -t rides .
docker run  --name rides -p 8080:80 rides

