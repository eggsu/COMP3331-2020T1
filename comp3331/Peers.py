from operator import itemgetter

#this class holds the peers, successors and files of an instance of a peer 
class peerMap(object):
    def __init__(self,peer_id):
        self.peer = peer_id
        self.successor=[]
        self.predecessor=[]
        self.peers=[]
        self.successorNum=[]
        self.files=[]

    def add_files(self, file): 
        self.files.append(file)

    def get_files(self,file): 
        if (file in self.files): 
            return file
        else:
            return "None"
        
    def add_successor(self, peer_id):
        self.successor.append(peer_id)
        self.successor.sort(key=itemgetter(1))

    #sort successor list in ascending order
    def rem_successorPos(self, pos):
        self.successor.pop(pos-1)
        #order by position  
        self.successor.sort(key=itemgetter(1))

    def rem_successorNum(self, num):
       
        for l in self.successor:
            if (l[2] == num):
                self.successor.remove(l)

    
    def add_predecessor(self,peer_id):
        if (peer_id not in self.predecessor):
            self.predecessor.append(peer_id)
            #sort in order 
        
        if (len(self.predecessor) == 2):
            #seinc can only be 1 predecessor, get rid
            #of the most min precessor 
            self.predecessor.pop(0)
            
    #only return the object
    def get_successor(self,pos):
        return self.successor[pos][0]
    
    def get_predecessor(self):
        if (len(self.predecessor) == 0):
            return
        else:
            return self.predecessor[0]
    
    def get_all_successors(self):
        return self.successor