# syntax=docker/dockerfile:1

FROM python:3.10.5-buster

########## LaTeXML ##########

ENV DEBIAN_FRONTEND=noninteractive
RUN set -ex && apt-get update -qq && apt-get install -qy --no-install-recommends tzdata
RUN set -ex && apt-get update -qq && apt-get install -qy \
  texlive \
  texlive-fonts-extra \
  texlive-lang-all \
  texlive-latex-extra \
  texlive-bibtex-extra \
  texlive-science \
  texlive-pictures \
  texlive-pstricks \
  texlive-publishers 

# latexml dependencies
RUN set -ex && apt-get update -qq && apt-get install -qy \
  build-essential \
  git \
  imagemagick \
  libarchive-zip-perl \
  libdb-dev \
  libfile-which-perl \
  libimage-magick-perl \
  libimage-size-perl \
  libio-string-perl \
  libjson-xs-perl \
  libparse-recdescent-perl \
  libtext-unidecode-perl \
  liburi-perl \
  libuuid-tiny-perl \
  libwww-perl \
  libxml-libxml-perl \
  libxml-libxslt-perl \
  libxml2 libxml2-dev \
  libxslt1-dev \
  libxslt1.1 \
  liblocal-lib-perl \
  make \
  perl-doc \
  cpanminus

# make sure perl paths are OK
RUN eval $(perl -I$HOME/perl5/lib -Mlocal::lib)
RUN echo 'eval "$(perl -I$HOME/perl5/lib/perl5 -Mlocal::lib)"' >> ~/.bashrc

# Collect the extended arxmliv-bindings files
ENV ARXMLIV_BINDINGS_COMMIT=cc02d684af394b3f413c825d752138a7fc0810d1
RUN rm -rf /opt/arxmliv-bindings
RUN git clone https://github.com/dginev/arxmliv-bindings /opt/arxmliv-bindings
WORKDIR /opt/arxmliv-bindings
RUN git reset --hard $ARXMLIV_BINDINGS_COMMIT

# Install LaTeXML, at a fixed commit, via cpanminus
RUN mkdir -p /opt/latexml
WORKDIR /opt/latexml
ENV LATEXML_COMMIT=2bfdaf26ab73aea95e210f044762dd4891855b47
RUN cpanm --notest --verbose https://github.com/brucemiller/LaTeXML/tarball/$LATEXML_COMMIT

# Enable imagemagick policy permissions for work with arXiv PDF/EPS files
RUN perl -pi.bak -e 's/rights="none" pattern="([XE]?PS\d?|PDF)"/rights="read|write" pattern="$1"/g' /etc/ImageMagick-6/policy.xml
# Extend imagemagick resource allowance to be able to create with high-quality images
RUN perl -pi.bak -e 's/policy domain="resource" name="width" value="(\w+)"/policy domain="resource" name="width" value="126KP"/' /etc/ImageMagick-6/policy.xml
RUN perl -pi.bak -e 's/policy domain="resource" name="height" value="(\w+)"/policy domain="resource" name="height" value="126KP"/' /etc/ImageMagick-6/policy.xml
RUN perl -pi.bak -e 's/policy domain="resource" name="area" value="(\w+)"/policy domain="resource" name="area" value="2GiB"/' /etc/ImageMagick-6/policy.xml
RUN perl -pi.bak -e 's/policy domain="resource" name="disk" value="(\w+)"/policy domain="resource" name="disk" value="8GiB"/' /etc/ImageMagick-6/policy.xml
RUN perl -pi.bak -e 's/policy domain="resource" name="memory" value="(\w+)"/policy domain="resource" name="memory" value="2GiB"/' /etc/ImageMagick-6/policy.xml
RUN perl -pi.bak -e 's/policy domain="resource" name="map" value="(\w+)"/policy domain="resource" name="map" value="2GiB"/' /etc/ImageMagick-6/policy.xml

ENV MAGICK_DISK_LIMIT=2GiB
ENV MAGICK_MEMORY_LIMIT=512MiB
ENV MAGICK_MAP_LIMIT=1GiB
ENV MAGICK_TIME_LIMIT=900
ENV MAGICK_TMPDIR=/dev/shm
ENV TMPDIR=/dev/shm

########## Everything Else ##########

WORKDIR /arxiv

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install flask google-cloud-storage gunicorn Flask-SQLAlchemy pytz pg8000 google-cloud-logging bs4 filelock

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "600", "entry_point:app"]
