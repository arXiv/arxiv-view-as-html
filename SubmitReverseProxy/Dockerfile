# syntax=docker/dockerfile:1

FROM python:3.10.5-buster

RUN apt-get update && apt-get install git
RUN python -m pip install --upgrade pip

########## INSTALL arxiv_auth ##########

WORKDIR /lib

ENV ARXIV_AUTH_COMMIT=6f5b3e7a61cceb35483badd3901056004ea3aa66
RUN rm -rf /lib/arxiv-auth
RUN git clone https://github.com/arXiv/arxiv-auth.git
WORKDIR /lib/arxiv-auth
RUN git reset --hard $ARXIV_AUTH_COMMIT

WORKDIR /lib/arxiv-auth/arxiv-auth
RUN python -m pip install .

########## INSTALL OTHER DEPENDENCIES ##########

RUN python -m pip install flask google-cloud-storage gunicorn google-cloud-logging flask_CORS

########## COPY SOURCE ##########

WORKDIR /source

COPY . .

########## RUN ##########
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]