'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
'''
import splunk.admin as admin
import splunk.entity as entity
    

class EventGenApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    
    def setup(self):
        #if self.requestedAction == admin.ACTION_EDIT:
        #    for arg in ['field_1', 'field_2_boolean', 'field_3']:
        #        self.supportedArgs.addOptArg(arg)
        pass

    def handleList(self, confInfo):
        confDict = self.readConfCtx('eventgen')
        if confDict != None:
            for stanza, settings in confDict.items():
                for key, value in settings.items():
                    if key != 'eai:acl':
                        confInfo[stanza].append(key, str(value))
                    else:
                        confInfo[stanza].setMetadata(key, value)
                    
# initialize the handler
admin.init(EventGenApp, admin.CONTEXT_APP_AND_USER)