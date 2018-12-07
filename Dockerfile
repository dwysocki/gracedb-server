FROM ligo/base:stretch
LABEL name="LIGO GraceDB Django application" \
      maintainer="tanner.prestegard@ligo.org" \
      date="20181206"
ARG SETTINGS_MODULE="config.settings.container"
WORKDIR /app
ADD . /app/gracedb_project

# Volumes
VOLUME /app/logs /app/project_data

RUN apt-get update
RUN apt-get install --assume-yes gcc \
        git \
        libmariadbclient-dev \
        libldap2-dev \
        libsasl2-dev \
        libxml2-dev \
        libsqlite3-dev \
        mariadb-client \
        python2.7 \
        python-glue \
        python-pip \
        python-voeventlib

# Install npm and bower
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get update && \
  apt-get install nodejs && \
  apt-get clean && \
  npm install -g bower

# Set up bower components
WORKDIR /app/gracedb_project
RUN bower install --allow-root

# Install Python packages
RUN pip install -r requirements.txt

# Give pip-installed packages priority over distribution packages
ENV PYTHONPATH /usr/local/lib/python2.7/dist-packages:$PYTHONPATH
ENV VIRTUAL_ENV dummy

# Collect static components. First step: set settings module and
# fake a few other required environment variables
ENV DJANGO_SETTINGS_MODULE ${SETTINGS_MODULE}
ENV DJANGO_DB_PASSWORD fake_password
ENV DJANGO_SECRET_KEY fake_key
ENV DJANGO_PRIMARY_FQDN fake_fqdn
RUN python manage.py collectstatic --noinput

# Unset faked environment variables
RUN unset DJANGO_SETTINGS_MODULE \
    DJANGO_DB_PASSWORD \
    DJANGO_SECRET_KEY \
    DJANGO_PRIMARY_FQDN

# Expose port and run Gunicorn
EXPOSE 8000
CMD ["gunicorn", "--reload", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
