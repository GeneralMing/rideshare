# RideShare Cabs BackEnd

The aim of this project is to build a few REST API's for the RideShare Cabs app and to provide cloud architecture in implementing them

## Getting Started

These instructions will get you a copy of the project up and running for development and testing purposes.

### Prerequisites

What things you need to install the software and how to install them

```
An AWS account with atleast basic privileges.
```

### Installing

A step by step series of examples that tell you how to get a development env running

Setting up AWS

```
Create three virtual machines on AWS named Users, Rides and Orchestrator.
All three virtual machines need to run on Ubuntu 18.04.
All three virtual machines need to have their ports 8080 and 80 exposed and need to be ssh secured with 8GB of RAM and 12GB of disk space.
Associate Elastic IP addresses for all three VM's
Create a load balancer for http requests in AWS with the following rules
 * All URLS with /api/v1/users to be forwarded to the Users VM
 * All URLS with /api/v1/rides to be forwarded to the Rides VM
 * All URLS the rest of the URLS to be forwarded to the Orchestrator VM
You will need to create custom Target Groups for load balancing
Start all Three machines and login to them
```

Installing Nginx

```
Run the command "sudo apt install nginx" on all three VM's
After installation, navigate to /etc/nginx/sites-enabled
Edit the existing "default" file by adding a port forwarding mechanism from the port 80 to 8080.
This implements a reverse proxy for our containers.
For more details on port forwarding see
```
(https://www.digitalocean.com/community/questions/how-to-forward-traffic-from-another-port-to-port-80)


Extraction of files

```
In the "Users VM" folder, inside users/users.py, replace all occurrences of "Mark-1-901447356.us-east-1.elb.amazonaws.com" with your load balancer URL
In the "Rides VM" folder, inside ridess/rides.py, replace all occurrences of "Mark-1-901447356.us-east-1.elb.amazonaws.com" with your load balancer URL
In the "Orchestrator VM" folder, inside orchestrator/orchestrator.py, replace all occurrences of "Mark-1-901447356.us-east-1.elb.amazonaws.com" with your load balancer URL
Extract the folder contents given into their respective VMS
All three VM's have a file called launch.sh
Execute all three and wait for a minute or two
```
##Testing

Manually

```
For testing the given API's calls can be made to manually verify the working
For the read and write counts for the conatiner, requests can be sent to the Elastic IP of the containers for verification
```
## Built With

* [Flask](https://flask.palletsprojects.com/en/1.1.x/) - The web framework used
* [Nginx](https://www.nginx.com/) - Web Server used
* [RabbitMQ](https://www.rabbitmq.com/) - Used to handle Queuing
* [Docker](https://www.docker.com/) - Used to handle Sandboxing and separation of services
* [Pika](https://pika.readthedocs.io/en/stable/) - Queue Interface used
* [Docker Sdk](https://docker-py.readthedocs.io/en/stable/) - Used to interact with the sandbox environment
* [Zookeeper](https://zookeeper.apache.org/) - Used to handle workers and sacling
* [SQLite3](https://www.sqlite.org/) - Used to handle the database
* [Kazoo](https://kazoo.readthedocs.io/) - Used to interface with the Zookeeper
* [AWS](https://aws.amazon.com/) - Used to host the application

## Contributing

I'm always available on Discord going by the ID General Ming#7573 . Free free to review my code and send edits of my code to me. I will add you as a contributor to this project.

## Authors

* **Advaith K Vasisht**
* **Rohan Kamath**
* **Abhiram G K**
* **Yamini Cherukuri**


## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE.md](LICENSE.md) file for details