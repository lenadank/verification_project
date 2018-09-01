#####################
# Class Definitions #
#####################
from pattern.collection.basics import Cabinet, ListWithAdd

#Class HashList holds a set of states, allowing efficient "add" and "find" operations,
#while maintaining the order of addition to the set.
#It consists of a list, holding the states in the order of their addition to the set,
#and a dictionary, holding the same states hashed by given keys.  
class HashList:
    def __init__(self):
        self.l = [] #list
        self.d = {} #dictionary (hash)
    def Add(self,obj,key):
        (self.l).append(obj)
        (self.d)[key] = obj
    def Find(self,key):
        if key in self.d:
            return (self.d)[key]
        else:
            return None
    def GetItem(self,index): #get the item at place "index" in the list
        return (self.l)[index]

#Class Column represents a column in the dynamic programming table. Its main constituent is a HashList of states.
#To allow efficient implementation of the Predictor and Completer procedures, it also contains a dictionary storing
#all grammatical variables whose expansions have already been added to the column by the Predictor procedure. The 
#dictionary maps each such variable to the set of states awaiting it in the column.     
class Column:
    def __init__(self,cnum):
        self.col_num=cnum #column's serial number in the table
        self.snum = 0 #number of states in column
        self.states = HashList() #HashList of states
        self.predicted = {} #dictionary of predicted categories
    def AddState(self,st): #add state to the column
        (self.states).Add(st,st.Key())
        st.index = (self.col_num,self.snum)
        self.snum += 1
    def FindState(self,st): #find a state in the column with the same key as input state st
        return (self.states).Find(st.Key())
    def StateNum(self): #return number of states in the column
        return self.snum
    def AddPredicted(self,cat,s): #add to "predicted" category cat and state s awaiting it
        if cat in self.predicted: #existing predicted category
            (self.predicted[cat]).add(s)
        else: #new predicted category
            self.predicted[cat] = set([s])
    def FindExpecting(self,cat): #return the set of states awaiting category cat
        if cat in self.predicted:
            return self.predicted[cat]
        else:
            return set([])
    def GetState(self,index): #get a state by its index in the column
        return (self.states).GetItem(index)

#Class State represents a state in the dynamic programming table.  
#To allow efficient construction of the parse trees, pointers are recorded in the "ptrs" field,
#implemented as a set of pairs of pointers to states. The "ptrs" field of state z' contains pair (s,z) iff applying the
#Completer procedure to state s yielded state z' by advancing state z.     
class State: 
    def __init__(self,r,d,s,p): 
        self.rule=r #grammatical rule
        self.dot=d #the index of the symbol in the rule after which the dot is located
        self.start=s #index of the column where rule analysis started
        self.ptrs=p #set of pairs of pointers to states 
        self.index=None #DEBUG state's index in the table (a pair containing column number and place within column) 
    def Print(self): #DEBUG print
        p =  str(self.index) + " " + self.rule[0] + " -> "  
        for i in range(1,self.dot+1):
            p = p + unicode(self.rule[i]) + " "
        p = p + ". "
        for i in range (self.dot+1,len(self.rule)):
            p = p + unicode(self.rule[i]) + " "
        p = p + "[" + str(self.start) + "]" + " " + str([(s[0].index,s[1].index) for s in self.ptrs])
        print p     
    def IsComplete(self): #check if state is complete (dot at the end)
        return (self.dot == (len(self.rule)-1))
    def Advance(self,ptr): #create a new state in which the dot is advanced by one place, and put ptr in its "ptrs" set 
        return State(self.rule,self.dot + 1,self.start,set([ptr]))
    def NextCat(self): #return the grammatical category right after the dot
        if self.IsComplete():
            return None
        else:
            return (self.rule)[self.dot+1]
    def Head(self): #return the grammatical category in the left-hand side of the grammatical rule
        return (self.rule)[0]   
    def IsEpsilon(self): #check if the state contains an epsilon-rule
        return (len(self.rule) == 1)
    def Key(self): #return the state's key in the column's HashList
        return (self.rule,self.dot,self.start)

#Class Tree represents a labeled ordered tree.
import adt.tree

