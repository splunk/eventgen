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
	rm -rf dist
	docker rmi ${EVENTGEN_TAG} || true

setup_eventgen:
	wget ${ENGINE_CONF_SOURCE}
	mv eventgen_engine.conf splunk_eventgen/default/eventgen_engine.conf

run_server:
	cd splunk_eventgen && nameko run eventgen_nameko_server --config ./server_conf.yml

run_controller:
	cd splunk_eventgen && nameko run eventgen_nameko_controller --config ./controller_conf.yml
