# syntax=docker/dockerfile:1

FROM python:3.11.8-bookworm

RUN apt-get update -y && apt-get install git -y
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

RUN python -m pip install flask==2.2.5 werkzeug==2.3.7 pydantic==1.10.13 google-cloud-pubsub google-cloud-storage gunicorn google-cloud-logging flask_CORS pg8000

########## COPY PROXY APP SOURCE ##########

RUN rm -rf /source/ReverseProxy
WORKDIR /source

COPY . .

########## GET BROWSE TEMPLATE RESOURCES ##########

WORKDIR /lib
ENV ARXIV_BROWSE_COMMIT=7d404bbdc3571b33abd00b572cd7009570186d38
RUN rm -rf /lib/arxiv-browse
RUN git clone https://github.com/arXiv/arxiv-browse.git
WORKDIR /lib/arxiv-browse
RUN git checkout $ARXIV_BROWSE_COMMIT
# We only need the templates and transformation pipeline here.
RUN mkdir -p /source/ReverseProxy/templates/dissemination
RUN cp -r /lib/arxiv-browse/browse/templates/dissemination/article_scaffold \
    /source/ReverseProxy/templates/dissemination/
RUN cp -r /lib/arxiv-browse/browse/services/html_processing/scaffold.py \
    /source/ReverseProxy/

########## RUN ##########
WORKDIR /source

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]