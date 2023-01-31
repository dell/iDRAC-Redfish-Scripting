from setuptools import setup, find_packages
import codecs
import os

define_path = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(define_path, "README.txt"), encoding="utf-8") as x:
    long_description = "\n" + x.read()

DESCRIPTION = "iDRAC Redfish API support for multiple iDRAC workflows."
LONG_DESCRIPTION = "Python module for iDRAC Redfish support to allow the user to perform multiple workflows. This module can be imported from python prompt to start an interactive session with the iDRAC to perform multiple operations. Some workflow examples include configuration changes, firmware updates, exporting logs and SupportAssist collection. See module function section below for all supported workflows."

# Setting up
setup(
        name="IdracRedfishSupport", 
        version="0.0.6",
        license='GPLv2',
        author="Texas Roemer",
        author_email="texas_roemer@dell.com",
        description=DESCRIPTION,
        long_description_content_type="text/markdown",
        long_description=long_description,
        packages=["IdracRedfishSupport"],
        url='',
        install_requires=["requests"],
        keywords=["python", "Redfish", "IDRAC"]
)
