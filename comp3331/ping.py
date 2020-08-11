import socket
from socket import AF_INET, SOCK_DGRAM
from store import Store 
import threading
from threading import Event, Thread
import time
from time import sleep
import datetime as dt
import sys 
from Peers import peerMap
from messages import Message
import re
import os

B_PORT=Store()['base_port']
t_lock=threading.Condition()


#these classes are for the communication of peers using udp and tcp

#UDP server/client reference set up: https://pymotw.com/2/socket/tcp.html
#TCP server/client reference set up:https://wiki.python.org/moin/UdpCommunication



class udpServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.clientSocket = socket.socket(AF_INET, SOCK_DGRAM)
        self.serverSocket = socket.socket(AF_INET, SOCK_DGRAM)
        self.portNum = int(B_PORT)+int(Store()['peerID'])
        self.peerNum=self.portNum-B_PORT
        self.serverSocket.bind(('localhost', self.portNum))
        self.ping_interval=int(Store()['ping_interval'])
        self.prev_peer =-1

    
    def answer_ping(self, message,address):
        message = message.decode()
    
        #send message back to pint client
        with t_lock:
            if (message):
                clientId=re.findall('\d+', message)[0]
               # print(message)
                if (message.find('First Incoming')!=-1):

                    #add predecssor once there is connection
                    Store()['peer_instance'].add_pred(clientId)
                receviedmsg="Ping request message received from Peer "+clientId
                print(receviedmsg)

                self.prev_peer = clientId
                msg = "Ping response received from Peer "+str(self.peerNum)
                sent = self.clientSocket.sendto(msg.encode(),address)
               
            t_lock.notify()

    def run(self):
        #this is once the main thread quits
        if (Store()['status']== "Quit"):
            self.threading.join=True() 

        while True:
            message,clientAddress=self.serverSocket.recvfrom(2048)
            self.answer_ping(message,clientAddress)
        self.serverSocket.close()


#set up of UDP client followed: https://stackoverflow.com/questions/3393612/run-certain-code-every-n-seconds

class udpClient(threading.Thread):
    def __init__(self, successorId, peer_init, successorOrder, joinFlag):
        #threading.Thread.__init__(self)
        self.clientSocket = socket.socket(AF_INET, SOCK_DGRAM)
        self.clientSockTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.successorId=int(successorId)
        self.serverPort = int(B_PORT)+int(successorId)
        self.peerInit = peer_init
        self.successorOrder = successorOrder
        self.server_name="localhost"
        self.timeoutCount=0
        self.interval= int(Store()['ping_interval'])
        self.clientSocket.settimeout(self.interval+1) #time out occurs 1 second afrer interval
        self.joinFlag = joinFlag
        self.abort = False

        if (self.successorOrder == 1):
            self.message = "First Incoming Ping Request from " + self.peerInit
        if (self.successorOrder == 2):
            self.message = "Second Incoming Ping Request from " + self.peerInit
        self.ping_count = 0
  
        
        #timer thread set up so that it pings every x seconds
        self.interval= int(Store()['ping_interval'])
        self.start = time.time()
        self.event = Event()
        self.thread = Thread(target=self.pingCondition)
        self.thread.daemon = True
        self.thread.start()


    @property
    def _time(self):
        return self.interval - ((time.time() - self.start) % self.interval)

    def stop(self):
        self.event.set()
        self.thread.join()

    def pingCondition(self): 
        while not self.event.wait(self._time):
            self.ping()


    def ping(self):
        try:
            #send data 
            sent = self.clientSocket.sendto(self.message.encode(),(self.server_name, self.serverPort))
            #receive response 

            data, server = self.clientSocket.recvfrom(2048)
            print(data.decode()) #'ping response received from Peer x  
  
            if (self.joinFlag==0):
                succ_arr_length = len(Store()['peer_instance'].get_all_successors())

                if (succ_arr_length>2):
                    Store()['peer_instance'].remove_successorPos(3)

                #update the ports 
                if (self.successorOrder == 1):
                    #print("here1")
                    self.serverPort = int(Store()['peer_instance'].get_successor(0).serverPort)
                elif (self.successorOrder == 2):
                    #print("here2")
                    self.serverPort = int(Store()['peer_instance'].get_successor(1).serverPort)
        except (socket.timeout):
            self.timeoutCount=self.timeoutCount+1
            if (self.timeoutCount >=2):
                #reset timeout count
                if  (Store()['status'] == "Abrupt"):
                    self.abort = True
          
                self.timeoutCount = 0

