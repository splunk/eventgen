FROM redis:5.0.5-alpine

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
	bash \
	sudo \
	curl && \
	pip install --upgrade pip && \
	rm -rf /tmp/* && \
	rm -rf /var/cache/apk/*

COPY dockerfiles/entrypoint.sh /sbin/entrypoint.sh
COPY dist/* /root/splunk_eventgen.tgz
RUN pip install /root/splunk_eventgen.tgz && \
	rm /root/splunk_eventgen.tgz

EXPOSE 6379 9500
RUN chmod a+x /sbin/entrypoint.sh
WORKDIR /usr/lib/python2.7/site-packages/splunk_eventgen
ENTRYPOINT ["/sbin/entrypoint.sh"]
