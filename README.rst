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

  $ pubtools-iib-add-bundles \
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --bundle container-registry.example.com/bundle/image:123
    --arch x86_64
    --deprecation-list container-registry.example.com/index/bundle-image:latest,container-registry.example.com/index/bundle-image:2

  $ pubtools-iib-remove-operators \
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --operator bundle/image:123
    --arch x86_64