class tcpFileClient(threading.Thread): 
    def __init__(self, receivingPeer,fileName,fileNum,currPeer):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.currentPortNum=int(receivingPeer)
        self.fileName = fileName
        self.fileNum = fileNum
        self.peerNum = self.currentPortNum-B_PORT
        self.s.connect(('localhost',self.currentPortNum))
        self.fromPeer = currPeer
        
    def run(self):
        filetosend = open(self.fileName,"rb")
        print('Sending file '+ str(self.fileNum)+ ' to Peer '+str(self.peerNum))
        data = filetosend.read(1024)
        msg = ("DOWNLOAD FILE from Peer "+self.fromPeer).encode()
        self.s.send(msg)
        while data: #read until finish
            self.s.send(data)
            data = filetosend.read(1024)
        
        filetosend.close()
        print(self.s.recv(1024).decode()) #file has been sent 
        self.s.shutdown(2)
        self.s.close()
            



class tcpClient(threading.Thread):
    def __init__(self,nextPortNum, flagType):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.currentPortNum=int(nextPortNum) + int(B_PORT)
        self.flagType = flagType
        self.fileSending = False

        #graceful quitting of a peer
        if (self.flagType == 2): #the peer is quitting gracefully and updating values 
            self.newfirstSuccess= str(Message()['New first successor'])
            self.newsecondSuccess= str(Message()['New second Successor'])
            self.departingPeer = str(Store()['peerID'])
            self.updateNum = str(Message()['Num update'])
            self.msg = 'DEPARTING Peer ' + self.departingPeer + ' New first: '+self.newfirstSuccess + ' New second: '+self.newsecondSuccess +' Update num: '+self.updateNum
       
       #aborting a peer
        elif (self.flagType == 3):# aborting flag
            self.newfirstSuccess= str(Message()['New first successor'])
            self.newsecondSuccess= str(Message()['New second Successor'])
            self.departingPeer = str(Store()['peerID'])
            self.updateNum = str(Message()['Num update'])
            self.msg = 'ABORTING Peer ' + self.departingPeer + ' New first: '+self.newfirstSuccess + ' New second: '+self.newsecondSuccess +' Update num: '+self.updateNum
       
       #joining a peer
        elif ((self.flagType == 1) or (self.flagType == 0)):
            self.peerId=int(Message()['joiningPeerId'])
            self.peerIdPortNum=self.peerId+int(B_PORT)
            if ((self.peerIdPortNum>self.currentPortNum) & flagType!=2):
                self.msg = 'JOIN Forward ' + str(self.peerId)
            if (self.flagType==1): #the peer is joining 
                if (self.currentPortNum<self.peerIdPortNum):
                    first_succ =  str(Message()['prevNewFirstSucc'])
                    second_succ = str(Message()['prevNewSecondSucc'])
                    self.msg = 'JOIN Prev Successor change received '+ first_succ + ' '+second_succ 

        #data insertion 
        elif (self.flagType == 4): 
            self.peerStore=int(Message()['location storage Peer'])+B_PORT
            self.peerIdPortNum=self.peerStore+int(B_PORT)
            self.filename = str(Message()['filename'])
            if (self.currentPortNum<self.peerStore):
                self.msg = 'Forward to Store file '+ self.filename 
            else: 
                self.msg = 'Store file '+self.filename

        #data retrieval
        elif (self.flagType == 5):
            self.peerStore=int(Message()['location find Peer'])+B_PORT
            self.peerIdPortNum=self.peerStore+int(B_PORT)
            self.filename = str(Message()['filename'])
    
            if (self.peerStore>self.currentPortNum):
                self.msg = 'Forward for File request '+ self.filename +' '+Store()['peerID']
            else:
               # self.fileToSend = open(Message()['filenameWExt'],'rb')
                self.receivingPeer = Store()['peerID']
                self.msg = 'File request accepted '+self.filename+'send to '+self.receivingPeer

        self.peerForwardTo= -1
        self.requestChangePeer=-1
        self.prevPeer = -1
        self.prevPeerDepart = -1
        self.first_succ = -1
        self.joinedFlag = -1
        self.storeFlag = -1
        self.retrieveFlag = -1

    def contactServer(self):
        self.s.connect(('localhost', self.currentPortNum))
        self.s.sendall(self.msg.encode())
        data = self.s.recv(1024).decode()

        if (self.flagType == 2 or self.flagType == 3):
            if (data != "Finished updating"):
                #setting next successor to establish tcp connection
                self.prevPeerDepart = re.findall('\d+', data)[0]
        elif(self.flagType == 4 or self.flagType == 5): #for data insertion
            if (data.find('Forwarding')!=-1):
                #keep forwarding to next successor
                self.peerForwardTo = int(re.findall('\d+', data)[0])
            else: 
                #set flag to quit forward while loop in p2p.py
                if (self.flagType == 4):
                    self.storeFlag = 1
                if (self.flagType == 5):
                    self.retrieveFlag = 1
        else: #for joining
            if (data.find('Forwarding')!=-1):
                #send over next port to forward 
                self.peerForwardTo=int(re.findall('\d+', data)[0])
            elif (data.find('Join request has been accepted')!=-1):
                #return first and second succssor
                self.first_succ = re.findall('\d+', data)[0]
                self.second_succ = re.findall('\d+', data)[1]#
            elif (data.find('Init Successor Change ')!=-1):
                #storing to update peer succesors
                self.prevPeer = re.findall('\d+', data)[0]
                self.first_succ = int(self.currentPortNum - B_PORT)
                self.peerForwardTo = re.findall('\d+', data)[1]
                self.joinFirst_succ = re.findall('\d+', data)[2]
                self.joinedFlag = 1
        self.s.close()

    def run(self):
        self.contactServer()

class tcpServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.portNum=int(Store()['peerID'])+int(B_PORT)
        self.s.bind(('localhost',self.portNum))
        self.s.listen(1)

    def answer_pingJoin(self,conn,addr,data):
        with t_lock:
            #eg: portNum on 19 (with example)
                #updsate successor
            if (data.find('Prev Successor change received ')!=-1):
                first_succ = re.findall('\d+', data)[0]
                second_succ = re.findall('\d+', data)[1]
                print('Successor Change request received')
                print('My new first successor is Peer '+first_succ)
                print('My new second successor is Peer '+second_succ)

                #start pinging
                ping_instance=udpClient(int(second_succ), str(self.portNum-B_PORT),2,1)
                Store()['peer_instance'].add_successor([ping_instance,2, second_succ])
                #update the store 
                msg = "Prev changed"
            elif (data.find('Forward')!=-1):
                peerId=int(re.findall('\d+', data)[0])
                self.nextPort= Store()['peer_instance'].get_successor(0).serverPort
                num=self.nextPort-B_PORT
                if (num<peerId): #contains the substring
                    print('Peer '+ str(peerId)+ ' Join request forwarded to my successor')
                    msg = "Forwarding to Peer " + str(self.nextPort-B_PORT)
                else:
                    #send back msg to prev peer to update 
                    #shif the successors and add new one. Update 
                    prev_peer = Store()['peer_instance'].get_predecessor()
                    second_success_next=int(Store()['peer_instance'].get_successor(1).successorId)

                    first_success_next=int(Store()['peer_instance'].get_successor(0).successorId)
                    print('Peer '+str(peerId) + ' Join request received')
                    print('My new first successor is Peer ' + str(peerId))
                    print('My new second successor is Peer ' + str(first_success_next))
                    ping_instance=udpClient(int(peerId),str(self.portNum-B_PORT),1,1)
                    Store()['peer_instance'].add_successor([ping_instance,1, peerId])

                    #update join peer predecessor  
                    msg = 'Init Successor Change to Peer '+ str(prev_peer)+ ' '+str(second_success_next)+' '+str(first_success_next)
                    #change the successor 
           
            #send message back to client
            conn.sendall(msg.encode()) 
            t_lock.notify()
        conn.close()
    
    def answer_pingDepart(self,conn,addr,data):
        with t_lock: 
        
            departing_peer = re.findall('\d+', data)[0]
            new_first=re.findall('\d+', data)[1]
            new_second=re.findall('\d+', data)[2]
            updateNum = int(re.findall('\d+', data)[3])

            if (data.find('DEPARTING')!=-1):
                print("Peer "+departing_peer + " will depart from the network")
            else: 
                print("Peer "+departing_peer + " is no longer alive")
            print ("My new first successor is Peer "+ new_first)
            print("My new second successor is Peer "+new_second)
            Message()['numRemove'] = departing_peer

           # if (int(updateNum) == 1): #new incoming second successor
                #append and start oinging new succesor
            succ_arr_length = len(Store()['peer_instance'].get_all_successors())
            if (succ_arr_length == 2):
                Store()['peer_instance'].remove_successorPos(1)
                Store()['peer_instance'].remove_successorPos(1)

                ping_instance=udpClient(int(new_first), str(self.portNum-B_PORT),1,0)
                Store()['peer_instance'].add_successor([ping_instance,1,new_second])

            ping_instance=udpClient(int(new_second), str(self.portNum-B_PORT),2,0)
            Store()['peer_instance'].add_successor([ping_instance,2,new_second])                
            
            msg = ''
            if updateNum == 1:
                prevPeer = Store()['peer_instance'].get_predecessor()
                msg = 'Departing Update with prev '+prevPeer
            else:
                msg = 'Finished updating'

             #send message back to client
            conn.sendall(msg.encode()) 
            t_lock.notify()
        conn.close()

    def dataInsert(self, conn,addr,data):
        with t_lock:
            filename = re.findall('\d+', data)[0]
            if (data.find('Forward to Store file')!=-1): 
                successor = Store()['peer_instance'].get_successor(0).successorId
                #check if it is storing the file 
                msg = 'Forwarding '+ str(successor)
                print('Store '+filename +' request forwarded to my successor')
            elif (data.find('Store file')!=-1): 
                Store()['peer_instance'].add_files(filename)
                print('Store '+filename +' request accepted')
                msg = 'Store acknowledged'
                
            conn.sendall(msg.encode())
            t_lock.notify()
        conn.close()


    def dataRetrievePrint(self, conn,addr,data):
        with t_lock:
            filename = re.findall('\d+', data)[0]
            #if the file is not stored. continue looking
            if (data.find('Forward for File request')!=-1): 
                peerOrig = int(re.findall('\d+', data)[1])+B_PORT
                successor = Store()['peer_instance'].get_successor(0).successorId

                if (Store()['peer_instance'].get_file(filename) != filename):
                    print('Request for File '+filename +' has been received, but the file is not here')
                    msg = 'Forwarding '+ str(successor)
                    conn.sendall(msg.encode())
                
            #if the file is stored in the location
            if (data.find('accepted')!=-1): 
                receivingPeer = int(re.findall('\d+', data)[1])+B_PORT
                print('File '+filename+' is stored here')
                #add to instance 
                #add file to peer instance 
                Store()['peer_instance'].add_files(filename)
                #get the file from the program directory 
                fileToSend =''
                for root,dirs,files in os.walk("."): 
                    for fileName in files: 
                        if (fileName.find(filename)!=-1):
                            fileToSend = fileName
            
                msg ="SENDING NOW"
                currPeer = str(self.portNum-B_PORT)
                
                #open file and send over to receving peer as TCP 
                fileSentTcp = tcpFileClient(receivingPeer, fileToSend, filename, currPeer)
                fileSentTcp.start()
                fileSentTcp.join()
                
                conn.sendall(msg.encode())
            t_lock.notify()
        conn.close()


    def downloadFile(self,conn,addr,data,filedownload,fileName,fromPeer):
        with t_lock:
            data = conn.recv(1024)
            print("Peer "+ str(fromPeer) + " had File "+str(fileName))
            print("Receiving File "+str(fileName) + " from Peer "+str(fromPeer))
            
            #get all the text
            while (data):
                filedownload.write(data)
                if (len(data)<1024): #check if reach eof
                    break
                else:
                    data=conn.recv(1024)
            filedownload.close()
            
            msg = "The file has been sent"
            conn.sendall(msg.encode())
            print("File "+str(fileName)+ ' received')
            t_lock.notify()
        conn.close()
        


    def run(self):
        
        while 1:
            conn,addr=self.s.accept()
            data=conn.recv(1024).decode()
            
            count = 1
            if (data.find('DOWNLOAD FILE')!=-1):
                fromPeer = re.findall('\d+', data)[0]
                fileName = Message()['filenameWExt']
                fileNum = Message()['filename']
                #overwrite if existing copy aleady
                fileCopy = "_"+fileName
                filedownload = open(fileCopy,"w").close() #clears file
                filedownload = open(fileCopy,"wb")

                self.downloadFile(conn,addr,data,filedownload,fileNum,fromPeer)
            else:
                if not data:
                    break
                if (data.find('DEPARTING')!=-1 or data.find('ABORTING')!=-1):
                    self.answer_pingDepart(conn,addr,data)
                elif (data.find('Store file')!=-1):
                    self.dataInsert(conn,addr,data)
                elif(data.find('File request')!=-1): 
                    self.dataRetrievePrint(conn,addr,data)
                elif(data.find('JOIN')!=-1):
                    self.answer_pingJoin(conn,addr,data)
    
        self.s.close()


