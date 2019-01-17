.. _new_gracedb_instance:

==================================
Standing up a new GraceDB instance
==================================

*Last updated 14 December 2017*

Disclaimer
==========
Certain parts of these instructions may not work.
Please edit when you find something that fails. 

Also note that setup of a GraceDB server relies heavily on Puppet.
You may attempt a Puppet-less setup at your own risk!

Initial steps
========================
The first step is to pick the FQDN for your new server.
As of spring 2017, it's preferred to use the ``.ligo.uwm.edu`` domain.
For this exercise, we'll assume that a server name ``gracedb-new.ligo.uwm.edu``.
You should also decide whether you will need a LIGO.ORG domain name (i.e., ``gracedb-new.ligo.org``).
This is not absolutely necessary for test instances, but is recommended in order to simulate the production environment as closely as possible.

Virtual machine setup
---------------------
You'll need to either have one of the VMWare tools (VMWare Workstation for Linux or VMWare Fusion for OS X) installed on your machine, access to ``headroom.cgca.uwm.edu`` (a Windows machine that has VMWare vSphere), or access to the `web interface <http://vc5.ad.uwm.edu>`__.
Currently, the web interface is the preferred method for setting up a new VM, so the following instructions will be for this method.

Find the VM template you want to use (click on a VM host (left panel), then "VMs" (middle frame), then "VM Templates in Folders").
Currently, the Debian templates are on ``vmhost05``, but you may have to check all of the VM hosts if you don't find it there.
We are currently using Debian 8, but in the process of moving to Debian 9. 
Left-click on the template and then choose "New VM from This Template" (above the list of templates).
Enter ``gracedb-new`` for the virtual machine's name and hit "Next".
Then, choose the VM host you want to put the VM on and hit "Next".
You can probably skip the next two steps and hit "Finish".

At this point, you can modify the VM's settings:

- CPU: 2 is fine for testing, use only 1 socket total (not 1 per core).
- RAM: something like 2 GB should be fine for testing.
- Storage space: add a second hard drive of about 100 GB (for testing). You may want a larger disk if this is a production server or if you intend to copy the entire production database for testing purposes.
- Network adapter: use public VLAN 61.

The instructions on the CGCA computing `wiki <https://www.lsc-group.phys.uwm.edu/wiki/Computing/ManagingVirtualMachines>`__ provide more detailed information that may be helpful.

Getting certificates
--------------------
It's best to submit your requests for any certificates as soon as possible, as waiting for these will most likely be the biggest bottleneck in this process.

- In all cases, you'll need an InCommon SSL certificate for your ligo.uwm.edu domain name. Follow the instructions on the CGCA computing wiki `here <https://www.lsc-group.phys.uwm.edu/wiki/CertificateRequestUWM>`__.  Note that the "short hostname" for our server is ``gracedb-new``.
- If you decided that you want a LIGO.ORG domain name, you'll need an InCommon SSL certificate for this, as well.  Follow the instructions `here <https://wiki.ligo.org/AuthProject/ComodoInCommonCert>`__.
- Finally, you may want an IGTF certificate to provide gsissh access.  It depends whether you want non-UWM people to potentially have access via the command line without SSH keys.  You can do this for either the UWM or LIGO domain names; Tom prefers that we use the UWM one.  The instructions for the UWM SSL certificate also contain information about obtaining an IGTF certificate.

In all cases, you'll generate a key and a certificate request, and will send the certificate request to the proper authorities for it to be signed.
Once your certificate is ready, you'll receive an e-mail with instructions for downloading your certificate.
You will usually want the certificate labeled as "X509 Certificate only, Base64 encoded".

DNS configuration
-----------------

