FROM ubuntu:20.04

# set a directory for the app
WORKDIR /app

# copy all the files to the container
COPY . .

#install jdk
RUN apt-get update -y

RUN apt-get -y install libgl1-mesa-glx

RUN apt-get -y install libglib2.0-0

RUN apt-get install -y python3-pip

RUN apt-get -y install curl

#install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# run the command
CMD ["python3", "belloga-img-preprocessing.py"]
