ChangeLog
=========

Unreleased
-----------

0.25.0 (2024-06-05)
-------------------
* Add an argument to set the IIB build timeout

0.24.0 (2023-10-17)
-------------------
* Remove Docker Pulp support

0.23.0 (2023-09-12)
-------------------
* Add check_related_images parameter

0.22.0 (2023-05-22)
-------------------
* Add Bandit scanning to pipeline
* Fixed broken tests
* Drop Python2 support
* Display an IIB error directly in the pub logs
* Pin bandit version
* Upgrade iiblib to 7.1.0

0.21.0 (2022-02-07)
-------------------
* Added build_tags support
* Use pubtools.iib logger rather than root logger

0.20.0 (2021-06-10)
-------------------
* Make Pulp-related arguments non-mandatory

0.19.0 (2021-04-01)
-------------------
* Remove option of pushing to Quay
* Restore original installation of dependencies

0.18.1 (2021-03-31)
-------------------
* Change iiblib version to 3.0.0.

0.18.0 (2021-03-29)
-------------------
* Add deprecation_list and index_image_resolved attribute
* Add option of pushing to Quay
* Add log links to build details
* Remove duplicated FakeTaskManager

0.17.0 (2020-10-19)
-------------------
* Change IIBlib imports

0.16.0 (2020-09-29)
-------------------
* Made --bundle an optional argument
* Made --binary-image an optional argument

0.15.0 (2020-06-25)
-------------------
* Replaced content-delivery-release-bot with token
* Added support for providing "overwrite-from-index-token" when calling IIB

0.14.0 (2020-05-27)
-------------------
* Fixed multiple argument passing to use 'append' mode

0.13.0 (2020-04-29)
-------------------
* Added --skip-pulp attribute support

0.12.0 (2020-03-30)
-------------------
* added --overwrite-index-image param

0.11.0 (2020-03-09)
-------------------
* Fixed push items handling

0.10.0 (2020-03-04)
-------------------
* fixed wrong feed attribute
* sync only needed tags

0.9.0 (2020-03-04)
------------------
* succesful build dump to output

0.8.0 (2020-03-04)
------------------
* fixed repo sync attributes

0.7.0 (2020-03-04)
------------------
* added iib-insecure attribute
* dump error build details on output
* index-image attribute optional

0.6.0 (2020-03-04)
------------------
* iiblib 0.7.0 compat changes

0.5.0 (2020-03-03)
------------------
* fixed invalid argument for IIBClient init

0.4.0 (2020-02-27)
------------------
* added legacy registry support

0.3.0 (2020-02-27)
------------------
* kerberos support


0.2.0 (2020-02-27)
------------------

Fixed
~~~~~
* iiblib 0.3.0 compatiblity fixes

Added
~~~~~
* ssl_verification option for IIBClient



0.1.0 (2020-02-25)
------------------

* Initial release.

