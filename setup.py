import pathlib
from setuptools import setup, find_packages

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="RequestMap",
    version="1.0.3",
    description="RequestMap is a micro framework for API developments.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/yyjlincoln/RequestMap",
    author="Yijun Yan",
    author_email="yyjlincoln@gmail.com",
    license="Apache",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(),
    install_requires=["flask"]
)
