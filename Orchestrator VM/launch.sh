#!/bin/bash
sudo ufw allow 5000
alias python='python3'
cd ~/orchestrator
apt install docker-compose -y
docker network create --driver=bridge --subnet=10.0.2.0/16 --gateway=10.0.2.1 cry_cloud
docker pull rabbitmq
docker pull zookeeper
docker run -d --net cry_cloud --ip 10.0.2.3 --name zootopia zookeeper
docker run -d --net cry_cloud --ip 10.0.2.2 --name rabbitmq rabbitmq
docker container prune -f
docker build -t orchestrator .
cd ~/worker
docker build -t worker .
docker run --net cry_cloud --ip 10.0.2.4 -p 8080:80 --name orchestrator -v /var/run/docker.sock:/var/run/docker.sock orchestrator

