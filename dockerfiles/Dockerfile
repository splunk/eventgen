FROM alpine:3.6

ENV RABBITMQ_VERSION=3.6.13

RUN apk --no-cache upgrade && \
	apk add --no-cache --update \
	python2-dev \
    py2-pip \
    gcc \
    build-base \
    libffi-dev \
	openssl-dev \
	openssh \
	erlang \
	erlang-mnesia \
	erlang-public-key \
	erlang-crypto \
	erlang-ssl \
	erlang-sasl \
	erlang-asn1 \
	erlang-inets \
	erlang-os-mon \
	erlang-xmerl \ 
	erlang-eldap \
	erlang-syntax-tools \
	xz \
	curl \
	bash && \ 
	rm -rf /var/cache/apk/* && \
	curl -sL https://www.rabbitmq.com/releases/rabbitmq-server/v${RABBITMQ_VERSION}/rabbitmq-server-generic-unix-${RABBITMQ_VERSION}.tar.xz | tar -xJ -C /usr/local && \
	ln -s /usr/local/rabbitmq_server-${RABBITMQ_VERSION}/sbin/rabbitmq-server /usr/sbin/rabbitmq-server && \
	ln -s /usr/local/rabbitmq_server-${RABBITMQ_VERSION}/sbin/rabbitmq-env /usr/sbin/rabbitmq-env && \
	/usr/local/rabbitmq_server-${RABBITMQ_VERSION}/sbin/rabbitmq-plugins enable rabbitmq_management && \
	rm -rf /tmp/* && \
	ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa && \
	mkdir -p /var/run/sshd && \
	mkdir -p /root/.ssh && \
	chmod 0700 /root/.ssh && \
	pip install requests_futures nameko pyOpenSSL --upgrade

COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /sbin/entrypoint.sh
COPY splunk_eventgen.tgz /root/splunk_eventgen.tgz
COPY rabbitmq.config /usr/local/rabbitmq_server-${RABBITMQ_VERSION}/etc/rabbitmq/rabbitmq.config

RUN pip install /root/splunk_eventgen.tgz

EXPOSE 2222 5672 15672 9501 9500
WORKDIR /root
ENTRYPOINT ["/sbin/entrypoint.sh"]
