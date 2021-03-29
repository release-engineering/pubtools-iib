==============
 pubtools-iib
==============

Set of cli scripts used for operating with IIB service.



Requirements
============

* Python 3.7+ or Python 2.7

Features
========

* pubtools-iib-add-bundles - script used for running add bundle on IIB
* pubtools-iib-remove-operator - script used for running remove operator on IIB

Setup
=====

::

  $ pip install -r requirements.txt
  $ pip install . 
  or
  $ python setup.py install

Usage
=====

Push the created index image to Pulp
::

  $ export PULP_PASSWORD="pulppassword"
  $ pubtools-iib-add-bundles --pulp-url https://pulphost.example.com/\
    --pulp-user pulp-user\
    --pulp-repository index-image-repository\
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --bundle container-registry.example.com/bundle/image:123
    --arch x86_64
    --skip-quay
    --deprecation-list container-registry.example.com/index/bundle-image:latest,container-registry.example.com/index/bundle-image:2

  $ export PULP_PASSWORD="pulppassword"
  $ pubtools-iib-remove-operators --pulp-url https://pulphost.example.com/\
    --pulp-user pulp-user\
    --pulp-repository index-image-repository\
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --operator bundle/image:123
    --arch x86_64
    --skip-quay

Push the created index image to Quay in a remote server and send a UMB message
::

  $ export QUAY_PASSWORD=quay_password
  $ export SSH_PASSWORD=ssh_password
  $ pubtools-iib-add-bundles \
    --iib-server iibhostname.example.com \
    --binary-image container-registry.example.com/binary/image:latest \
    --index-image container-registry.example.com/index/image:latest \
    --bundle container-registry.example.com/bundle/image:123 \
    --arch x86_64 \
    --skip-pulp \
    --quay-dest-repo quay.io/namespace/repo \
    --quay-user namespace+robot_account \
    --quay-remote-exec \
    --quay-ssh-remote-host 127.0.0.1 \
    --quay-ssh-remote-host-port 2222 \
    --quay-ssh-username ssh_user \
    --quay-send-umb-msg \
    --quay-umb-url amqps://umb-url1:5671 \
    --quay-umb-url amqps://umb-url2:5671 \
    --quay-umb-cert /path/to/file.crt \
    --quay-umb-client-key /path/to/file.key \
    --quay-umb-ca-cert /path/to/cacert.crt

