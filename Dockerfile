FROM debian:trixie
LABEL name="LIGO GraceDB Django application" \
      maintainer="alexander.pace@ligo.org" \
      date="20250925"
ARG SETTINGS_MODULE="config.settings.container.dev"

COPY docker/SWITCHaai-swdistrib.gpg /etc/apt/trusted.gpg.d
COPY docker/backports.pref /etc/apt/preferences.d
RUN apt-get update && \
    apt-get -y install gnupg curl


RUN echo 'deb http://deb.debian.org/debian trixie-backports main' > /etc/apt/sources.list.d/backports.list
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt trixie-pgdg main' > /etc/apt/sources.list.d/pgdg.list
RUN echo 'deb [trusted=yes] https://hypatia.aei.mpg.de/lsc-amd64-trixie ./' > /etc/apt/sources.list.d/lscsoft.list
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
RUN apt-get update && \
    apt-get --assume-yes upgrade && \
    apt-get install --install-recommends --assume-yes \
        apache2 \
        emacs-nox \
        gcc \
        git \
        krb5-user \
        libkrb5-dev \
        libapache2-mod-shib \
        libapache2-mod-xsendfile \
        libldap2-dev \
        libsasl2-dev \
        libsasl2-modules-gssapi-mit \
        libxml2-dev \
        pkg-config \
        libpng-dev \
        libpq-dev \
        libfreetype-dev \
        libxslt1-dev \
        ligo-ca-certs \
        osg-ca-certs \
        php \
        php8.4-pgsql \
        php8.4-mbstring \
        postgresql-client-15 \
        python3 \
        python3-dev \
        python3-libxml2 \
        python3-pip \
        procps \
        redis \
        shibboleth-sp-common \
        shibboleth-sp-utils \
        libssl-dev \
        swig \
        htop \
        telnet \
        vim && \
    apt-get clean


# Install AWS X-ray daemon
RUN curl -O https://s3.us-east-2.amazonaws.com/aws-xray-assets.us-east-2/xray-daemon/aws-xray-daemon-3.x.deb && \
    dpkg -i aws-xray-daemon-3.x.deb && \
    rm aws-xray-daemon-3.x.deb

# Install osg-ca-certs
RUN curl -O https://hypatia.aei.mpg.de/lsc-amd64-trixie/osg-ca-certs/osg-ca-certs_1.137NEW_all.deb && \
    dpkg -i osg-ca-certs_1.137NEW_all.deb && \
    rm osg-ca-certs_1.137NEW_all.deb

# Install ligo-ca-certs
RUN curl -O https://hypatia.aei.mpg.de/lsc-amd64-trixie/ligo-ca-certs_1.0.2-0+deb13u0_all.deb && \
    dpkg -i ligo-ca-certs_1.0.2-0+deb13u0_all.deb && \
    rm ligo-ca-certs_1.0.2-0+deb13u0_all.deb


# Supervisord configs (all services - controlled by env vars at runtime):
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/supervisord-apache2.conf /etc/supervisor/conf.d/apache2.conf
COPY docker/supervisord-igwn-alert-overseer.conf /etc/supervisor/conf.d/igwn-overseer.conf
COPY docker/supervisord-qcluster.conf /etc/supervisor/conf.d/qcluster.conf
COPY docker/supervisord-shibd.conf /etc/supervisor/conf.d/shibd.conf
COPY docker/supervisord-aws-xray.conf /etc/supervisor/conf.d/aws-xray.conf

# Apache configs:
COPY docker/apache-config /etc/apache2/sites-available/gracedb.conf
COPY docker/mpm_prefork.conf /etc/apache2/mods-enabled/mpm_prefork.conf

# Enable mpm_event module and do some more apache stuff:

RUN rm /etc/apache2/mods-enabled/mpm_prefork.*
RUN rm /etc/apache2/mods-enabled/php8.4.*
RUN cp  /etc/apache2/mods-available/mpm_event.* /etc/apache2/mods-enabled/
RUN a2dissite 000-default.conf && \
    a2ensite gracedb.conf && \
    a2enmod headers proxy proxy_http rewrite xsendfile

