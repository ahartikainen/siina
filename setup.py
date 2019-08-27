"""Python setup information."""
import codecs
import os
import re

from setuptools import setup, find_packages

PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
REQUIREMENTS_FILE = os.path.join(PROJECT_ROOT, "requirements.txt")
README_FILE = os.path.join(PROJECT_ROOT, "README.md")
VERSION_FILE = os.path.join(PROJECT_ROOT, "siina", "__init__.py")


def get_requirements():
    """Read contents from requirements.txt."""
    with codecs.open(REQUIREMENTS_FILE) as buff:
        return buff.read().splitlines()


def get_long_description():
    """Read contents from README.md."""
    with codecs.open(README_FILE, "rt") as buff:
        return buff.read()


def get_version():
    """Read version info from __init__.py."""
    lines = open(VERSION_FILE, "rt").readlines()
    version_regex = r"^__version__ = ['\"]([^'\"]*)['\"]"
    for line in lines:
        version_search = re.search(version_regex, line, re.M)
        if version_search:
            return version_search.group(1)
    raise RuntimeError("Unable to find version in %s." % (VERSION_FILE,))


setup(
    name="siina",
    version=get_version(),
    description="Python library for Ground Penetrating Radar (GPR): IO, processing and visualization",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/ahartikainen/siina",
    author="Ari Hartikainen",
    license="Apache-2.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Physics",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="ground penetrating radar gpr io",
    packages=find_packages(exclude=["docs", "tests"]),
    install_requires=get_requirements(),
)
