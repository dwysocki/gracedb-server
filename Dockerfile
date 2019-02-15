FROM ligo/base:stretch
LABEL name="LIGO GraceDB Django application" \
      maintainer="tanner.prestegard@ligo.org" \
      date="20181206"
ARG SETTINGS_MODULE="config.settings.container.dev"

COPY docker/SWITCHaai-swdistrib.gpg /etc/apt/trusted.gpg.d
RUN echo 'deb http://pkg.switch.ch/switchaai/debian stretch main' > /etc/apt/sources.list.d/shibboleth.list
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash -
RUN apt-get update && \
    apt-get install --install-recommends --assume-yes \
        apache2 \
        gcc \
        git \
        libapache2-mod-xsendfile \
        libmariadbclient-dev \
        libldap2-dev \
        libsasl2-dev \
        libxml2-dev \
        libsqlite3-dev \
        mariadb-client \
        nodejs \
        osg-ca-certs \
        python2.7 \
        python2.7-dev \
        python-glue \
        python-pip \
        python-voeventlib \
        procps \
        shibboleth \
        supervisor \
        vim && \
    apt-get clean && \
    npm install -g bower

COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/supervisord-apache2.conf /etc/supervisor/conf.d/apache2.conf
COPY docker/supervisord-shibd.conf /etc/supervisor/conf.d/shibd.conf
COPY docker/shibboleth-ds /etc/shibboleth-ds
COPY docker/apache-config /etc/apache2/sites-available/gracedb.conf
COPY docker/login.ligo.org.cert.LIGOCA.pem /etc/shibboleth/login.ligo.org.cert.LIGOCA.pem
COPY docker/inc-md-cert.pem /etc/shibboleth/inc-md-cert.pem
COPY docker/check_shibboleth_status /usr/local/bin/check_shibboleth_status

RUN a2dissite 000-default.conf && \
    a2ensite gracedb.conf && \
    a2enmod headers proxy proxy_http rewrite xsendfile

# this line is unfortunate because "." updates for nearly any change to the
# repository and therefore docker build rarely caches the steps below
ADD . /app/gracedb_project

# install gracedb application itself
WORKDIR /app/gracedb_project
RUN bower install --allow-root
RUN pip install --upgrade setuptools wheel && \
    pip install -r requirements.txt

# Give pip-installed packages priority over distribution packages
ENV PYTHONPATH /usr/local/lib/python2.7/dist-packages:$PYTHONPATH
ENV ENABLE_SHIBD false
ENV VIRTUAL_ENV dummy

# Expose port and run Gunicorn
EXPOSE 8000

# Generate documentation
WORKDIR /app/gracedb_project/docs/user_docs
RUN sphinx-build -b html source build
WORKDIR /app/gracedb_project/docs/admin_docs
RUN sphinx-build -b html source build

RUN mkdir /app/logs /app/project_data

WORKDIR /app/gracedb_project
RUN DJANGO_SETTINGS_MODULE=${SETTINGS_MODULE} \
    DJANGO_DB_NAME=fake_name \
    DJANGO_DB_PASSWORD=fake_password \
    DJANGO_SECRET_KEY=fake_key \
    DJANGO_PRIMARY_FQDN=fake_fqdn \
    LVALERT_USER=fake_user \
    LVALERT_PASSWORD=fake_password \
    LVALERT_SERVER=fake_server \
    LVALERT_OVERSEER_PORT=2 \
    python manage.py collectstatic --noinput

RUN rm -rf /app/logs/* /app/project_data/*

RUN useradd -M -u 50001 -g www-data -s /bin/false gracedb

RUN chown gracedb:www-data /app/logs /app/project_data && \
    chmod 0750 /app/logs /app/project_data

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