# this line is unfortunate because "." updates for nearly any change to the
# repository and therefore docker build rarely caches the steps below
ADD . /app/gracedb_project

# Docker scripts (unified entrypoint handles both local and production)
COPY docker/entrypoint /usr/local/bin/entrypoint
COPY docker/cleanup /usr/local/bin/cleanup

# Shibboleth configs and certs (used in production, ignored in local)
RUN cp -r /app/gracedb_project/docker/shibboleth-ds /etc/shibboleth-ds && \
    cp /app/gracedb_project/docker/login.ligo.org.cert.LIGOCA.pem /etc/shibboleth/login.ligo.org.cert.LIGOCA.pem && \
    cp /app/gracedb_project/docker/inc-md-cert.pem /etc/shibboleth/inc-md-cert.pem && \
    cp /app/gracedb_project/docker/check_shibboleth_status /usr/local/bin/check_shibboleth_status

# install gracedb application itself
WORKDIR /app/gracedb_project
RUN pip3 install -r requirements.txt --break-system-packages

# install supervisor from pip
RUN pip3 install supervisor --break-system-packages

# Give pip-installed packages priority over distribution packages
ENV PYTHONPATH /usr/local/lib/python3.13/dist-packages:$PYTHONPATH
ENV ENABLE_SHIBD false
ENV ENABLE_AWS_XRAY false
ENV ENABLE_OVERSEER true
ENV LOCAL_BUILD false
ENV VIRTUAL_ENV /dummy/

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
    EGAD_URL=fake_url \
    EGAD_API_KEY=fake_key \
    LVALERT_USER=fake_user \
    LVALERT_PASSWORD=fake_password \
    LVALERT_SERVER=fake_server \
    LVALERT_OVERSEER_PORT=2 \
    IGWN_ALERT_USER=fake_user \
    IGWN_ALERT_PASSWORD=fake_password \
    IGWN_ALERT_SERVER=fake_server \
    IGWN_ALERT_OVERSEER_PORT=2 \
    IGWN_ALERT_GROUP=fake_group \
    DJANGO_TWILIO_ACCOUNT_SID=fake_sid \
    DJANGO_TWILIO_AUTH_TOKEN=fake_token \
    DJANGO_AWS_ELASTICACHE_ADDR=fake_address:11211 \
    AWS_SES_ACCESS_KEY_ID=fake_aws_id \
    AWS_SES_SECRET_ACCESS_KEY=fake_aws_key \
    python3 manage.py collectstatic --noinput

RUN rm -rf /app/logs/* /app/project_data/*

RUN useradd -M -u 50001 -g www-data -s /bin/false gracedb

#RUN groupadd -r xray
#RUN useradd -M -u 50002 -g xray -s /bin/false xray

# set secure file/directory permissions. In particular, ADD command at
# beginning of recipe inherits umask of user running the build
RUN chmod 0755 /usr/local/bin/entrypoint && \
    chmod 0755 /usr/local/bin/cleanup && \
    chown gracedb:www-data /app/logs /app/project_data && \
    chmod 0750 /app/logs /app/project_data && \
    find /app/gracedb_project -type d -exec chmod 0755 {} + && \
    find /app/gracedb_project -type f -exec chmod 0644 {} +

# create and set scitoken key cache directory
RUN mkdir /app/scitokens_cache && \
    chown gracedb:www-data /app/scitokens_cache && \
    chmod 0750 /app/scitokens_cache
ENV XDG_CACHE_HOME /app/scitokens_cache

# Remove packages that expose security vulnerabilities and close out.
# Edit: zlib1g* can't be removed because of a PrePend error
RUN apt-get --assume-yes --purge autoremove wget libaom3 node-ip
RUN apt-get clean

ENTRYPOINT [ "/usr/local/bin/entrypoint" ]
CMD ["/usr/local/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
