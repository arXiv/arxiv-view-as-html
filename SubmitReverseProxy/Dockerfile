# syntax=docker/dockerfile:1

FROM python:3.11.8-bookworm

RUN apt-get update -y && apt-get install git -y
RUN python -m pip install --upgrade pip

########## INSTALL OTHER DEPENDENCIES ##########

RUN python -m pip install flask==2.2.5 werkzeug==2.3.7 google-cloud-pubsub google-cloud-storage gunicorn google-cloud-logging flask_CORS pg8000

########## INSTALL ARXIV BASE AND GET BROWSE RESOURCES ##########

WORKDIR /lib
ENV ARXIV_BASE_COMMIT=dec16c16f78a4d45e0f93461486a3f541ba237a3
RUN rm -rf /lib/arxiv-base
RUN git clone https://github.com/arXiv/arxiv-base.git
WORKDIR /lib/arxiv-base
RUN git checkout $ARXIV_BASE_COMMIT
RUN python -m pip install .

WORKDIR /lib
ENV ARXIV_BROWSE_COMMIT=406f35e0000e6cee8ef82d09bcb576531f7c00d9
RUN rm -rf /lib/arxiv-browse
RUN git clone https://github.com/arXiv/arxiv-browse.git
WORKDIR /lib/arxiv-browse
RUN git checkout $ARXIV_BROWSE_COMMIT
# We only need the templates and transformation pipeline here.
RUN mkdir -p /source/templates/
RUN cp -r /lib/arxiv-browse/browse/templates/dissemination/article_scaffold \
    /source/templates/

########## COPY PROXY APP SOURCE ##########

WORKDIR /source

COPY . .

RUN cp -r /lib/arxiv-browse/browse/services/html_processing/scaffold.py \
    /source/ReverseProxy/

########## RUN ##########
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]