UWM
___
In the web interface, you should be able to find the MAC address of the network adapter under the adapter's settings.
If you need to generate a new MAC address, I'm not sure how to do that through the web interface.
However, you can do this with VMWare Workstation by right-clicking on your VM to access "Settings", then "Network adapter", and then "Advanced."
Follow the `instructions <https://www.lsc-group.phys.uwm.edu/wiki/Computing/ManagingVirtualMachines#Create_a_DNS_entry_for_the_guest>`__ on the CGCA wiki for setting up a DNS entry through ``dns.uwm.edu``.
Note that you will have to click on the "Data Management" tab in the top middle to get to the "Network" settings specified in these instructions.

After this is complete, you can boot up the VM.

LIGO DNS
________
This section is only relevant if you are using a LIGO.ORG domain name.
Email Larry Wallace (larry.wallace@ligo.org) and ask him to configure ``gracedb-new.ligo.org`` as a CNAME that points to ``gracedb-new.ligo.uwm.edu``.

VM configuration
================

Standard CGCA server configuration
----------------------------------
Log on to your server through VMWare Workstation, using the standard root password (note that the hostname is initially set to ``server``).
Download and run the Debian setup script (as shown on the CGCA wiki)::

    curl -s http://omen.phys.uwm.edu/setup_debian.sh | bash -s -- gracedb-new.ligo.uwm.edu

Reboot the VM.
The hostname should now be ``gracedb-new.ligo.uwm.edu``.
Change the root password to match the new hostname using the standard root password formula (use the ``passwd`` command).
Note: the root password formula may change/be removed in late 2017.

The setup script has generated and sent a Puppet certificate request to the puppetmaster server.
Log in to ``puppet.cgca.uwm.edu`` and sign the certificate (see instructions `here <https://www.lsc-group.phys.uwm.edu/wiki/Computing/AddingPuppet>`__).

Running Puppet
--------------
GraceDB servers use the standard CGCA configuration for a webserver, with several customizations implemented by a gracedb module.
More information about how to use this module is in its README file.
You can find the module `here <https://git.ligo.org/cgca-computing-team/cgca-config/tree/production/localmodules/gracedb>`__ (for now, it may move to its own repo in the near future).

First, you'll need to generate hiera files for this server for use with Puppet.
In the cgca-config repository, create ``data/nodes/gracedb-new.ligo.uwm.edu.yaml`` and ``data/nodes/gracedb-new.ligo.uwm.eyaml``.
I suggest copying another GraceDB server's files and customizing them as needed.
Things you will likely need to change include:

- The database password: ``gracedb::mysql::database::password``
- The root MySQL password: ``mysql::server::root_password``)
- Accounts for LVAlert servers (if this is a test server, use only ``lvalert-test.cgca.uwm.edu``): create the new account on the LVAlert server (current best method is the online Openfire interface). You'll need to add an entry to ``gracedb::config::netrc`` for this account.
- Set ``shibboleth::certificate::useHiera`` to false. This will cause a new Shibboleth key and certificate to be generate on the first Puppet run.  After that, you'll copy the generated certificate and key into your server's .eyaml file and set this variable to true.  Then re-run Puppet.
- If you have SSL certificates already, add them to the .eyaml file.  If not, remove these lines for now and add them back in once you have the certificates.
- Add this server to the gracedb hostgroup (contains base setup for all GraceDB servers) in the `puppet_node_classifier <https://git.ligo.org/cgca-computing-team/cgca-config/blob/production/site/profile/files/puppetmaster/puppet_node_classifier>`__.

Push your changes to the repository (use a branch and ``r10k`` if you want to be cautious).
Then, run Puppet on your new server.
Note that it may take a few minutes for the changes to propagate to the puppetmaster machine, so you may have to wait before running Puppet.

Shibboleth SP registration
--------------------------
Once you have your Shibboleth key and certificate set up in the Puppet configuration, with ``shibboleth::certificate::useHiera`` set to true, you need to register your SP.
Send an email to ``rt-auth@ligo.org`` and ask that a service provider with your FQDN be added to the LIGO shibboleth metadata (generally, use the LIGO.org FQDN, if available).
You will need to attach the cert you find at ``/etc/shibboleth/sp-cert.pem``.

