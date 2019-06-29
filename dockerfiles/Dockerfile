FROM rabbitmq:3.7.15-management-alpine

RUN apk --no-cache upgrade && \
	apk add --no-cache --update \
	python2-dev \
	py2-pip \
	gcc \
	libc-dev \
	libffi-dev \
	openssl-dev \
	libxml2-dev \
	libxslt-dev \
	curl && \
	pip install --upgrade pip && \
	rm -rf /tmp/* && \
	rm -rf /var/cache/apk/*

COPY dockerfiles/entrypoint.sh /sbin/entrypoint.sh
COPY dist/* /root/splunk_eventgen.tgz
RUN pip install /root/splunk_eventgen.tgz && rm /root/splunk_eventgen.tgz

EXPOSE 5672 15672 9500
WORKDIR /opt/splunk/etc/apps
ENTRYPOINT ["/sbin/entrypoint.sh"]
