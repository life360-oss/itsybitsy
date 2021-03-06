import re
from setuptools import setup

version = re.search(
    r'^__version__\s*=\s*"(.*)"',
    open('itsybitsy/itsybitsy.py').read(),
    re.M
).group(1)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="itsybitsy",
    version=version,
    author="etherops",
    author_email="patrick@life360.com",
    description="It's like a web-crawler, but for microservices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/life360/itsybitsy",
    packages=['itsybitsy', 'itsybitsy.plugins'],
    entry_points={
        "console_scripts": ['itsybitsy = itsybitsy.itsybitsy:main']
    },
    install_requires=[
        'asyncssh~=2.2.1',
        'boto3~=1.16.42',
        'configargparse~=1.2.3',
        'coolname~=1.1.0',
        'faker~=4.1.8',
        'kubernetes~=11.0.0',
        'paramiko~=2.7.2',
        'pyyaml~=5.3.1',
        'graphviz~=0.13.2',
        'termcolor~=1.1.0',
    ],
    extras_require={
        'test': [
            'prospector~=1.2.0',
            'pytest~=6.2.1 ',
            'pytest-asyncio~=0.14.0',
            'pytest-cov~=2.10.1',
            'pytest-mock~=3.4.0'
        ]
    },
    setup_requires=[
        'wheel~=0.36.2'
    ],
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License     ",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
