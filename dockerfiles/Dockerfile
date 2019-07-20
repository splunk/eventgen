FROM python:2

COPY requirements.txt /tmp

RUN pip install -r /tmp/requirements.txt

COPY . /usr/src/app/

RUN cd /usr/src/app && \
    make && \
    mkdir -p /usr/src/dist && \
    cp /usr/src/app/dist/* /usr/src/dist/ && \
    ls /usr/src/dist

FROM redis:5-alpine

RUN apk --no-cache upgrade && \
	apk add --no-cache --update \
	python2 \
	py2-pip \
	python2-dev \
	py2-pip \
	gcc \
	libc-dev \
	libffi-dev \
	openssl-dev \
	libxml2-dev \
	libxslt-dev \
	curl  && \
	pip install --upgrade pip && \
	rm -rf /tmp/* && \
	rm -rf /var/cache/apk/*

COPY dockerfiles/entrypoint.sh /sbin/entrypoint.sh
COPY --from=0 /usr/src/dist/* /tmp/splunk_eventgen.tgz

RUN ls /tmp && \
    pip install /tmp/splunk_eventgen.tgz && \
	rm /tmp/splunk_eventgen.tgz

EXPOSE 2222 6379 9500
RUN chmod a+x /sbin/entrypoint.sh
WORKDIR /usr/lib/python2.7/site-packages/splunk_eventgen
ENTRYPOINT ["/sbin/entrypoint.sh"]
