
#borrowed website code from https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
class Message():

    #instance of the peer's messages it may send over tcp/udp
    __instance={
    }
    
    #return whole instance 
    def __new__(cls):
        return cls.__instance