Shibboleth discovery service
----------------------------
Next, set up the embedded discovery service for Shibboleth.
Go to the "latest" Shibboleth downloads `page <http://shibboleth.net/downloads/embedded-discovery-service/latest/>`__ and determine the version.
Then you can do::

    wget http://shibboleth.net/downloads/embedded-discovery-service/latest/shibboleth-embedded-ds-1.2.0.tar.gz

Unpack the archive into ``/etc/shibboleth-ds`` (create the directory if it doesn't exist), and edit ``idpselect_config.js``.

Change the line starting with ``this.preferredIdP`` to::

    this.preferredIdP = ['https://login.ligo.org/idp/shibboleth', 'https://login.guest.ligo.org/idp/shibboleth', 'https://google.cirrusidentity.com/gateway'];

This determines the identity providers which will be shown on the discovery service login page.
For test deployments, you may not need to include the Google IdP (depends if your server is set up to use the Cirrus Google gateway or not), but it doesn't hurt anything to include it.

You may need to increase the width of the ``idpSelectIdpSelector`` element in
``idpselect.css`` (set to ~512 px for 3 IdPs).
You may need to edit ``this.maxPreferredIdPs`` if you have more than the default number (3).

Check if the link provided in ``this.helpURL`` is functional or not; it has not worked for me in the past several versions of ``shibboleth-ds``.
I suggest using this `link <https://wiki.shibboleth.net/confluence/display/SHIB2/DiscoveryService>`__ instead (if functional).

Finally, if you are confused about parts (or all) of this section, I suggest looking at other GraceDB servers and emulating their configuration.

Populating the database
=======================

"Fresh" database
----------------
To construct a "fresh" database from migrations, just run::

    cd $HOME/gracedb_project
    python manage.py migrate

Copying production database
---------------------------
First, as yourself, copy the database from a test server to your new server::

    sudo cp /opt/gracedb/sql_backups/gracedb.sql.gz $HOME
    scp gracedb.sql.gz $(whoami)@gracedb-new.ligo.uwm.edu:~

On the new server, as yourself, import the database using the ``gracedb`` user's credentials::

    gunzip gracedb.sql.gz
    mysql -u gracedb -p gracedb < gracedb.sql

Note that files related to the events aren't part of the database and won't exist on the new server unless you copy them over, too (see :ref:`copying_event_data` for more information).

Next, become the ``gracedb`` user, enter the Django manager shell, and delete all Contacts and Notifications so that people don't get phone or email alerts from this instance without signing up for them::

    from alerts.models import Contact, Notification
    for c in Contact.objects.iterator():
        c.delete()
    for t in Notification.objects.iterator():
        t.delete()

You might want to delete the Events, too, especially if you copy the production database.

Extra steps
===========

As root
-------
- Add time zone information to the database::

    mysql_tzinfo_to_sql /usr/share/zoneinfo/ | mysql -u root mysql
    systemctl restart mariadb

- Upgrade ``nodejs`` version (also installs ``npm``)::

    curl -sL https://deb.nodesource.com/setup_8.x | bash -
    apt-get install nodejs

  - Note: you may want to check for a newer version than 8.x.
- Install ``bower`` for managing JavaScript packages: ``npm install -g bower``
- Reconfigure ``exim4`` package for sending e-mail: ``dpkg-reconfigure exim4-config``. Accept the defaults, except for:
    - Set the host to be an "internet site"; mail is sent and received directly using SMTP.
    - Remove ``::`` from the list of listening addresses; seems to cause the server to hang.
    - Set "system mail name" to ``gracedb-new.ligo.uwm.edu``.
    - Set the IP address to listen to for incoming connections to be ``127.0.0.1``.
    - Set "other destinations for which mail is accepted" to ``gracedb-new.ligo.uwm.edu``; can optionally add ``gracedb-new.ligo.org`` if desired.
    - Once you're done, restart the ``exim4`` process: ``systemctl restart exim4``
- Build and mount the secondary file system for holding data files:
    - Build the filesystem: ``mkfs.ext4 /dev/sdb``
    - Add the following line to ``/etc/fstab``: ``/dev/sdb /opt/gracedb ext4 errors=remount-ro 0 1``
        - A safer option is to find the UUID for your drive (``ls -lh /dev/disk/by-uuid``) and use that in place of ``/dev/sdb`` (see other entries in the file for examples).
    - If there are subdirectories currently in ``/opt/gracedb``, move them somewhere else temporarily.
    - Mount the filesystem: ``mount -a``
    - Move back any subdirectories that you may have temporarily moved.

As the ``gracedb`` user
-----------------------
- Activate the virtualenv: ``source $HOME/djangoenv/bin/activate``

- Build the GraceDB documentation::

    cd $HOME/gracedb_project/docs/user_docs
    sphinx-build -b html source build
    cd ../admin_docs
    sphinx-build -b html source build

- Clone the GraceDB admin scripts repo into the gracedb user's ``$HOME``::

    git clone https://git.ligo.org/gracedb/scripts.git $HOME/bin

  - Note that the server code repo has already been cloned by Puppet, since it's publicly available. We clone this repo by hand since it's private and dealing with deploy keys is too annoying.
  - You can call the directory whatever you want (instead of ``bin``), but then you should change the corresponding parameter (``gracedb::config::script_dir``) in the server's Puppet configuration file.

- Run the setup script in this repository (``initial_server_setup.py``) to pull user accounts from the LIGO LDAP, set up admin/superuser accounts, add users to the executives group, and add users to the EM advocates group.

- Collect static files::

    cd $HOME/gracedb_project
    python manage.py collectstatic

- Use bower to install Javascript and CSCS packages (the ``bower.json`` file contains all of the package details)::

    cd $HOME/gracedb_project
    bower install

- Instantiate the database backups (``logrotate`` will fail if there isn't an initial file)::

    touch /opt/gracedb/sql_backups/gracedb.sql.gz

Allowing access
===============

Outside networks
----------------
As configured, your new VM is only accessible from the UWM campus network (or from outside if you are on the VPN).
If you'd like to allow access from the outside world, email ``noc@uwm.edu``, specify the FQDN and IP address of your new server, and ask them to add openings to the entire world for SSH, HTTP, and HTTPS.

In either case, you'll need to update the firewall policy document, which is used to track the accessibility of all of the CGCA servers.
It's hosted in the CGCA Computing SharePoint, accessible through your UWM Microsoft Online account.
The file is called ``cgca-firewall-policy.xlsx``; add a new entry and follow the syntax of the other GraceDB servers.

Non-LVC users
-------------
For non-internal users to be able to access this server, you'll need to register the server with InCommon.
This provides access via federated identity login (through their university or organization).
Talk to Scott K. about how to set this up.

If you want to allow Google account access, you'll need to set it up through the Cirrus gateway in addition to registering with InCommon.
Go `here <https://apps.cirrusidentity.com/console/auth/index>`__ to login, look at the other GraceDB servers to see how they are configured, and follow the directions.
Make sure to set the Google service up with your LIGO.ORG credentials rather than a personal Gmail account.
Note that you'll need to be an admin in the Cirrus console to make these changes; talk to Warren A. about setting that up.

If you use either of these services, users will need to register through gw-astronomy in order to get the proper attributes added to their session.
Ask Mike Manske to "add the server to the attribute filter for the attribute authority IdP" (his words).
This is necessary so that gw-astronomy will send information about LV-EM group memberships.

Why isn't everything managed by Puppet?
=======================================

Ideally, the entire process of standing up a GraceDB instance should be automated.
This would be very useful (perhaps necessary?) for moving GraceDB to the cloud, and also for disaster recovery.
However, there do not exist suitable Puppet modules for certain portions of the configuration (i.e., the parts that you just did manually in `Extra steps`_).
As new modules become available (or you develop them yourself), it may be possible to Puppetize more (or all) of this process.
