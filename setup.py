#
#  SPDX-FileCopyrightText: 2021 Thorsten Hapke <thorsten.hapke@sap.com>
#
#  SPDX-License-Identifier: Apache-2.0
#


import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="dimetadata_api",
    version="0.0.2",
    author="Thorsten Hapke",
    author_email="thorsten.hapke@sap.com",
    description="Python package using SAP Metadata Management API Business HUB.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    project_urls={'SAP Metadata Management API':"https://api.sap.com/api/metadata/overview"},
    url="https://github.com/thhapke/dimetadata_api/",
    classifiers=[
         "Programming Language :: Python :: 3.9",
         "License :: OSI Approved :: Apache Software License",
         "Operating System :: OS Independent",
    ],
    include_package_data=True,
    #package_dir={"": "src"},
    #packages=setuptools.find_packages(),
    install_requires=[
        'rdflib'
    ],
    packages=['dimetadata_api'],
    python_requires=">=3.6",
)