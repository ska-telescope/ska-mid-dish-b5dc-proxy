###########
Change Log
###########

## unreleased
*************

Version 0.0.1
*************
- Helm chart created to enable B5dc Proxy deployment
- Added buildState attribute
- Created B5dc Proxy tango device with B5DC sensor attributes
- Commands added to B5dc Proxy tango device to enable B5dc device configuration

  - SetFrequency
  - SetAttenuation

- Added connectionState attribute to B5dc Proxy tango device
- Upgraded ska-mid-dish-dcp-lib chart to v0.0.4
- Updated dockerfile to use new base images and improved docker image build
- Bootstrap repo with ska-cookiecutter-pypackage