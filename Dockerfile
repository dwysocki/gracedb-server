FROM ligo/base:stretch
LABEL name="LIGO GraceDB Django application" \
      maintainer="tanner.prestegard@ligo.org" \
      date="20190920"
ARG SETTINGS_MODULE="config.settings.container.dev"

COPY docker/SWITCHaai-swdistrib.gpg /etc/apt/trusted.gpg.d
COPY docker/backports.pref /etc/apt/preferences.d
RUN echo 'deb http://pkg.switch.ch/switchaai/debian stretch main' > /etc/apt/sources.list.d/shibboleth.list
RUN echo 'deb http://deb.debian.org/debian stretch-backports main' > /etc/apt/sources.list.d/backports.list
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
        ligo-ca-certs \
        mariadb-client \
        nodejs \
        osg-ca-certs \
        python3.5 \
        python3.5-dev \
        python3-libxml2 \
        python3-pip \
        procps \
        shibboleth \
        supervisor \
        libssl-dev \
        swig \
        vim && \
    apt-get clean && \
    npm install -g bower

COPY docker/entrypoint /usr/local/bin/entrypoint
COPY docker/cleanup /usr/local/bin/cleanup
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/supervisord-apache2.conf /etc/supervisor/conf.d/apache2.conf
COPY docker/supervisord-lvalert-overseer.conf /etc/supervisor/conf.d/overseer.conf
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
RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools wheel && \
    pip3 install -r requirements.txt

# Give pip-installed packages priority over distribution packages
ENV PYTHONPATH /usr/local/lib/python3.5/dist-packages:$PYTHONPATH
ENV ENABLE_SHIBD false
ENV ENABLE_OVERSEER true
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
    DJANGO_DB_USER=fake_user \
    DJANGO_DB_PASSWORD=fake_password \
    DJANGO_SECRET_KEY=fake_key \
    DJANGO_PRIMARY_FQDN=fake_fqdn \
    DJANGO_ALERT_EMAIL_FROM=fake_email \
    LVALERT_USER=fake_user \
    LVALERT_PASSWORD=fake_password \
    LVALERT_SERVER=fake_server \
    LVALERT_OVERSEER_PORT=2 \
    DJANGO_TWILIO_ACCOUNT_SID=fake_sid \
    DJANGO_TWILIO_AUTH_TOKEN=fake_token \
    AWS_SES_ACCESS_KEY_ID=fake_aws_id \
    AWS_SES_SECRET_ACCESS_KEY=fake_aws_key \
    python3 manage.py collectstatic --noinput

RUN rm -rf /app/logs/* /app/project_data/*

RUN useradd -M -u 50001 -g www-data -s /bin/false gracedb

# set secure file/directory permissions. In particular, ADD command at
# beginning of recipe inherits umask of user running the build
RUN chmod 0755 /usr/local/bin/entrypoint && \
    chmod 0755 /usr/local/bin/cleanup && \
    chown gracedb:www-data /app/logs /app/project_data && \
    chmod 0750 /app/logs /app/project_data && \
    find /app/gracedb_project -type d -exec chmod 0755 {} + && \
    find /app/gracedb_project -type f -exec chmod 0644 {} +

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
