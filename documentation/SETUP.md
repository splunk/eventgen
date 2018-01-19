## Install ##

Installing Eventgen is simple. There are 3 approaches to using Eventgen - as a container, as a PyPI module, or as a Splunk App. Follow the instructions below depending on your ideal use:

1. Use Eventgen as a [Docker container](#container-installation)
2. Use Eventgen as a [Splunk App](#splunk-app-installation)
3. Use Eventgen as a [Python (PyPI) package](#pypi-installation)


---

##### Container Installation #####

First and foremost, you'll need to install the appropriate [Docker engine](https://docs.docker.com/engine/installation/#supported-platforms) for your operating system. Once you have Docker installed, you must login to [Artifactory](https://repo.splunk.com). For your first-time run, Eventgen requires that you be able to pull images from Artifactory. While connected to Splunk's private network (VPN, if you are remote), run the following commands:
```
$ docker login repo.splunk.com
$ docker pull repo.splunk.com/splunk/products/eventgen:latest

# In order to simplify communication, create an overlay network to which the eventgen containers will be created
$ docker network create --attachable --driver bridge eg_network

# Bring up a controller node
$ docker run -d -p 5672 -p 15672:15672 -p 9500:9500 --network eg_network --name eg_controller repo.splunk.com/splunk/products/eventgenx:latest controller

# Bring up a server node, connecting it to the controller node
$ docker run -d --p 5672 -p 15672 -p 9500 --network eg_network -e EVENTGEN_AMQP_HOST="eg_controller" --name eg_server repo.splunk.com/splunk/products/eventgenx:latest server
```

---

##### Splunk App Installation #####

To use Eventgen as a Splunk app, download the TGZ/SPL file from [Artifactory](https://repo.splunk.com). Then, follow the instructions below on installing the app on top of an existing Splunk installation:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click "Install app from file"
3. Navigate to your Eventgen download, and upload the file
4. Restart Splunk after you have been notified of a successful installation

---

##### PyPI Installation #####

To use Eventgen as a PyPI module, you will need to download the package from [Artifactory](https://repo.splunk.com). While connected to Splunk's private network (VPN, if you are remote), run the following command:
```
$ pip install splunk-eventgen -i https://repo.splunk.com/artifactory/api/pypi/pypi/simple
```

To verify Eventgen is properly installed, run "splunk_eventgen --version" on your system. You should see information about your current Eventgen version.
```
$ splunk_eventgen --version
0.6.0
```

---

## Configure ##

Now that Eventgen is installed in any of the forms above, there's still the matter of configuring it. How much data should Eventgen send? Where should Eventgen send data to? How does Eventgen send data? What type of data do you want it to send? There are two key concepts behind the configuration process of Eventgen:

* `eventgen.conf`: This is a ini-style configuration file that Eventgen parses to set global, default, and even sample-specific settings. These settings include which plugin to use, how much data to send, and where to send it to. For more information, see [this section](TUTORIAL#the-configuration-file).
* `sample files`: This is a collection of text files that Eventgen will read on initiation. Samples act as templates for the raw data that Eventgen pumps out. As such, these templates can include tokens or specific replacement strings that will get modified during processing-time (ex. timestamps updated in real-time). For more information, see [this section](TUTORIAL#sample-files).

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

Using the terminology above, follow the instructions below on setting up Eventgen using your desired installation:

1. Configuring Eventgen as a [Docker container](#container-setup)
2. Configuring Eventgen as a [Splunk App](#splunk-app-setup)
3. Configuring Eventgen as a [Python (PyPI) package](#pypi-setup)

---

##### Container Setup #####

Following the example from above, the container architecture of Eventgen includes two roles:

* Controller/`eg_controller`: this serves as the broadcaster
* Server/`eg_server`: this serves as a single listener or worker

If you want to scale the local Eventgen cluster using this design, simply add another `eg_server` container call (using a different `--name`), and it should automatically register with the `eg_controller`. 

Using this design, you can make REST API calls against the `eg_controller`. When an appropriate request is made against the `eg_controller` server port (9500), that action will be distributed to all the server nodes connected to it allowing simplistic orchestration. This simplifies any and all interactions you need to make to properly setup a cluster. For example, see some example cURL commands below on using the `eg_controller`:

```
$ curl http://localhost:9500
*** Eventgen Controller ***
Host: c8df86e59376
You are running Eventgen Controller.
```

```
# This should show the status of your eg_server
$ curl http://localhost:9500/status
{
    "6f654722f3d8": {
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
        "EVENTGEN_HOST": "6f654722f3d8"
    }
}
```

```
# Additionally, it's possible to target a specific node in your distributed Eventgen cluster by using the target keyword
$ curl http://localhost:9500/status?target=6f654722f3d8
{
    "6f654722f3d8": {
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
        "EVENTGEN_HOST": "6f654722f3d8"
    }
}
```

Using the concept of the bundle from above, if the bundle is packaged and hosted somewhere accessible for download, simply hit the /bundle API with a POST and a JSON including the URL of your bundle.
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
2018-01-18 23:07:57,487 eventgen_listener INFO     MainProcess set_conf method called with
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

After you have restarted Splunk, you should see Eventgen as an app in SplunkWeb. Additionally, you'll see SA-Eventgen in your Splunk apps installation directory:
```
$ cd ${SPLUNK_HOME}/etc/apps
```

Using the concept of the bundle from above, you can package your eventgen.conf and sample files into a directory structure as outlined above. After that's done, copy/move the bundle into your `${SPLUNK_HOME}/etc/apps/` directory and restart Splunk. If you have specific samples enabled in your eventgen.conf, you should see data streaming into the specified Splunk index. 

Through the SplunkWeb UI, navigate to the Eventgen app. If Eventgen is working correctly, you'll also have visibility into Eventgen statistics, including real-time volume generated as well as the proportion of data sent based on sample used. If the charts are not populated, you can navigate to the logs to introspect the generator queues, output queues, and more debug information.

---

##### PyPI Setup #####

The PyPI can be used in one of two ways: to run Eventgen from the command-line pointing to a specific configuration file, or to replicate the controller-server clustered architecture that the container is using.

### Command Line ###

TODO

### Controller/Server Cluster ###

A quick preface on this mode of operation: due to it's complexity, this is only recommended if you're developing or comfortable with technical setups. Having said that, you can follow these instructions:

1. Install and run [RabbitMQ](https://www.rabbitmq.com/download.html) locally
2. Install [Eventgen PyPI module](SETUP.md#pypi-setup)
3. To standup a controller, run `splunk_eventgen service --role controller`
4. To standup a server, run `splunk_eventgen service --role server`
5. By default, the controller and server will try to locate RabbitMQ on pyamqp://localhost:5672 using credentials guest/guest and RabbitMQ's web UI at http://localhost:15672
6. You can change any of those parameters using the CLI - for instance, if your RabbitMQ is accessible on rabbit-mq.company.com with credentials admin/changeme you should run `splunk_eventgen service --role controller --amqp-host rabbit-mq.company.com --amqp-user admin --amqp-pass changeme`
7. Please see `splunk_eventgen service --help` for additional CLI options
8. **NOTE:** Running the controller and server on the same machine will cause port collisions for the Eventgen web server. To mitigate this, you can tell the server to run on a separate port using `splunk_eventgen service --web-server-address 0.0.0.0:9501`

---