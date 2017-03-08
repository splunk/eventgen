# ORCA

ORCA is a command-line utility that uses container technology to make it easy to spin up Splunk environments for development, functional, performance and user acceptance testing.

[ORCA in Confluence](https://confluence.splunk.com/display/PROD/Orca+-+Splunk+Orchestration+and+Automation+Tool)

* [Getting Started with Orca](https://confluence.splunk.com/display/PROD/Getting+Started+with+Orca)
* [Creating Stacks with Orca](https://confluence.splunk.com/display/PROD/Creating+Stacks+with+Orca)
* [UCP and Local Mode](https://confluence.splunk.com/display/PROD/ORCA+-+UCP+and+Local+Mode)
* [Orca for Developers](https://confluence.splunk.com/display/PROD/Orca+for+Developers)
* [ORCA ERD](https://confluence.splunk.com/display/PROD/Orca+-+Splunk+Orchestration+and+Automation+Tool+ERD)

Help can also be found in the #orca HipChat room.


1. Installation:
===============
    From the /orca directory, run:

    `python setup.py bdist_wheel`

	NOTE: If you have any problems running the above command, check the version of your pip (to 8.1.2 or later) and your setuptools (to 28.2.0 or later) 
    
    To create the wheels package. Then from /orca/dist run:

    `sudo pip install --upgrade splunk_orca-0.[version].0-py2-none-any.whl`

    To install splunk_orca as a library.
