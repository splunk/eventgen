import logging
import time

import redis


class RedisConnector:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("eventgen_server")
        self.members_connection = redis.Redis(host=self.host, port=int(self.port), db=0)
        self.message_connection = redis.Redis(host=self.host, port=int(self.port), db=1)
        self.pubsub = self.message_connection.pubsub()
        self.logger.info("Initialized RedisConnector")
        self.servers_channel = "servers_channel"
        self.controller_channel = "controller_channel"
        self.retry_time_list = [5, 10, 20, 30, 60, 0]

    def register_myself(self, hostname, role="server"):
        for retry_time in self.retry_time_list:
            try:
                if role == "server":
                    self.members_connection.sadd("servers", hostname)
                    self.pubsub.subscribe(self.servers_channel)
                else:
                    self.members_connection.set("controller", hostname)
                    self.pubsub.subscribe(self.controller_channel)
                self.logger.info(
                    "Registered as {} and subscribed the channel.".format(role)
                )
                return
            except:
                self.logger.warning(
                    "Could not connect to Redis at {}:{}. Retrying in {} seconds.".format(
                        self.host, self.port, retry_time
                    )
                )
                if not retry_time:
                    raise Exception("Failed to connect to Redis.")
                time.sleep(retry_time)
                continue

    def get_registered_servers(self):
        for retry_time in self.retry_time_list:
            try:
                servers = list(self.members_connection.smembers("servers"))
                self.logger.info("Registered Servers: {}".format(servers))
                return servers
            except:
                self.logger.warning(
                    "Could not connect to Redis at {}:{}. Retrying in {} seconds.".format(
                        self.host, self.port, retry_time
                    )
                )
                if not retry_time:
                    raise Exception("Failed to connect to Redis.")
                time.sleep(retry_time)
                continue
