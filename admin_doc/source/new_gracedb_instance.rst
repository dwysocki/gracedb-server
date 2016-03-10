==================================
Standing up a new GraceDB instance
==================================

Disclaimer
==========

These instructions will almost certainly not work. Please edit when you find
something that fails. 

Recipe
======

Machine and certificates
------------------------

I'll assume that the new instance will have the FQDN ``gracedb-new.cgca.uwm.edu``.
Follow the 
`instructions <https://www.lsc-group.phys.uwm.edu/wiki/Computing/ManagingVirtualMachines>`__ 
for setting up a new Debian stock VM managed by puppet. 
You are going to need an InCommon SSL certificate for Apache, so I recommend
requesting this first. Instructions are found 
`here <https://www.lsc-group.phys.uwm.edu/wiki/CertificateRequestUWM>`__. Store the 
cert and key with correct file permissions somewhere for safe keeping.

.. NOTE::
    If this new instance will have a FQDN ending in ``.ligo.org``, you will
    need to get the cert from Caltech instead. Some instructions are found
    `here <https://wiki.ligo.org/AuthProject/ComodoInCommonCert>`__.

Puppet configuration
--------------------

On your workstation, clone the ``cgca-hiera`` git repository::

    git clone git@git.ligo.org:cgca-computing-team/cgca-hiera.git

Create the necessary YAML files by copying from one of the existing
instances.  This will get you pretty far::

    cd cgca-hiera
    cp gracedb-test.cgca.uwm.edu.yaml gracedb-new.cgca.uwm.edu.yaml
    cp gracedb-test.cgca.uwm.edu.eyaml gracedb-new.cgca.uwm.edu.eyaml

Edit the latter file until you are satisfied. Here are some things you
will definitely want to change

- instances of the FQDN
- SSH key for the gracedb@gracedb-new.cgca.uwm.edu user
- user entry for yourself, to map your InCommon cert DN to the gracedb user account

You may also need to add the ``webserver3`` and ``gracedb`` modules to the 
list, as these handle much of the work, but are sometimes left off of the 
list in order to prevent changes being made to the server without the 
maintainer's knowledge.

Next, edit the EYAML file, which has the secret information in it.
At the time of writing, the best way of editing an EYAML file has not
been settled upon. (My favorite way to
do this is to use ``eyaml edit``. But at the time of writing, that is only
available as root on the ``puppet.cgca.uwm.edu`` machine, and you have to
explicitly provide paths to the PKCS7 public and private keys. In the 
intervening time, it is likely that a better way to edit eyaml files will
have been devised.) Change the mysql root and gracedb
user passwords, noting that these occur in multiple locations. Add in the 
naturally occurring shib cert and key, as well
as the apache cert and key.  Importantly, you should comment out the 
lines associated with the file ``settings_secret``. We don't want Puppet
to try to create this file yet, since our server code directories that 
contain it don't exist yet.

Commit the new files and push. Then log into the new machine as root and 
run the puppet agent::

    puppet agent -t 

This may initially produce errors, so some iteration is to be expected.

Shibboleth SP registration
--------------------------

At this point, the ``shibboleth`` package should be installed, along with its
self-signed certificates. Send email to ``rt-auth`` and ask that a service provider
with your FQDN be added to the LIGO shibboleth metatadata. You will need to
attach the cert you find at ``/etc/shibboleth/sp-cert.pem``.  The rest of the
Shibboleth SP configuration should already have been taken care of by Puppet,
so it should "just work" once it is added to the LIGO metadata.  If it doesn't,
there is more detail about setting up a new Shibboleth SP 
`here <https://wiki.ligo.org/AuthProject/DeployLIGOShibbolethDebianSqueeze>`__.

Application code
----------------

Next, we'll pull down the repo containing the source code. Log in to the 
new machine as the ``gracedb`` user, and clone the 
server code using your LIGO credentials::

    cd
    ecp-cookie-init LIGO.ORG https://versions.ligo.org/git albert.einstein
    git clone https://versions.ligo.org/git/gracedb.git

Create a new settings file by copying from one of the existing ones::

    cd gracedb/settings
    cp test.py new.py

or some other appropriate name. (Copy from ``default.py`` if you'd rather
have a production-like instead of testing-like instance.) Edit this new 
settings module as desired. You will at least want to change the
``CONFIG_NAME`` and all instances of the FQDN.  Now edit
``settings/__init__.py`` to make sure this new settings module will
be invoked::

    from default import *

    config = configs.get(ROOT_PATH, "production")

    if socket.gethostname() == 'gracedb-test':
        config = 'test'
    elif socket.gethostname() == 'gracedb-new':
        config = 'new'

    settings_module = __import__('%s' % config, globals(), locals(), 'gracedb')

Note that the behavior here is that we first import everything from default.
Then we'll overwrite those settings with fhe module specified by ``config``.
Also uncomment the ``settings_secret`` file in the EYAML for this machine,
and run the puppet agent again. This will install our secret settings file
that is pulled in by the default settings.

Required packages
-----------------

