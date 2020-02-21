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

  $ export PULP_PASSWORD="pulppassword"
  $ pubtools-iib-remove-operators --pulp-url https://pulphost.example.com/\
    --pulp-user pulp-user\
    --pulp-repository index-image-repository\
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --operator bundle/image:123
    --arch x86_64

