FROM python:3

# set a directory for the app
WORKDIR /usr/src/app

# copy all the files to the container
COPY . .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

ENV TEAM_NAME=CC_0102_0207_0811_1029
# tell the port number the container should expose
EXPOSE 80

# run the command
CMD ["python3", "./orchestrator.py"]
