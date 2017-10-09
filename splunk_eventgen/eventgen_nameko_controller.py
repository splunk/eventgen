from nameko.standalone.rpc import ClusterRpcProxy

CONFIG = {'AMQP_URI': "amqp://guest:guest@localhost"}

def compute():
    with ClusterRpcProxy(CONFIG) as rpc:
        print(rpc.eventgen_api_server.index())
        print(rpc.eventgen_api_server.get_conf())
        print(rpc.eventgen_api_server.set_conf("tests/sample_eventgen_conf/windbag/eventgen.conf.windbag"))
        print(rpc.eventgen_api_server.status())
        print(rpc.eventgen_api_server.get_conf())
        print(rpc.eventgen_api_server.start())

compute()
