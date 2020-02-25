Pubtools-iib-remove-operators
=============================


.. argparse::
   :module: pubtools.iib.iib_ops
   :func: make_rm_operators_parser
   :prog: pubtools-iib-remove-operators


Example of usage
------------------

::

  $ export PULP_PASSWORD="pulppassword"
  $ pubtools-iib-remove-operators --pulp-url https://pulphost.example.com/\
    --pulp-user pulp-user\
    --pulp-repository index-image-repository\
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --operator bundle/image:123
    --arch x86_64

