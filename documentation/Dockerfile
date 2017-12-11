FROM alpine:3.6

# Install stuff
RUN apk upgrade --update && \
	apk add --no-cache --update \
	nodejs \
	nodejs-npm \
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

WORKDIR /root/
ENTRYPOINT ["/sbin/entrypoint.sh"]
