## Install ##

Installing Eventgen is simple. There are 3 approaches to using Eventgen - as a container, as a PyPI module, or as a Splunk App. Follow the instructions below depending on your ideal use:

1. Use Eventgen as a [Docker container](#container-installation)
2. Use Eventgen as a [Python (PyPI) package](#pypi-installation)
3. Use Eventgen as a [Splunk App](#splunk-app-installation)

---

##### Container Installation #####

First and foremost, you'll need to install the appropriate [Docker engine](https://docs.docker.com/engine/installation/#supported-platforms) for your operating system. Once you have Docker installed, you must login to [Artifactory](https://repo.splunk.com). For your first-time run, Eventgen requires that you be able to pull images from Artifactory. While connected to Splunk's private network (VPN, if you are remote), run the following commands:
```
$ docker login repo.splunk.com
$ docker pull repo.splunk.com/splunk/products/eventgen:latest

# In order to simplify communication, create an overlay network to which the eventgen containers will be created
$ docker network create --attachable --driver bridge eg_network

# Bring up a controller node
$ docker run -d -p 5672 -p 15672 -p 9500 --network eg_network --name eg_controller repo.splunk.com/splunk/products/eventgenx:latest controller

# Bring up a server node, connecting it to the controller node
$ docker run -d --p 5672 -p 15672 -p 9500 --network eg_network -e EVENTGEN_AMQP_HOST="eg_controller" --name eg_server repo.splunk.com/splunk/products/eventgenx:latest server
```

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

##### Splunk App Installation #####

To use Eventgen as a Splunk app, download the TGZ/SPL file from [Artifactory](https://repo.splunk.com). Then, follow the instructions below on installing the app on top of an existing Splunk installation:

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click "Install app from file"
3. Navigate to your Eventgen download, and upload the file
4. Restart Splunk after you have been notified of a successful installation

---

## Configure ##

Now that Eventgen is installed in any of the forms above, there's still the matter of configuring it. How much data should Eventgen send? Where should Eventgen send data to? How does Eventgen send data? What type of data do you want it to send? There are two key concepts behind the configuration process of Eventgen:

* `sample files`: This is a collection of text files that Eventgen will read on initiation. Samples act as templates for the raw data that Eventgen pumps out. As such, these templates can include tokens or specific replacement strings that will get modified during processing-time (ex. timestamps updated in real-time)
* `eventgen.conf`: This is a ini-style configuration file that Eventgen parses to set global, default, and even sample-specific settings. These settings include which plugin to use, how much data to send, and where to send it to.

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
2. Configuring Eventgen as a [Python (PyPI) package](#pypi-setup)
3. Configuring Eventgen as a [Splunk App](#splunk-app-setup)

---

##### Container Setup #####



---

##### PyPI Setup #####

TODO

---

##### Splunk App Setup #####

After you have restarted Splunk, you should see Eventgen as an app in SplunkWeb. Additionally, you'll see SA-Eventgen in your Splunk apps installation directory:
```
$ cd ${SPLUNK_HOME}/etc/apps
```

Using the concept of the bundle from above, you can package your eventgen.conf and sample files into a directory structure as outlined above. After that's done, copy/move the bundle into your `${SPLUNK_HOME}/etc/apps/` directory and restart Splunk. If you have specific samples enabled in your eventgen.conf, you should see data streaming into the specified Splunk index. 

Through the SplunkWeb UI, navigate to the Eventgen app. If Eventgen is working correctly, you'll also have visibility into Eventgen statistics, including real-time volume generated as well as the proportion of data sent based on sample used. If the charts are not populated, you can navigate to the logs to introspect the generator queues, output queues, and more debug information.

---
