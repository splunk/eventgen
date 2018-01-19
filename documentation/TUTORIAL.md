#Eventgen Tutorial

**New Server-Controller Architecture**

* Allows single controller to orchestrate all eventgen wsgi servers. This architecture allows eventgen servers to scale very easily.
* All Eventgen clusters require a single controller instance with RabbitMQ running
* Eventgen clusters can contain as many server instances as desired - they just all need to communicate with the same controller/message broker

**Running Eventgen**

This new Eventgen model can be brought up in several different ways. Please see the options below for how to configure your Eventgen cluster:

1. Use Docker
    * [Setup controllers and servers](SETUP.md#container-setup) using your local Docker client
    * For multiple servers, it's ideal to create all the containers in the same network. For instance:
    * `docker network create --attachable --driver bridge eg_network`
    * `docker run -d -p 5672 -p 15672 -p 9500 --network eg_network --name eg_controller repo.splunk.com/splunk/products/eventgenx:latest controller`
    * `docker run -d --p 5672 -p 15672 -p 9500 -e EVENTGEN_AMQP_HOST="eg_controller" --network eg_network --name eg_server repo.splunk.com/splunk/products/eventgenx:latest server`
    * For multiple servers, make sure you specify a different `--name` parameter to make server management easier
    * By default, Eventgen servers will use the container's hostname to identify itself with the controller. In a container, this will be random (ex: `75f966472253`). It's also recommended to add a `--hostname` parameter to your Docker run CLI so make management easier.

2. Using PyPI package
    * Install and run [RabbitMQ](https://www.rabbitmq.com/download.html) locally
    * Install [Eventgen PyPI module](SETUP.md#pypi-setup)
    * To standup a controller, run `splunk_eventgen service --role controller`
    * To standup a server, run `splunk_eventgen service --role server`
    * By default, the controller and server will try to locate RabbitMQ on pyamqp://localhost:5672 using credentials guest/guest and RabbitMQ's web UI at http://localhost:15672
    * You can change any of those parameters using the CLI - for instance, if your RabbitMQ is accessible on rabbit-mq.company.com with credentials admin/changeme you should run `splunk_eventgen service --role controller --amqp-host rabbit-mq.company.com --amqp-user admin --amqp-pass changeme`
    * Please see `splunk_eventgen service --help` for additional CLI options
    * NOTE: Running the controller and server on the same machine will cause port collisions for the Eventgen web server. To mitigate this, you can tell the server to run on a separate port using `splunk_eventgen service --web-server-address 0.0.0.0:9501`

3. Local machine + development setup
    * Install and run [RabbitMQ](https://www.rabbitmq.com/download.html) locally
    * Edit splunk_eventgen/controller_conf.yml to specify Eventgen web server port and RabbitMQ information
    * To standup the Eventgen controller node, inside of splunk_eventgen directory run: ```nameko run eventgen_nameko_controller --config ./controller_conf.yml```
    * Edit splunk_eventgen/server_conf.yml to specify Eventgen web server portand RabbitMQ information. You can optionally set ```EVENTGEN_NAME: {DESIRED_EVENTGEN_NAME}```. By default, eventgen hostname will be your machine's hostname.
    * To standup the Eventgen sserver node, inside of splunk_eventgen directory run: ```nameko run eventgen_nameko_server --config ./server_conf.yml```

**Controller APIs**

* Note, body will be always in json format. For example, {"target": "", "content": ""}

* ```GET /index```
* ```GET /status```
* ```POST /start```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
* ```POST /stop```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
* ```POST /restart```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
* ```GET /conf```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
* ```POST /conf```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
        * content={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will overwrite the existing config file with the content.
            * Format: {"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}.
                * For example, {"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}.
* ```PUT /conf```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
        * content={JSON_REPRESENTATION_OF_CONFIG_FILE}, it will only replace matching values in existing configfile.
            * Format: {"{SAMPLE}": {"{CONF_KEY}": "{CONF_VALUE}"}}.
                * For example, {"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}.
* ```POST /bundle```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
        * url={BUNDLE_URL}
            * Pass in a URL to an app/bundle of Eventgen files to seed configurations and sample files.
            * Format: {"url": "{BUNDLE_URL}"}
    * Example: curl http://localhost:9500/bundle -X POST -d '{"url": "http://artifact.server.com/eventgen-bundle.tgz "}'
* ```POST /setup```
    * body
        * target={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * If target is not passed in, DEFAULT value will be "all" which means all servers receive the request.
        * content={ARGUMENTS}, it will only replace matching values in existing configfile.
            * Format: {"mode": "", "hostname_template": "", "protocol": "", "key": "", "key_name": "", "password": "", "hec_port": "", "mgmt_port": "", "new_key": ""}.
                * Default values
                    * mode: "roundrobin"
                    * hostname_template: "idx{0}"
                    * protocol: "https"
                    * key: "00000000-0000-0000-0000-000000000000"
                    * key_name: "eventgen"
                    * password: "Chang3d!"
                    * hec_port: 8088
                    * mgmt_port: 8089
                    * new_key: True
