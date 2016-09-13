# Dockerfile for DigitalCC
FROM python:3.5.1
MAINTAINER Jeremy Nelson <jermnelson@gmail.com>

# Set environmental variables
ENV DIGCC_GIT https://github.com/Tutt-Library/digital-cc.git
ENV DIGCC_HOME /opt/digital-cc

# Update and install Python3 setuptool and pip
RUN apt-get update && apt-get install -y && \
  apt-get install -y python3-setuptools &&\
  apt-get install -y python3-pip && \
  apt-get install -y supervisor && \
  apt-get install -y cron

# Clone master branch of Tutt Library Digitial CC repository,
# setup Python env, run 
RUN git clone $DIGCC_GIT $DIGCC_HOME && \
  cd $DIGCC_HOME && \
  mkdir instance && \
  pip3 install -r requirements.txt && \
  chmod +x $DIGCC_HOME/search/poll.py && \
  crontab crontab.txt

COPY instance/conf.py $DIGCC_HOME/instance/conf.py
COPY supervisord.conf /etc/supervisor/conf.d/
EXPOSE 5000

WORKDIR $DIGCC_HOME
CMD ["/usr/local/bin/supervisord"]
#CMD ["python", "run.py"]
#CMD ["nohup", "uwsgi", "-s", "0.0.0.0:5000", "-w", "run:app"]