class Tree(adt.tree.Tree):
    def IsLeaf(self): #check if tree is a leaf
        return len(self.subtrees) == 0
    def IsRootUnary(self): #check if the root has exactly one child
        return len(self.subtrees) == 1
    def AddChildOnRight(self,t): #add Tree t as the rightmost child of the root       
        return Tree(self.root,self.subtrees + [t])
    def Print(self): #print tree with indentation
        self.PrintFormatted(0,False)
    def PrintFormatted(self,offset,print_offset):
        if print_offset:
            print (offset-1)*" ",
        root_txt = unicode(self.root)
        print root_txt,
        offset += len(root_txt)
        if not self.IsLeaf():
            print "->",
            offset += 4
            (self.subtrees[0]).PrintFormatted(offset,False)
            for t in self.subtrees[1:]:
                print "\n",
                t.PrintFormatted(offset,True)
        
#######################       
# Auxiliary functions #
#######################

#Predictor procedure applied to input state s in column col_num of table, using dictionary nlG of non-lexical rules.
#Returns 1 if a new state is added to the table, 0 otherwise.
def Predictor(table,col_num,s,nlG): 
    change=0
    cat = s.NextCat()
    if (cat not in table[col_num].predicted) and (cat in nlG):
        for r in nlG[cat]:
            table[col_num].AddState(State(r,0,col_num,set([])))
            change=1
    table[col_num].AddPredicted(cat,s)
    return change        

#Completer procedure applied to input state s in column col_num of table.
#Returns 1 if a new state is added to the table, 0 otherwise.
def Completer(table,col_num,s): 
    #find states awaiting the category derived in s, and advance them 
    expecting = (table[s.start]).FindExpecting(s.Head())
    advanced = [z.Advance((s,z)) for z in expecting]
    #merge list of advanced states with existing column 
    change=0
    for st in advanced:
        ds = (table[col_num]).FindState(st) #find states with same key as st
        if ds:  
            ds.ptrs = ds.ptrs | st.ptrs
        else:
            (table[col_num]).AddState(st)  
            change=1
    return change

#Build all parse trees with root state s from the completed dynamic programming table tab.
#Returns a list of parse trees.
def BuildTrees(tab,s):
    if len(s.ptrs) == 0: #base case
        if s.IsComplete():         
            if s.IsEpsilon():  #epsilon rule
                terminal = "Eps"
            else:  #lexical rule
                terminal = (s.rule[1], s.start)
                terminal = s.rule[1]
            return [Tree(s.Head(),[Tree(terminal,[])] if terminal is not None else [])] 
        else:  #dot at the beginning
            return [Tree(s.Head(),[])]                    
    else:
        res = []  #list of parse trees
        for ptr in s.ptrs:
            left_subs = BuildTrees(tab,ptr[1])
            rightmost_subs = BuildTrees(tab,ptr[0]) 
            for lt in left_subs:
                for rt in rightmost_subs:
                    res.append(lt.AddChildOnRight(rt))
        return res

#Initialize dynamic programming table according to input dictionary of lexical rules lG and input sentence w.
#If lG is None, then each token is considered to be a separate lexical category.
#Returns the initialized table.
def InitTable(lG,w):
    table = []  #list of Columns
    #initialize Column 0 with initial state
    s = State(("g","S"),0,0,set([]))
    col = Column(0)
    col.AddState(s)
    table.append(col)
    #initialize all other Columns with states corresponding to lexical rules
    wlen = len(w) #length of input sentence
    for i in range(0,wlen):
        col = Column(i+1)
        if lG is None:
            col.AddState(State((w[i],None), 1, i, set()))
        else:
            try:
                rules = lG[w[i]]
            except KeyError:
                #input word w[i] is not a terminal of the input grammar
                return False 
            for r in rules:
                s = State((r[0],w[i]),1,i,set([]))
                col.AddState(s)
        table.append(col)
    return table

#Turn set g of grammatical rules into a dictionary keyed by the i-th string in each rule (i>=0).
#Returns a dictionary mapping each string x to a list of rules where x appears in place i. 
#(All rules in g are assumed to contain at least i+1 strings.)
def BuildDict(g,i):
    if g is None: return None
    return Cabinet().of(ListWithAdd).with_key(lambda o: o[i], role=Cabinet.SINGULAR).updated(g)
    #g_dict = {}
    #for r in g:
    #    if r[i] in g_dict:
    #        g_dict[r[i]].append(r)
    #    else:
    #        g_dict[r[i]] = [r]
    #print g_dict
    #return g_dict

