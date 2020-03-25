FROM splunk/splunk:7.3-debian

RUN sudo apt-get update

RUN echo "installing docker dependencies and development tools" && \
    sudo apt-get --assume-yes install curl vim

COPY ["provision.sh", "add_httpevent_collector.sh", "/opt/splunk/"]
