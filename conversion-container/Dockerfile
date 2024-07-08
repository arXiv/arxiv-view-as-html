# syntax=docker/dockerfile:1

# This dockerfile is for doing full corpus convert.
# It needs to be run with the correct environment 
# variables and google application credentials

FROM ar5ivist-base

######## Install Python 3.11 ########

RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update -y
RUN apt install python3.11 python3-pip -y

######### Install Auth Proxy #########

WORKDIR /cloudsql

RUN apt-get -y install curl
RUN curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.0/cloud-sql-proxy.linux.amd64
RUN chmod +x cloud-sql-proxy

########## Everything Else ##########

WORKDIR /arxiv

RUN apt-get install -y python3.11-dev pkg-config default-libmysqlclient-dev build-essential

RUN python3.11 -m pip install --upgrade pip
RUN python3.11 -m pip install poetry 
RUN poetry config virtualenvs.create false

COPY . .
RUN apt remove python3-blinker -y
RUN poetry install

RUN mkdir /arxiv/extracted
RUN mkdir /arxiv/publish
RUN mkdir /arxiv/locks
RUN chmod +x wrapper.sh

CMD ["/arxiv/wrapper.sh"]
