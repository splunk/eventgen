## Install ##

Installing Eventgen is simple. There are two approaches to using Eventgen - as a container, or as a PyPI module. Follow the instructions below depending on your ideal use:

1. Install the appropriate [Docker engine](https://docs.docker.com/engine/installation/#supported-platforms) for your operating system
2. Use Eventgen as a [Docker container](#container-installation)
3. Use Eventgen as a [Python (PyPI) package](#pypi-installation)

##### Container Installation #####

Once you have Docker installed, you must login to [Artifactory](https://repo.splunk.com). For your first-time run, Eventgen requires that you be able to pull images from Artifactory. While connected to Splunk's private network (VPN, if you are remote), run the following commands:
```
$ docker login repo.splunk.com
$ docker pull repo.splunk.com/splunk/products/eventgen:latest

# To bring up a container
$ docker run -d -p 2222 -p 5672 -p 15672 -p 9500 -p 9501repo.splunk.com/splunk/products/eventgen:latest master
```

##### PyPI Installation #####

To use Eventgen as a PyPI module, you will need to download the package from [Artifactory](https://repo.splunk.com). While connected to Splunk's private network (VPN, if you are remote), run the following command:
```
$ pip install splunk-eventgen -i https://repo.splunk.com/artifactory/api/pypi/pypi/simple
```

##### Verifying Installation #####

To verify Eventgen is properly installed, run "splunk_eventgen --version" on your system. You should see information about your current Eventgen version.
```
$ splunk_eventgen --version
0.6.0
```
---
