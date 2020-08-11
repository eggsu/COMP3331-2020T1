#Edlyn Liew, z5161709
from socket import *
from ping import udpServer, udpClient, tcpServer,tcpClient
from Peers import peerMap
import os
from store import Store
import time
import threading
from messages import Message
import re

"""
this program establishes a p2p network.
it checks the peer's status through udp network 
it sends information and requests over a tcp network
instances of the peers are set up using classes 
"""


def main():
    
    if (sys.argv[1] == "init"):       
        Store()['status'] = "Running"
        Store()['ping_interval']=sys.argv[5]
        Store()['peerID']=sys.argv[2]
        successors=[sys.argv[3], sys.argv[4]]
        Store()['peer_instance']=peerInstancePing(sys.argv[1], Store()['peerID'],successors)
        Store()['Join Status'] = "Not Joined"

    if (sys.argv[1]== "join"):
        Store()['status'] = "Running"
        Store()['ping_interval']=sys.argv[4]
        Store()['peerID']=sys.argv[2]
        knownPeer=sys.argv[3]
        Store()['Join Status'] = "Joined"
        Store()['peer_instance']=peerInstancePing(sys.argv[1],Store()['peerID'],knownPeer)
    while True:
        user_input=input()
        if (user_input=="Quit"):
            Store()['status']="Quit"
            #send to tcp to let know of departure change 
            Store()['peer_instance'].departureChange(2)
            print("Quit")
            sys.exit(0)
        if (user_input.find('Store')!=-1 or user_input.find('Request')!=-1):
            #search through current directory to find the extension filename

            filename=int(re.findall('\d+', user_input)[0])
            Message()['filenameWExt']='None'
            for root,dirs,files in os.walk("."): 
                for fileName in files: 
                    if (fileName.find(str(filename))!=-1):
                        Message()['filenameWExt'] = fileName
            
            if (Message()['filenameWExt'] !="None"):
                locationToFind = filename%256 
                Message()['filename'] = filename

                if (user_input.find('Store')!=-1):
                    Message()['location storage Peer'] = locationToFind
                    Store()['peer_instance'].dataInsertRetrieve(4)
                else:
                    Message()['location find Peer'] = locationToFind
                    Store()['peer_instance'].dataInsertRetrieve(5)
            else:
                print("Error - File not found")


      
#creates instance of a Peer in which holds 
#the pinging, joining, exiting conditions as well as messages it will send to other Peers 
class peerInstancePing():
    def __init__(self,runType, peerId, otherPeers):

        self.peer=peerMap(peerId)
        self.peerId=peerId
        self.runType=runType
        self.otherPeers=otherPeers
        self.joinRequestChange = False

        #start pinging
        self.ping_successors()

    def ping_successors(self):

        if (self.runType=="init"):
            first_successor=self.otherPeers[0]
            second_successor=self.otherPeers[1]
            self.joinRequestChange = False
            Message()['first successor'] = first_successor
            Message()['second successor'] = second_successor
            
            print("Ping requests sent to Peers "+first_successor+" and " +second_successor)
           
        if (self.runType=="join"):
            Message()['knownPeerId']=self.otherPeers[0] #known peer already joined
            Message()['joiningPeerId']=self.peerId
    
            #print("Peer " + self.peerId+" Requesting to Join...")
            
            checkPeerAgainst=self.otherPeers[0]
            while True: #if not joined yet 
                self.joining = tcpClient(checkPeerAgainst,0)
                self.joining.start()
                self.joining.join()

                #exit if joined
                if (self.joining.joinedFlag!=-1):
                    break
                
                checkPeerAgainst=int(self.joining.peerForwardTo)



                #forwarding requests onto successor until the next successor num
                #is greater than the joining request peer id 
                #set the predecessor of first peer with the known peer 
            Message()['prevNewFirstSucc'] = self.joining.first_succ
            Message()['prevNewSecondSucc'] = Message()['joiningPeerId']
            Message()['nextSuccessorPort'] = self.joining.peerForwardTo #this value is the 2nd successor of Joining Peer 
            Message()['firstSuccessorPort'] = self.joining.joinFirst_succ #this value is the first successor of Joining Peer 
            
            self.joining = tcpClient(self.joining.prevPeer,1)
            self.joining.start()
            self.joining.join()
            
            #get successor numbers 
            first_successor=  Message()['firstSuccessorPort']
            second_successor=  Message()['nextSuccessorPort']
            self.otherPeers=[first_successor,second_successor]
            self.joinRequestChange = True
            print("Join request has been accepted")
            print("My first successor is Peer "+ str(first_successor))
            print("My second successor is Peer "+ str(second_successor))
        

        #pinging the successors over udp
        self.ping_server =udpServer()
        self.ping_server.daemon= True
        self.ping_server.start()
        
        self.tcp_server=tcpServer()
        self.tcp_server.daemon=True
        self.tcp_server.start()

        self.threads=self.udpPing()
    


    def udpPing(self):

        threads=[]
        successors=self.otherPeers
        i = 1

        for s in successors:
            if (self.joinRequestChange == True):
                pingInstance = udpClient(s, self.peerId,i,1)
            else: 
                pingInstance = udpClient(s, self.peerId,i,0)
            threads.append(pingInstance)

            #add successor ping instances 
            #lists in  successor lists contains the udp object 
            #the successor number (whether it is first/second)
            #and the successor port number 
            self.add_successor([pingInstance,i,s])
            i = i+1
        return threads


