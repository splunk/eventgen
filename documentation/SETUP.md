## Install ##

Installing Eventgen is simple. There are 3 approaches to using Eventgen - as a container, as a PyPI module, or as a Splunk App. Follow the instructions below depending on your ideal use:

* Use Eventgen as a [Docker container](#container-installation)
* Use Eventgen as a [Splunk App](#splunk-app-installation)
* Use Eventgen as a [Python (PyPI) package](#pypi-installation)


---

##### Container Installation #####

First, you need to install the appropriate [Docker engine](https://docs.docker.com/engine/installation/#supported-platforms) for your operating system. Once you have Docker installed, you must login to [Artifactory](https://repo.splunk.com). For your first-time run, Eventgen requires that you be able to pull images from Artifactory. While connected to Splunk's private network (VPN, if you are remote), run the following commands:
```
$ docker login repo.splunk.com
$ docker pull repo.splunk.com/splunk/products/eventgenx:latest

# In order to simplify communication, create an overlay network to which the eventgen containers will be created.
$ docker network create --attachable --driver bridge eg_network

# Bring up a controller node
$ docker run -d -p 5672 -p 15672:15672 -p 9500:9500 --network eg_network --name eg_controller repo.splunk.com/splunk/products/eventgenx:latest controller

# Bring up a server node, and specifying a docker network will automatically connect server to the controller.
$ docker run -d -p 5672 -p 15672 -p 9500 --network eg_network -e EVENTGEN_AMQP_HOST="eg_controller" --name eg_server repo.splunk.com/splunk/products/eventgenx:latest server

# Confirm that controller is running correctly. If only one SERVER instance is running, you will only one item in connected servers.
$ curl 127.0.0.1:9500
*** Eventgen Controller ***
Host: <SOME_HOST_ID>
Connected Servers: [<SOME_SERVER_ID>]
You are running Eventgen Controller.
```

---

##### PyPI Installation #####

To use Eventgen as a PyPI module, you will need to download the package from [Artifactory](https://repo.splunk.com). While connected to Splunk's private network (VPN, if you are remote), run the following command:
```
$ pip install splunk_eventgen -i https://repo.splunk.com/artifactory/api/pypi/pypi-virtual/simple
```
If you run into any permission issues such as `OSError: [Errno 1] Operation not permitted`, try running it with `sudo`.

To verify Eventgen is properly installed, run "splunk_eventgen --version" on your system. You should see information about your current Eventgen version.
```
$ splunk_eventgen --version
Eventgen 0.6.0
```

---

##### Splunk App Installation #####

To use Eventgen as a Splunk app, you need a SPL file. In order to generate the SPL file, install Eventgen through PyPI with the instruction above.

Once you have Eventgen installed, run:

```
# This command generates spl file
splunk_eventgen build --destination <DESIRED_PATH_TO_OUTPUT_SPL_FILE>
```

With the generated SPL file, follow these steps to install.
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click "Install app from file".
3. Navigate to the path where your local SPL file is and select.
4. Restart Splunk after you have been notified of a successful installation.
5. Go to Settings>Data inputs.
5. Verify that SA-Eventgen shows up under Local inputs.

---

## Configure ##

Now you probably wonder about how much data should Eventgen send? Or where should Eventgen send data to? Or how does Eventgen send data? Or what type of data do you want Eventgen to send?
After Eventgen is installed in any of the forms mentioned above, it is time to configure Eventgen.
There are two key concepts behind the configuration process of Eventgen:

* `eventgen.conf`: This is a ini-style configuration file that Eventgen parses to set global, default, and even sample-specific settings. These settings include which plugin to use, how much data to send, and where to send it to. For more information, see [this section](TUTORIAL.md#the-configuration-file).
* `sample files`: This is a collection of text files that Eventgen will read on initiation. Samples act as templates for the raw data that Eventgen pumps out. As such, these templates can include tokens or specific replacement strings that will get modified during processing-time (ex. timestamps updated in real-time). For more information, see [this section](TUTORIAL.md#the-sample-file).

In addition, common use cases work around bundling these relevant files.
Because Eventgen configs can be tightly coupled with custom sample files, they can be bundled up into a package itself, in the format:
```
bundle/
	default/
		eventgen.conf
	samples/
		users.sample
		hosts.sample
		firewall.logs
```
If you have not read the sections below, please do so first and revisit bundling your files.

Based on your Eventgen installation, perform one of the following to set up Eventgen:

* Configuring Eventgen as a [Docker container](#container-setup)
* Configuring Eventgen as a [Splunk App](#splunk-app-setup)
* Configuring Eventgen as a [Python (PyPI) package](#pypi-setup)

---

##### Container Setup #####

The new Server-Controller architecture of Eventgen includes two roles:

* Controller (`eg_controller`): this serves as the broadcaster
* Server (`eg_server`): this serves as a single listener or worker

If you want to scale the local Eventgen cluster using this design, simply add another `eg_server` container call (using a different `--name`), and should automatically register with the `eg_controller`. *NOTE [container installation](#container-installation)

Controller-Server architecture is a RESTful service.
To interact with this architecture, you can make REST API calls against `eg_controller`.
When an appropriate request is made against `eg_controller`'s server port (9500), that action will be distributed to all the server nodes connected to it for easy orchestration.
This simplifies all interactions you need to make to properly setup a cluster. Some example cURL commands using `eg_controller`:

```
# Assuming that a controller is deployed to your localhost and wired to port 9500
$ curl http://localhost:9500
*** Eventgen Controller ***
Host: 06198584f5fc
Connected Servers: [u'98cfac1a8507']
You are running Eventgen Controller.

# This should show the status of your eg_server
$ curl http://localhost:9500/status
{
    "98cfac1a8507": {
        "EVENTGEN_STATUS": 0, 
        "CONFIGURED": false, 
        "CONFIG_FILE": "N/A", 
        "QUEUE_STATUS": {
            "WORKER_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }, 
            "SAMPLE_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }, 
            "OUTPUT_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }
        }, 
        "EVENTGEN_HOST": "98cfac1a8507"
    }
}

# Additionally, it's possible to target a specific node in your distributed Eventgen cluster by using the target keyword and eventgen_host variable
$ curl http://localhost:9500/status?target=98cfac1a8507
{
    "98cfac1a8507": {
        "EVENTGEN_STATUS": 0, 
        "CONFIGURED": false, 
        "CONFIG_FILE": "N/A", 
        "QUEUE_STATUS": {
            "WORKER_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }, 
            "SAMPLE_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }, 
            "OUTPUT_QUEUE": {
                "QUEUE_LENGTH": "N/A", 
                "UNFINISHED_TASK": "N/A"
            }
        }, 
        "EVENTGEN_HOST": "98cfac1a8507"
    }
}
```

Now you know how to communicate with and check the status of your Eventgen instances through Eventgen controller, let's pass in a config file.
When communicating with Eventgen controller, you need to translate your Eventgen configfile into a JSON representation.
```
# If you have an Eventgen Config ini file looking like below
[windbag]
generator = windbag
earliest = -3s
latest = now
interval = 5
count = 5
outputMode = stdout
end = 15
threading = process

# can be translated to:
{"windbag": {"generator": "windbag", "earliest": "-3s", "latest": "now", "interval": 5, "count": 5, "outputMode": "stdout", "end": 15, "threading": "process"}}

```
Basically in the JSON structure, first level is a stanza and the second level dictionary is a collection of key value pairs.

Let's pass in this JSON representation.
```
$ curl -X POST http://localhost:9500/conf -d '{"windbag": {"count": "5","end": "15","generator": "windbag","interval": "2","earliest": "-3s","latest": "now", "outputMode": "file", "fileName": "tutorial.txt"}}'
# Response comes back as JSON showing that Eventgen instance, 98cfac1a8507, is configured.
{
    "98cfac1a8507": {
        "windbag": {
            "count": "5",
            "end": "15",
            "generator": "windbag",
            "interval": "2",
            "fileName": "tutorial.txt",
            "outputMode": "file",
            "earliest": "-3s",
            "latest": "now"
        }
    }
}
# Let's confirm that your Eventgen instances are configured.
$ curl http://localhost:9500/status
{
    "98cfac1a8507": {
        "CONFIG_FILE": "/usr/lib/python2.7/site-packages/splunk_eventgen/default/eventgen_wsgi.conf",
        "CONFIGURED": true,
        "EVENTGEN_STATUS": 0,
        "EVENTGEN_HOST": "98cfac1a8507",
        "QUEUE_STATUS": {
            "WORKER_QUEUE": {
                "QUEUE_LENGTH": 0,
                "UNFINISHED_TASK": 0
            },
            "SAMPLE_QUEUE": {
                "QUEUE_LENGTH": 0,
                "UNFINISHED_TASK": 0
            },
            "OUTPUT_QUEUE": {
                "QUEUE_LENGTH": 0,
                "UNFINISHED_TASK": 0
            }
        },
        "TOTAL_VOLUME": 0.0
    }
}

$ curl http://localhost:9500/conf
{
    "98cfac1a8507": {
        "windbag": {
            "count": "5",
            "end": "15",
            "generator": "windbag",
            "interval": "2",
            "fileName": "tutorial.txt",
            "outputMode": "file",
            "earliest": "-3s",
            "latest": "now"
        }
    }
}

# Start Eventgen
$ curl http://localhost:9500/start -X POST

# Verify generated data
$ docker exec -it <YOUR_EVENTGEN_INSTANCE_ID> bash
$ ls
tutorial.txt
$ cat tutorial.txt
# There will be bunch of WINDBAG data like the one below
2018-02-10 03:10:30.927660 -0700 WINDBAG Event 1 of 5

```

Great, you have successfully configured your Eventgen using a controller. We have utilized basic endpoints such as /status or /conf in the tutorials but there are more endpoints.
Feel free to explore [Eventgen API Reference](REFERENCE.html#rest-api-reference)

### Bundling your conf and sample file ###

Using the concept of the bundling, if the bundle is packaged and hosted somewhere accessible for download, simply hit the /bundle API with a POST and a JSON including the URL of your bundle.
```
$ curl http://localhost:9500/bundle -X POST -d '{"url": "http://artifact.server.com/bundle.tgz"}'
Bundle event dispatched to all with url http://artifact.server.com/bundle.tgz
```

To verify that your bundle installation and configuration was successful, you can check the logs of the `eg_server` role, or run a GET against the /conf endpoint:
```
$ docker logs eg_server
2018-01-18 23:07:57,442 eventgen_listener INFO     MainProcess Download complete!
2018-01-18 23:07:57,444 eventgen_listener INFO     MainProcess Extracting bundle /opt/splunk/etc/apps/eg-bundle.tgz...
2018-01-18 23:07:57,468 eventgen_listener INFO     MainProcess Extraction complete!
2018-01-18 23:07:57,468 eventgen_listener INFO     MainProcess Detecting sample files...
2018-01-18 23:07:57,469 eventgen_listener INFO     MainProcess Moving sample files...
2018-01-18 23:07:57,484 eventgen_listener INFO     MainProcess Sample files moved!
2018-01-18 23:07:57,484 eventgen_listener INFO     MainProcess Detecting eventgen.conf...
2018-01-18 23:07:57,485 eventgen_listener INFO     MainProcess Reading eventgen.conf...
2018-01-18 23:07:57,487 eventgen_listener INFO     MainProcess set_conf method called with ...
```

```
$ curl http://localhost:9500/conf?target=6f654722f3d8
{
    "6f654722f3d8": {
        "auth_passwordless_ssh.nix": ...
    }
}
```

---

##### Splunk App Setup #####

Before you start, confirm that you have successfully installed SA-Eventgen app using this instruction [Splunk App Installation](#splunk-app-installation).

You should see SA-Eventgen App in SplunkWeb.
![Local Image](./images/splunk_web_sa_eventgen.png)

You should see SA-Eventgen as an input under Settings>Data inputs
![Local Image](./images/splunk_web_sa_eventgen_modinput.png)

Additionally, you'll see SA-Eventgen in your Splunk apps installation directory:
```
$ cd ${SPLUNK_HOME}/etc/apps
```

If SA-Eventgen App is correctly installed, there is no additional configuration required. SA-Eventgen app will automatically identify with any apps with Eventgen.conf and start generating data with that config when modinput is enabled.

If you wish you add your bundle so that modinput can detect your package:
Package your eventgen.conf and sample files into a directory structure as outlined above. After that's done, copy/move the bundle into your `${SPLUNK_HOME}/etc/apps/` directory and restart Splunk. If you have specific samples enabled in your eventgen.conf, you should see data streaming into the specified Splunk index.

---

##### PyPI Setup #####

The PyPI can be used in one of two ways: to run Eventgen from the command-line pointing to a specific configuration file, or to replicate the controller-server clustered architecture that the container is using.

### Command Line ###

Assuming you've followed the above steps on installing the PyPI, run the following command and point it to an eventgen.conf file:

```
# Invoke python module
$ python -m splunk_eventgen -v generate tests/sample_eventgen_conf/replay/eventgen.conf.replay

# Alternatively, you can use the `splunk_eventgen` alias
$ splunk_eventgen -v generate path/to/eventgen.conf
```

### Controller/Server Cluster ###

A quick preface on this mode of operation: due to it's complexity, this is only recommended if you're developing or comfortable with technical setups. Having said that, you can follow these instructions:

1. Install and run [RabbitMQ](https://www.rabbitmq.com/download.html) locally
2. Install [Eventgen PyPI module](SETUP.md#pypi-setup)
3. To set up a controller, run `splunk_eventgen service --role controller`
4. To set up a server, run `splunk_eventgen service --role server`
5. By default, the controller and server will try to locate RabbitMQ on pyamqp://localhost:5672 using credentials guest/guest and RabbitMQ's web UI at http://localhost:15672
6. You can change any of those parameters using the CLI - for instance, if your RabbitMQ is accessible on rabbit-mq.company.com with credentials admin/changeme you should run `splunk_eventgen service --role controller --amqp-host rabbit-mq.company.com --amqp-user admin --amqp-pass changeme`
7. Please see `splunk_eventgen service --help` for additional CLI options
8. **NOTE:** Running the controller and server on the same machine will cause port collisions for the Eventgen web server. To mitigate this, you can tell the server to run on a separate port using `splunk_eventgen service --web-server-address 0.0.0.0:9501`

---