#DEBUG Print a given dynamic programming table.
def PrintTable(tab):
    for c in tab:
        print c.col_num
        for s in c.states.l:
            s.Print()

#Print a given list of parse trees.
def PrintTrees(trees):
    print "\n"
    if trees:
        i=1
        for t in trees:
            print "Tree",
            print i,
            print ":"
            if not isinstance(t, Tree): t = Tree.reconstruct(t)
            t.Print()
            print "\n"
            i += 1
    else:
        print "no parse"
    
######################
# Earley's Algorithm #
######################

#Runs Earley's algorithm and returns a list of all possible parse trees (a list of Tree objects),
#or False if the input sentence cannot be derived from the input grammar. 
#Input: nlG_list - a list of all non-lexical rules in the input context-free grammar G.
#       lG_list - a list of all lexical rules in the input context-free grammar G.
#       sen - an input sentence (string).
#       lexer - a function to separates sen into tokens (defaults to .split())
#       A grammatical rule is represented as a tuple of grammatical symbols (strings) in left-to-right order.
#       Assumptions: The initial variable in the input grammar is S.
#                    The input grammar does not contain a variable g (which we shall use as the initial dummy category).
#                    The input grammar does not contain the terminal "Eps" (which we use to denote Epsilon).
def Earley(nlG_list,lG_list,sen, lexer=lambda s: s.split()):
    nlG = BuildDict(nlG_list,0) #a dictionary mapping each grammatical category to the list of non-lexical rules expanding it 
    lG = BuildDict(lG_list,1) #a dictionary mapping each terminal to the list of its lexical categories
    w = lexer(sen) #split input sentence to a list of separate words
    if not isinstance(w, list): w = list(w)
    table = InitTable(lG,w)
    if table==False: #not all words in the input sentence are terminals in the input grammar
        return False
    wlen = len(w) #length of input sentence
    for i in range(0,wlen+1):  #iterate over all columns
        change=1  #loop on each column until there is no change (to allow treatment of epsilon rules)
        while change:  
            change=0 
            j=0       
            while j < (table[i]).StateNum(): 
                s = (table[i]).GetState(j)
                if s.IsComplete():
                    completer_change = Completer(table,i,s)
                    change = change or completer_change
                else:
                    predictor_change = Predictor(table,i,s,nlG)
                    change = change or predictor_change
                j=j+1
    #DEBUG print table
    #PrintTable(table)
    #construct parses
    final = State(("g","S"),1,0,[]) #final state
    f = (table[wlen]).FindState(final)
    if not f: return EarleyParses([], table)
    #notice: ignores g in all trees
    return EarleyParses(((t.subtrees)[0] for t in BuildTrees(table,f)), table)


class EarleyParses(list):
    def __init__(self, iterable, chart):
        super(EarleyParses, self).__init__(iterable)
        self.chart = chart


#Run Earley function on given input and print result    
def PrintEarley(nlG_list,lG_list,sen):
    PrintTrees(Earley(nlG_list,lG_list,sen))              

#Examples

#chosen grammar
if 0:
    nlG = [("SD","NP","VP"),("SI","Adv","VP"),("S","SD"),("S","SI"),("S","SD","CONJ","SD"),("S","SI","CONJ","SI"),("NP","D","Adj","N"),("NP","NP","PP"),("VP","Adv","V","NP"),("VP","VP","PP"),("VP","VP","CONJ","VP"),("PP","P","NP"),("Adv",),("Adj",)]
    lG = [("D","the"),("D","a"),("N","book"),("N","order"),("N","flight"),("N","cake"),("CONJ","and"),("V","book"),("V","order"),("P","through"),("P","from"),("NP","Houston"),("NP","NY"),("NP","I"),("NP","you"),("Adv","quickly"),("Adv","kindly"),("Adj","early"),("Adj","tasty")]
    print "Example 1"
    PrintEarley(nlG,lG,"I order a book and you book a flight")
    print "Example 2"
    PrintEarley(nlG,lG,"book the flight through Houston")
    print "Example 3"
    PrintEarley(nlG,lG,"quickly book the early flight through Houston")
    print "Example 4"
    PrintEarley(nlG,lG,"quickly book the flight and kindly order a cake")
    print "Example 5"
    PrintEarley(nlG,lG,"order the tasty cake from NY and book the flight through Houston")
    
