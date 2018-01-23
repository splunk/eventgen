#!/usr/bin/python

import os
import docker
import argparse


# Default constraints so that services are only scheduled on test nodes
DEFAULT_CONSTRAINTS = ["engine.labels.com.splunk.orca.workload.test==true"]
# Default labels so that services are only scheduled on test nodes
DEFAULT_LABELS = {
					"com.splunk.orca.performance": "false",
					"com.splunk.orca.workload.perf": "false",
					"com.splunk.orca.workload.build": "false",
					"com.splunk.orca.workload.test": "true",
					"com.docker.ucp.access.label": "test"
				 }


class EventgenDocs(object):

	# Default constraints so that services are only scheduled on test nodes
	DEFAULT_CONSTRAINTS = ["engine.labels.com.splunk.orca.workload.test==true"]
	# Default labels so that services are only scheduled on test nodes
	DEFAULT_LABELS = {
						"com.splunk.orca.performance": "false",
					  	"com.splunk.orca.workload.perf": "false",
					  	"com.splunk.orca.workload.build": "false",
					  	"com.splunk.orca.workload.test": "true",
					  	"com.docker.ucp.access.label": "test"
					  }

	def __init__(self, args):
		self.certs = args.certs
		if "~" in self.certs:
			self.certs = os.path.expanduser(self.certs)
		self.base_url = args.base_url
		self.name = args.name
		self.image = args.image
		self.replicas = args.replicas
		self.init_client()

	def init_client(self):
		self.tls_config = docker.tls.TLSConfig(client_cert=(os.path.join(self.certs, 'cert.pem'),
	                                 			   			os.path.join(self.certs, 'key.pem')),
	                    			  		   ca_cert=os.path.join(self.certs, 'ca.pem'),
	                    			  		   verify=os.path.join(self.certs, 'ca.pem'))
		self.client = docker.APIClient(base_url=self.base_url,
									   tls=self.tls_config, 
									   timeout=1800, 
									   version="1.26")

	def setup_config(self):
		container_spec = docker.types.ContainerSpec(image=self.image)
		placement = docker.types.Placement(constraints=DEFAULT_CONSTRAINTS)
		task_template = docker.types.TaskTemplate(container_spec=container_spec, placement=placement)
		service_mode = docker.types.ServiceMode(mode="replicated", replicas=self.replicas)
		endpoint_spec = docker.types.EndpointSpec(ports={14001:4000})
		update_config = docker.types.UpdateConfig(parallelism=1, delay=15, failure_action="continue")
		return  {
					"TaskTemplate": task_template,
					"ServiceMode": service_mode,
					"EndpointSpec": endpoint_spec,
					"UpdateConfig": update_config
				}

	def update_documentation(self):
		found_services = self.client.services(filters={"name": self.name})
		#print found_services
		if found_services and len(found_services) > 1:
			print "Too many services found - please double-check --name and try again."
		else:
			config = self.setup_config()
			if not found_services or len(found_services) == 0:
				print 'Service "{}" NOT found - starting new service...'.format(self.name)
				self.client.create_service(task_template=config["TaskTemplate"],
									   	   name=self.name,
									   	   labels=DEFAULT_LABELS,
									   	   mode=config["ServiceMode"],
									   	   update_config=config["UpdateConfig"],
									   	   endpoint_spec=config["EndpointSpec"])
				print 'Service "{}" created!'.format(self.name)
			elif len(found_services) == 1:
				print 'Service "{}" found - updating existing service...'.format(self.name)
				# Get version and increment by one, as required by update_service API
				version = found_services[0]["Version"]["Index"]
				name = found_services[0]["Spec"]["Name"]
				self.client.update_service(service=found_services[0]["ID"],
										   version=version,
										   task_template=config["TaskTemplate"],
									   	   labels=DEFAULT_LABELS,
									   	   name=name,
									   	   mode=config["ServiceMode"],
									   	   update_config=config["UpdateConfig"],
									   	   endpoint_spec=config["EndpointSpec"])
				print 'Service "{}" updated!'.format(name)


if __name__ == "__main__":
	# Parse arguments
	parser = argparse.ArgumentParser(prog='ORCA Docs',
                                     description='Build and push docs')
	parser.add_argument('--base-url', type=str, default="tcp://ucp.splunk.com:443", help='Specify UCP URL')
	parser.add_argument('--certs', type=str, required=True, help='Specify path to UCP certs')
	parser.add_argument('--name', type=str, default="eventgendocs", help='Specify service name')
	parser.add_argument('--image', type=str, default="stg-repo.splunk.com/tonyl/eventgen-docs:latest", help='Specify image used')
	parser.add_argument('--replicas', type=int, default=3, help='Specify replica count')
	args = parser.parse_args()

	# Initialize ORCA docs service manager
	docs = EventgenDocs(args)
	docs.update_documentation()
