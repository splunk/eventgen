import redis
import logging

class RedisConnector():

    def __init__(self, host, port):
        self.logger = logging.getLogger('eventgen_server')
        self.members_connection = redis.Redis(host=host, port=int(port), db=0)
        self.message_connection = redis.Redis(host=host, port=int(port), db=1)
        self.pubsub = self.message_connection.pubsub()
        self.logger.info("Initialized RedisConnector")
        self.servers_channel = 'servers_channel'
        self.controller_channel = 'controller_channel'
    
    def register_myself(self, hostname, role="server"):
        if role == "server":
            self.members_connection.sadd("servers", hostname)
            self.pubsub.subscribe(self.servers_channel)
        else:
            self.members_connection.set("controller", hostname)
            self.pubsub.subscribe(self.controller_channel)
        self.logger.info("Registered as {} and subscribed the channel.".format(role))
    
    def get_registered_servers(self):
        servers = list(self.members_connection.smembers("servers"))
        self.logger.info(servers)
        return servers


