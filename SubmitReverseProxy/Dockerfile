# syntax=docker/dockerfile:1

FROM python:3.11.8-bookworm

RUN apt-get update -y && apt-get install git -y
RUN python -m pip install --upgrade pip

########## INSTALL arxiv_auth ##########

WORKDIR /lib

# base needs to be new enough to handle scaffold use of metadata,
# but old enough to not conflict with arxiv-auth. 
# Messy. ideally we move everything to pydantic2 compat.
# And even more ideally we would use the 2.0 submission system without tricks.

WORKDIR /lib
ENV ARXIV_BASE_COMMIT=a1fed38fcae2d8630acc9aa8b53c2f4a1776f5c5
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
########## INSTALL OTHER DEPENDENCIES ##########

RUN python -m pip install flask==2.2.5 werkzeug==2.3.7 pydantic==2.* google-cloud-pubsub google-cloud-storage gunicorn google-cloud-logging flask_CORS pg8000
########## COPY SOURCE ##########

WORKDIR /source

COPY . .

RUN cp -r /lib/arxiv-browse/browse/services/html_processing/scaffold.py \
    /source/ReverseProxy/

########## RUN ##########
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]