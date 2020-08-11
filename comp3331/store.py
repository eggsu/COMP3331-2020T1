import time 
#borrowed website code from https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html

class Store():

    #overarching setting for setting up peer instances 
    __instance={
        'base_port': 12000
    }
    
    #return whole instance 
    def __new__(cls):
        return cls.__instance