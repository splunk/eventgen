VERSION := `grep '^__version__[^"]*"\([0-9.]*\)"' splunk_eventgen/__init__.py | sed -e 's/.*"\([0-9.]*\)".*/\1/'`
EVENTGEN_EGG := "dist/splunk_eventgen-${VERSION}.tar.gz"
EVENTGEN_TAG := "sa-eventgen"
CURTIME ?= $(shell date +%s)
EVENTGEN_TEST_IMAGE = "eventgen-test-container"
TESTS ?= large
TEST_ARGS += ${TESTS}
DESTROY_TEST ?= 0]
ENGINE_CONF_SOURCE ?= "https://repo.splunk.com/artifactory/Solutions/Common/misc/eventgen_engine.conf"

.PHONY: tests

all: egg

egg: clean
	python setup.py sdist

image: setup_eventgen egg
	cp dist/splunk_eventgen-*.tar.gz dockerfiles/splunk_eventgen.tgz
	cd dockerfiles && docker build . -t eventgen

clean:
	rm -rf dist *.egg-info *.log
	docker rmi ${EVENTGEN_TAG} || true

setup_eventgen:
	wget -O splunk_eventgen/default/eventgen_engine.conf ${ENGINE_CONF_SOURCE}

eg_network:
	docker network create --attachable --driver bridge eg_network || true

run_server: eg_network
	docker kill eg_server || true
	docker rm eg_server || true
	docker run --network eg_network --name eg_server -d -p 9500 -p 9501 eventgen:latest server

run_controller: eg_network
	docker kill eg_controller || true
	docker rm eg_controller || true
	docker run --name eg_controller --network eg_network --network-alias rabbitmq -d -p 5672 -p 15672 -p 9500 -p 9501 eventgen:latest controller
