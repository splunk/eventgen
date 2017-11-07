VERSION := `grep '^__version__[^"]*"\([0-9.]*\)"' splunk_eventgen/__init__.py | sed -e 's/.*"\([0-9.]*\)".*/\1/'`
EVENTGEN_EGG := "dist/splunk_eventgen-${VERSION}.tar.gz"
EVENTGEN_TAG := "sa-eventgen"
CURTIME ?= $(shell date +%s)
EVENTGEN_TEST_IMAGE = "eventgen-test-container"
TESTS ?= large
TEST_ARGS += ${TESTS}
DESTROY_TEST ?= 0]
ENGINE_CONF_SOURCE = ${ENGINE_CONF_SOURCE}

.PHONY: tests

all: egg

egg:
	python setup.py sdist

image: egg
	cp dist/splunk_eventgen-*.tar.gz dockerfiles/splunk_eventgen.tgz
	cd dockerfiles && docker build . -t eventgen

clean:
	rm -rf dist *.egg-info *.log
	docker rmi ${EVENTGEN_TAG} || true

setup_eventgen:
	wget ${ENGINE_CONF_SOURCE}
	mv eventgen_engine.conf splunk_eventgen/default/eventgen_engine.conf

eg_network:
	docker network create --attachable --driver bridge eg_network 2>/dev/null; true

run_server:
	docker kill eg_server 2>/dev/null; true
	docker rm eg_server 2>/dev/null; true
	docker run --network eg_network --name eg_server -d -p 9500 -p 9501 eventgen:latest server

run_controller: eg_network
	docker kill eg_controller 2>/dev/null; true
	docker rm eg_controller 2>/dev/null; true
	docker run --name eg_controller --network eg_network --network-alias rabbitmq -d -p 5672 -p 15672 -p 9500 -p 9501 eventgen:latest controller
