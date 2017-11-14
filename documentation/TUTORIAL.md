#Eventgen Tutorial

**New Server-Controller Architecture**

* Allows single controller to orchestrate all eventgen wsgi servers. This architecture allows eventgen servers to scale very easily.

**How to start server-controller architecture**

1. Use Orca
    * ```orca create --egx {NUM_OF_DESIRED_EVENTGEN_SERVER}```
    * Above command should automatically configure servers and controller for you. You can start making requests against your controller address.

2. Manual setup
    * Start rabbitMQ. Make sure your rabbitMQ ports are available.
    * Edit splunk_eventgen/controller_conf.yml to specify your port and rabbitMQ location.
    * Inside of splunk_eventgen directory, run ```nameko run eventgen_nameko_controller --config ./controller_conf.yml```
    * Edit splunk_eventgen/server_conf.yml to specify your port. You can optionally put ```EVENTGEN_NAME: {DESIRED_EVENTGEN_NAME}```. By default, eventgen hostname will be your environment hostname.
    * Inside of splunk_eventgen directory, run ```nameko run eventgen_nameko_server --config ./server_conf.yml```


**Controller APIs**

* ```GET /index```
* ```GET /status```
* ```POST /start```
    * body
        * nodes={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * Otherwise, sends start request to all servers.
* ```POST /stop```
    * body
        * nodes={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * Otherwise, sends stop request to all servers.
* ```POST /restart```
    * body
        * nodes={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * Otherwise, sends stop request to all servers.
* ```GET /conf```
    * body
        * nodes={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * Otherwise, sends stop request to all servers.
* ```POST /conf```
    * body
        * nodes={EVENTGEN_SERVER_NAME} if you want to target an individual server
            * Otherwise, sends stop request to all servers by default.
        * conf="PATH_TO_CONF_FILE"
            * For example, conf="tests/sample_eventgen_conf/windbag/eventgen.conf.windbag".
        * conf={"{SAMPLE}": conf={"{CONF_KEY}": "{CONF_VALUE}"}}.
            * For example, {"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}.
