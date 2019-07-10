DEBUG = True
class Constants():

    @property
    def PING_TIME(self):
        return 30 if not DEBUG else 3
    
    @property
    def BACKOFF_START(self):
        return 0.5
    
    @property
    def BACKOFF_MAX(self):
        return 120
