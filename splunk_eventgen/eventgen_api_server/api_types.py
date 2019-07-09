from enum import Enum

class ApiTypes(Enum):
    index = 'INDEX'
    status = 'STATUS'
    start = 'START'
    stop = 'STOP'
    restart = 'RESTART'
    get_conf = 'GET_CONF'
    set_conf = 'SET_CONF'
    edit_conf = 'EDIT_CONF'
    bundle = 'BUNDLE'
    setup = 'SETUP'
    get_volume = 'GET_VOLUME'
    set_volume = 'SET_VOLUME'
    reset = 'RESET'

            