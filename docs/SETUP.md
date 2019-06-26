## Install

There are multiple ways to use Eventgen, and you should choose the method that best fits your use case.
Below are the two major ways to use Eventgen - as a PyPI module and as a Splunk App. Follow the instructions below depending on your ideal use:

* Install / Use Eventgen as a [Splunk App](#splunk-app-installation)

    Benefits:
  * Easy To Install
  * Works with TA's downloaded direclty from SplunkBase
  * Uses a modular input for controlling the main Eventgen process
  * Reads configurations out of Splunk Rest
  * Supports apps default / local directories
  
  Draw Backs:
  * Limited to a single process
  * Can't scale to large datasets
  * Easily can fall behind on processing large quantities of eventgen.conf files
  * Doesn't install the jinja templating system automatically
  * No support for python multi-threading / processing

* Install / Use Eventgen as a [Python (PyPI) package](#pypi-installation)

    Benefits:
  * Support for threading / multiprocessing
  * Support for a centralized service that can controll and run multiple threading workers
  * Able to run a larger amount of datavolume with less overhead
  * Allows an Eventgen object to be embeded and controlled using python code
  * Exposes more of the plugin system
  * Includes/installs the Jinja2 templating engine
  
  Draw Backs:
  * More complex installation
  * You have to run the "build" command to produce a Splunk app
  * Harder to troubleshoot (especially in multiprocess mode)

---

## PyPI Installation / First Run

To use Eventgen as a PyPI module, you need to either download/clone the source code or install direct from github. 

###### Download Sourcecode
```
$ git clone https://www.github.com/splunk/eventgen
```
Depending on your desired case, you may wish to use a specific branch.  Eventgen's branching model will always have the "master" branch as the most stable and released version of Eventgen, while the "develop" branch will contain the bleeding edge codeline.
To select your codeline, simply checkout your desired branch (develop is selected by default).

```
$ git branch -a
* develop
  remotes/origin/HEAD -> origin/develop
  remotes/origin/develop
  remotes/origin/master
  
$ git checkout remotes/origin/master
Note: checking out 'remotes/origin/master'.

$ git pull
```

Then run below commands inside Eventgen directory:
```
$ python setup.py sdist

# you should see a tar file inside of dist directory
$ ls dist
splunk_eventgen-6.x.x.tar.gz

$ pip install splunk_eventgen-6.x.x.tar.gz

```
###### Install Direct From GitHub
To install Eventgen direct from github, use the following pip syntax:

```
$ pip install git+https://www.github.com/splunk/eventgen.git
```

###### Verify Installation

After completing either of the above install methods, you can verify seccussful installation by checking the packaged Eventgen version.
```
$ splunk_eventgen --version
Eventgen 6.x.x
```
Now you are ready to use Eventgen as a pip module.


#### First Run
##### Command Line ###

Assuming you've followed the above steps on installing the PyPI, run the following command and point it to an eventgen.conf file:

```
# Invoke python module
$ python -m splunk_eventgen -v generate tests/sample_eventgen_conf/replay/eventgen.conf.replay

# Alternatively, you can use the `splunk_eventgen` alias
$ splunk_eventgen -v generate path/to/eventgen.conf
```

##### Controller/Server Cluster ###

A quick preface on this mode of operation: due to its complexity, this is only recommended if you're developing or comfortable with technical setups. Having said that, you can follow these instructions:

1. Install and run [RabbitMQ](https://www.rabbitmq.com/download.html) locally
2. Install [Eventgen PyPI module](SETUP.md#pypi-setup)
3. To set up a controller, run `splunk_eventgen service --role controller`
4. To set up a server, run `splunk_eventgen service --role server`
5. By default, the controller and server will try to locate RabbitMQ on pyamqp://localhost:5672 using credentials guest/guest and RabbitMQ's web UI at http://localhost:15672.  If you're running another rabbitMQ server, you may error out.
6. You can change any of those parameters using the CLI - for instance, if your RabbitMQ is accessible on rabbit-mq.company.com with credentials admin/changeme you should run `splunk_eventgen service --role controller --amqp-host rabbit-mq.company.com --amqp-user admin --amqp-pass changeme`
7. Please see `splunk_eventgen service --help` for additional CLI options
8. **NOTE:** Running the controller and server on the same machine will cause port collisions for Eventgen web server. To mitigate this, you can tell the server to run on a separate port using `splunk_eventgen service --web-server-address 0.0.0.0:9501`

---

## Splunk App Installation / First Run

To use Eventgen as a Splunk app, you need a SPL file. This SPL file can be obtained in one of two ways:
1. Through running the "build" process of the splunk_eventgen pypi module
2. Downloading the SPL direct from [splunkbase](https://splunkbase.splunk.com/app/1924/): 

###### Gerating the SPL file
In order to generate the SPL file, install Eventgen through PyPI with the instruction above.
Once you have Eventgen installed, run:

```
# This command generates spl file
$ splunk_eventgen build --destination <DESIRED_PATH_TO_OUTPUT_SPL_FILE>
```

###### Finishing the Install
With the generated / downloaded SPL file, follow these steps to install:
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click "Install app from file".
3. Navigate to the path where your local SPL file is and select.
4. Restart Splunk after you have been notified of a successful installation.

Before you start Eventgen, confirm that you have successfully installed SA-Eventgen: 

You should see SA-Eventgen App in SplunkWeb.
![Local Image](./images/splunk_web_sa_eventgen.png)

You should see SA-Eventgen as an input under Settings>Data inputs
![Local Image](./images/splunk_web_sa_eventgen_modinput.png)

Additionally, you'll see SA-Eventgen in your Splunk apps installation directory:
```
$ cd ${SPLUNK_HOME}/etc/apps
```

### First Run
If SA-Eventgen App is correctly installed, there is no additional configuration required. SA-Eventgen app will automatically identify with any apps with eventgen.conf.

To start generating data, simply enable the SA-Eventgen modinput by going to Settings > Data Inputs > SA-Eventgen and by clicking "enable" on the default modular input stanza.

If you wish you add your bundle so that the modinput can detect your package:
Package your eventgen.conf and sample files into a directory structure as outlined in the [configuration](CONFIGURE.md). After that's done, copy/move the bundle into your `${SPLUNK_HOME}/etc/apps/` directory and restart Splunk. If you have specific samples enabled in your eventgen.conf, you should see data streaming into the specified Splunk index.

Make sure the bundle app permission is global. You can config this in two ways:
* Log in to Splunk Web and navigate to Apps > Manage Apps. Find the bundle app row and set the permission to 'Global' on the Sharing column.
* Create a folder `metadata` under the bundle with file `default.meta` and add the following content:
```
[]
export=system
```

---
