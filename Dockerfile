# Dockerfile for DigitalCC
FROM python:3.5.1
MAINTAINER Jeremy Nelson <jermnelson@gmail.com>

# Set environmental variables
ENV DIGCC_GIT https://github.com/Tutt-Library/Discover-Aristotle.git
ENV DIGCC_HOME /opt/digitalcc

# Update and install Python3 setuptool and pip
RUN apt-get update && apt-get install -y && \
  apt-get install -y python3-setuptools &&\
  apt-get install -y python3-pip

# Clone master branch of Tutt Library Discover Aristotle repository,
# setup Python env, run 
RUN git clone $DIGCC_GIT $DIGCC_HOME && \
  cd $DIGCC_HOME && \
  mkdir instance && \
  pip3 install -r requirements.txt && \
  python -c "import os,sys; sys.stout.write('SECRET_KEY=\"{}\"'.format(os.urandom()))" >> instance/conf.py
