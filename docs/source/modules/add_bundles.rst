Pubtools-iib-add-bundles
========================


.. argparse::
   :module: pubtools.iib.iib_ops
   :func: make_add_bundles_parser
   :prog: pubtools-iib-add-bundles

Example of usage
------------------

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
