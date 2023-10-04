# syntax=docker/dockerfile:1

FROM python:3.10.5-buster

RUN apt-get update && apt-get install git
RUN python -m pip install --upgrade pip

########## INSTALL DEPENDENCIES ##########

RUN python -m pip install flask google-cloud-storage gunicorn google-cloud-logging flask_CORS pg8000

########## COPY SOURCE ##########

WORKDIR /

COPY . .

########## RUN ##########
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]