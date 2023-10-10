Pubtools-iib-remove-operators
=============================


.. argparse::
   :module: pubtools.iib.iib_ops
   :func: make_rm_operators_parser
   :prog: pubtools-iib-remove-operators


Example of usage
------------------

::

  $ pubtools-iib-remove-operators\
    --iib-server iibhostname.example.com\
    --binary-image container-registry.example.com/binary/image:latest
    --index-image container-registry.example.com/index/image:latest
    --operator bundle/image:123
    --arch x86_64

