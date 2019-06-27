VERSION := `grep '^__version__[^"]*"\([0-9.]*\)"' splunk_eventgen/__init__.py | sed -e 's/.*"\([0-9.]*\)".*/\1/'`
EVENTGEN_EGG := "dist/splunk_eventgen-${VERSION}.tar.gz"
EVENTGEN_TAG := "sa-eventgen"
CURTIME ?= $(shell date +%s)
EVENTGEN_TEST_IMAGE = "eventgen-test-container"
TESTS ?= large
TEST_ARGS += ${TESTS}
ENGINE_CONF_SOURCE ?= "https://raw.githubusercontent.com/splunk/eventgen/develop/splunk_eventgen/default/eventgen.conf"
SMALL ?= 'tests/small'
MEDIUM ?= 'tests/medium'
LARGE ?= 'tests/large'
XLARGE ?= 'tests/xlarge'
NEWLY_ADDED_PY_FILES = $(shell git ls-files -o --exclude-standard | grep -E '\.py$$')
CHANGED_ADDED_PY_FILES = $(shell git ls-files -mo --exclude-standard | grep -E '\.py$$')

.PHONY: tests, lint, format, docs

all: egg

egg: clean
	python setup.py sdist

image: setup_eventgen egg
	rm splunk_eventgen/default/eventgen_engine.conf || true
	docker build -f dockerfiles/Dockerfile . -t eventgen

test: egg image test_helper run_tests test_collection_cleanup

test_helper:
	docker run -d -t --net=host -v /var/run/docker.sock:/var/run/docker.sock --name ${EVENTGEN_TEST_IMAGE} eventgen:latest cat

	@echo 'Creating dirs needed for tests'
	docker exec -i ${EVENTGEN_TEST_IMAGE} /bin/sh -c "mkdir -p $(shell pwd) " || true

	@echo 'Copying orca tree into the orca container'
	docker cp . ${EVENTGEN_TEST_IMAGE}:$(shell pwd) || true

	@echo 'Verifying contents of pip.conf'
	docker exec -i ${EVENTGEN_TEST_IMAGE} /bin/sh -c "cd $(shell pwd); pip install dist/splunk_eventgen*.tar.gz" || true

	@echo 'Installing test requirements'
	docker exec -i ${EVENTGEN_TEST_IMAGE} /bin/sh -c "pip install -r $(shell pwd)/tests/requirements.txt" || true

	@echo 'Installing docker-compose'
	sudo curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
	sudo chmod +x /usr/local/bin/docker-compose

run_tests:
	@echo 'Running the super awesome tests'
	docker exec -i ${EVENTGEN_TEST_IMAGE} /bin/sh -c "cd $(shell pwd); python tests/run_tests.py ${SMALL} ${MEDIUM} ${LARGE} ${XLARGE}" || true

test_collection_cleanup:
	@echo 'Collecting results'
	#TODO: Should be paramaterized or generalized so that we don't need to add this here
	docker cp ${EVENTGEN_TEST_IMAGE}:$(shell pwd)/tests/test-reports/tests_small_results.xml tests/test-reports/tests_small_results.xml || echo "no tests_small_results.xml"
	docker cp ${EVENTGEN_TEST_IMAGE}:$(shell pwd)/tests/test-reports/tests_medium_results.xml tests/test-reports/tests_medium_results.xml || echo "no tests_medium_results.xml"
	docker cp ${EVENTGEN_TEST_IMAGE}:$(shell pwd)/tests/test-reports/tests_large_results.xml tests/test-reports/tests_large_results.xml || echo "no tests_large_results.xml"
	docker cp ${EVENTGEN_TEST_IMAGE}:$(shell pwd)/tests/test-reports/tests_xlarge_results.xml tests/test-reports/tests_xlarge_results.xml || echo "no tests_xlarge_results.xml"

	docker cp ${EVENTGEN_TEST_IMAGE}:$(shell pwd)/htmlcov htmlcov || echo "no htmlcov folder"

	@echo 'Stopping test container'
	docker stop ${EVENTGEN_TEST_IMAGE} || true

clean:
	rm *.spl || true
	rm -rf dist *.egg-info *.log *.xml || true
	rm splunk_eventgen/logs/*.log || true
	rm tests/test-reports/*.xml || true
	rm -rf .idea || true
	rm -rf _book || true
	rm -rf docs/_book || true
	rm -rf node_modules || true
	rm -rf docs/node_modules || true
	rm splunk_eventgen/default/eventgen_wsgi.conf || true
	find . -name "*.pyc" -type f -delete || true
	find . -name "*.log" -type f -delete || true
	find . -name "*.pyc" -type f -delete || true
	docker stop ${EVENTGEN_TEST_IMAGE} || true
	docker rm ${EVENTGEN_TEST_IMAGE} || true
	docker network rm eg_network || true
	docker network rm eg_network_test || true

setup_eventgen:
	curl -O splunk_eventgen/default/eventgen_engine.conf ${ENGINE_CONF_SOURCE}

eg_network:
	docker network create --attachable --driver bridge eg_network || true

run_server: eg_network
	docker kill eg_server || true
	docker rm eg_server || true
	docker run --network eg_network --name eg_server -e EVENTGEN_AMQP_HOST="eg_controller" -d -p 9501:9500 eventgen:latest server

run_controller: eg_network
	docker kill eg_controller || true
	docker rm eg_controller || true
	docker run --name eg_controller --network eg_network -d -p 5672:5672 -p 15672:15672 -p 9500:9500 eventgen:latest controller

docs:
	cd docs/; bundle install; bundle exec jekyll serve

build_spl: clean
	python -m splunk_eventgen build --destination ./

lint:
ifeq ($(NEWLY_ADDED_PY_FILES), )
	@echo 'No newly added python files. Skip...'
else
	@flake8 $(NEWLY_ADDED_PY_FILES) || true
endif
	@git diff -U0 -- '*.py' | flake8 --diff || true

format:
ifeq ($(CHANGED_ADDED_PY_FILES), )
	@echo 'No changed python files. Skip...'
else
	@isort $(CHANGED_ADDED_PY_FILES)
endif
ifeq ($(NEWLY_ADDED_PY_FILES), )
	@echo 'No newly added python files. Skip...'
else
	@yapf -i $(NEWLY_ADDED_PY_FILES)
endif

lint-all:
	@flake8 .

format-all:
	@isort -rc .
	@yapf -r -i .