GraceDB relies on several packages that are best installed in a virtual environment
rather than at the system level. This is important, because we don't want 
our regular package updates to suprise us with, say, a new version of Django
that our code hasn't yet been ported to.
Create the virtual environment for the ``gracedb`` user in that user's
home directory::

    cd
    virtualenv djangoenv
    source djangoenv/bin/activate
    pip install mysql-python
    pip install python-ldap
    pip install html5lib
    pip install requests
    pip install Sphinx
    pip install python-memcached
    pip install django-model-utils
    pip install djangorestframework==3.3.2
    pip install django-guardian==1.4.1
    pip install django-debug-toolbar
    pip install django-debug-panel
    pip install Django==1.8.11
    pip install ligo-lvalert
    pip install ligo-lvalert-overseer       

You may find that you need to install additional packages during the testing
process.  Note that we ask for specific version numbers of some packages. Also, the
ordering of these commands matters, since packages such as ``django-guardian``
will try to pull in the very latest version of Django.  So if we really want
Django 1.8, we have to ask for that one *after* installing the third-party
packages.  I decided to stick with Django 1.8 for the time being, since it is
one of the designated LTS releases. Version 1.9, by contrast, is not and will
be supported for a shorter period of time. Successive releases of Django often
contain breaking API changes, so be prepared if you decide to update. 

Run ``collectstatic`` so that all of the static files from the various Python
sources are collected under ``gracedb/static``, where Apache will expect to 
find them::
    
    cd
    cd graced
    ./manage.py collectstatic

Next, install the JavaScript components GraceDB uses to render web pages.
As root::

    update-alternatives --install /usr/bin/node nodejs /usr/bin/nodejs 100
    which node
    curl https://www.npmjs.com/install.sh | sh
    which npm
    npm install -g bower

Then, as the ``gracedb`` user::

    cd
    bower install dgrid#0.4.0
    bower install dijit#1.10.4
    bower install dojox#1.10.4
    bower install moment#2.11.1
    bower install moment-timezone#0.5.0

These particular versions may be required in order for the web pages to render
correctly.

Miscellaneous
-------------

GraceDB relies on the ability to send email--both for alerts to users who
request them, and to the maintainer/developer in case of unhandled exceptions.
Reconfigure ``exim4`` as root by executing::

    dpkg-reconfigure exim4-config

The only change you need to make is to set it to an
"internet site; mail is sent and received directly using SMTP."

Next, set up the embedded discovery service.  Download from::

    http://shibboleth.net/downloads/embedded-discovery-service/latest/shibboleth-embedded-ds-1.1.0.tar.gz

Unpack the archive into /etc/shibboleth-ds, and edit ``idpselect_config.js``::

    this.preferredIdP = ['https://login.ligo.org/idp/shibboleth', 'https://login.guest.ligo.org/idp/shibboleth', 'https://google.cirrusidentity.com/gateway'];        // Array of entityIds to always show

You may need to increase the width of the ``idpSelectIdpSelector`` element in
``idpselect.css``. I set this to 512.

Obtain the random bin scripts used by GraceDB for various purposes::

    cd
    git clone git@git.ligo.org:cgca-computing-team/gracedb-scripts.git bin

Final steps
-----------

As the ``gracedb`` user, fill up the database::

    cd 
    scp gracedb@gracedb.cgca.uwm.edu:/opt/gracedb/sql_backups/gracedb.sql.gz .
    gunzip gracedb.sql.gz
    mysql -u gracedb -p gracedb < gracedb.sql

From your workstation, test the web interface of your new instance to make
sure it's working, and run the unit tests::

    cd gracedb-client/ligo/gracedb/test
    export TEST_SERVICE='https://gracedb-new.cgca.uwm.edu/api/'
    python test.py


Explanation of the hiera files
==============================

The ``hiera`` YAML and EYAML files attempt to describe the GraceDB server
as it *should* be.  They contain the build of the configuration necessary for
setting up a GraceDB instance, though there are some stray bits that have
to be done by hand.

.. NOTE::
    You may find yourself in the situation of needing to stand up an instance
    that is *not* managed by puppet--for example if you are setting up an 
    instance at a different data center. In that case, you will need to take
    care of the above tasks by hand. I recommend copying the Apache virtual
    host configuration and ``shibboleth2.xml`` from a working GraceDB 
    instance and modifying as needed.


Why isn't everything managed by Puppet?
=======================================

Ideally, the entire process of standing up a GraceDB instance should be
automated.  This would be very useful (perhaps necessary?) for moving GraceDB
to the cloud, and also for disaster recovery.  There are gaps in the puppet
config for ``gracedb`` and ``gracedb-test`` however, as I could not find
suitable existing puppet modules.  For example, there is a `python module
<https://forge.puppetlabs.com/stankevich/python>`__ in the Puppet forge that
manages virtul environments, but it does not handle dependencies well. You
would have to engineer a ``requirements.txt`` file that lists exact packages
and versions in a strict dependency order in order for that module to work. I
experimented with creating my own process based on a file resource for the
``requirements.txt`` and exec resources to create and update the virtual
environment based on changes to the file. However, this seemed fragile, and I
decided that it would be better to manage the virtual environment by hand.
That being said, I would recommend gradually finding ways to Puppet-ize the
rest of the install process, especially if improved modules become available.

