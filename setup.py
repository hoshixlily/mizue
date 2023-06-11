import setuptools
from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md")) as f:
    long_description = f.read()

setup(
    name="mizue",
    version="0.1.11",
    description="A Python package for various utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Hoshilily",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3"
    ],
    packages=setuptools.find_packages(),
    install_requires=["wcwidth"],
    include_package_data=True
)
