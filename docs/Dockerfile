FROM alpine:3.6

# Install stuff
RUN apk upgrade --update && \
	apk add --no-cache --update \
	nodejs \
	nodejs-npm \
	curl \
	python3 \
	build-base && \ 
	rm -rf /var/cache/apk/* && \
	npm install -g npm q gitbook-cli lodash commander optimist bash-color fs-extra

# Copy gitbook files
COPY *.md /root/
COPY book.json /root/

# Copy entrypoint
COPY entrypoint.sh /sbin/entrypoint.sh

# Run gitbook install
RUN cd /root/ && gitbook install

EXPOSE 4000

HEALTHCHECK --interval=1m --timeout=15s --start-period=1m --retries=3 \
	CMD curl -f http://localhost:4000 || exit 1

WORKDIR /root/
ENTRYPOINT ["/sbin/entrypoint.sh"]