#flagtype == 5: for requesting files 
#flagtype == 4: for storing files
    def dataInsertRetrieve(self,flagType):
        checkPeerAgainst = self.peerId

        if (flagType == 5):
            print("File request for "+ str(Message()['filename'])+ " has been sent to my successor")

        while True: 
            self.data = tcpClient(checkPeerAgainst,flagType)
            self.data.start()
            self.data.join()

            #if this is insertion
            if (flagType == 4):
                if (self.data.storeFlag!=-1):
                    break
            if (flagType == 5): 
                if (self.data.retrieveFlag!=-1):
                    break
            
            checkPeerAgainst=int(self.data.peerForwardTo)



    #typeDeparture = 2: graceful
    #typeDeparture = 3; aborting 
    def departureChange(self, typeDeparture):        
        peerDeparting = self.peer
        #get the predecessor

        predPeer = peerDeparting.get_predecessor()
        if (predPeer == None):
            return
        #get new successor
        firstSuccess = peerDeparting.get_successor(0).successorId
        secondSuccess = peerDeparting.get_successor(1).successorId
        Message()['New first successor'] = firstSuccess
        Message()['New second Successor'] = secondSuccess
        Message()['Num update'] = 1
        self.departing1 = tcpClient(predPeer,typeDeparture)
        self.departing1.start()
        self.departing1.join()

        #from the previous TCP get the previous of departing 1

        self.secondUpdatePeer = int(self.departing1.prevPeerDepart)
        Message()['New first successor'] = predPeer
        Message()['New second Successor'] = firstSuccess
        Message()['Num update'] = 2
        self.departing2 = tcpClient(self.secondUpdatePeer,typeDeparture)
        self.departing2.start()
        self.departing2.join()
    #send over tcp 


    #below is a list of the getters and setters of the Peer instance's successors,files and predecessors 
    #The class it is referring to is in Peers.py
    def add_successor(self, pingInstance):
        self.peer.add_successor(pingInstance)

    def add_pred(self, peerId):
        return self.peer.add_predecessor(peerId)
    
    def get_predecessor(self):
        return self.peer.get_predecessor()
    
    #get first or second successor based on pos 
    def get_successor(self,pos):
        return self.peer.get_successor(pos)

    def get_all_successors(self):
        return self.peer.get_all_successors()
 
    def remove_successorPos(self,pos):
        self.peer.rem_successorPos(pos)

    def remove_successorNum(self,num):
        self.peer.rem_successorNum(num)
    
    def add_files(self,file): 
        self.peer.add_files(file)

    def get_file(self,file): 
        self.peer.get_files(file)
   
if __name__ == "__main__":
    import sys 
    
    #set up the peer 
    try:
        main()
    except KeyboardInterrupt:
        Store()['status'] = "Abrupt"
            #check lost pings 
        a = Store()['peer_instance'].get_successor(0).abort
        b = Store()['peer_instance'].get_successor(1).abort

        while (a!=True & b!=True):
            a = Store()['peer_instance'].get_successor(0).abort
            b = Store()['peer_instance'].get_successor(1).abort
            time.sleep(1)
        Store()['peer_instance'].departureChange(3)

        sys.exit(0)
    
