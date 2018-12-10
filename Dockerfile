FROM ligo/base:stretch
LABEL name="LIGO GraceDB Django application" \
      maintainer="tanner.prestegard@ligo.org" \
      date="20180215"
WORKDIR /app
ADD . /app/gracedb_project

# Volumes
VOLUME /app/logs /app/project_data

RUN apt-get update
RUN apt-get install --assume-yes gcc \
        python2.7 \
        python-pip \
        mariadb-client \
        libmariadbclient-dev \
        libldap2-dev \
        libsasl2-dev \
        libxml2-dev \
        libsqlite3-dev \
        python-glue \
        python-voeventlib

# Install npm, bower, bower_components
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get update && \
  apt-get install nodejs && \
  apt-get clean && \
  npm install -g bower

# Install Python packages
RUN pip install -r ./gracedb_project/requirements.txt
EXPOSE 8000

# Give pip-installed packages priority over distribution packages
ENV PYTHONPATH /usr/local/lib/python2.7/dist-packages:$PYTHONPATH
ENV VIRTUAL_ENV dummy

# Set WORKDIR and run Gunicorn
WORKDIR /app/gracedb_project
#RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
