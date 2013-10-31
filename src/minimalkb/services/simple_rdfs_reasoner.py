import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import time
import datetime
import sqlite3

from minimalkb.backends.sqlite import sqlhash
from minimalkb.kb import DEFAULT_MODEL

REASONER_RATE = 5 #Hz

class OntoClass:
    def __init__(self, name):
        self.name = name
        self.parents = set()
        self.children = set()
        self.instances = set()

    def __repr__(self):
        return self.name + \
               "\n\tParents: " + str(self.parents) + \
               "\n\tChildren: " + str(self.children) + \
               "\n\tInstances: " + str(self.instances)

class SQLiteSimpleRDFSReasoner:

    def __init__(self, database = "kb.db"):
        self.db = sqlite3.connect(':memory:') # create a memory database
        self.shareddb = sqlite3.connect(database)

        # create the tables
        # taken from http://stackoverflow.com/questions/4019081
        query = None
        for line in self.shareddb.iterdump():
            if "triples" in line:
                    query = line
                    break
        self.db.executescript(query)

        self.running = True
        logger.info("Reasoner (simple RDFS) started. Classification running at %sHz" % REASONER_RATE)

    ####################################################################
    ####################################################################
    def classify(self):

        starttime = time.time()
        self.copydb()

        rdftype, subclassof = self.get_missing_taxonomy_stmts()

        #TODO: currently inferred statements are *only* added to the default model!
        newstmts = [(i, "rdf:type", c, DEFAULT_MODEL) for i,c in rdftype]
        newstmts += [(cc, "rdfs:subClassOf", cp, DEFAULT_MODEL) for cc,cp in subclassof]

        if newstmts:
            self.update_shared_db(newstmts)

            logger.info("Classification took %fsec." % (time.time() - starttime))

    def get_onto(self, db):

        onto = {}

        rdftype = None
        subclassof = None
        with db:
            rdftype = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, object FROM triples 
                       WHERE (predicate='rdf:type')
                    ''')}
            subclassof = {(row[0], row[1]) for row in db.execute(
                    '''SELECT subject, object FROM triples 
                       WHERE (predicate='rdfs:subClassOf')
                    ''')}

        for cc, cp in subclassof:
            parent = onto.setdefault(cp, OntoClass(cp))
            child = onto.setdefault(cc, OntoClass(cc))
            child.parents.add(parent)
            parent.children.add(child)

        for i, c in rdftype:
            onto.setdefault(c, OntoClass(c)).instances.add(i)

        return onto, rdftype, subclassof

    def get_missing_taxonomy_stmts(self):

        onto, rdftype, subclassof = self.get_onto(self.db)

        newrdftype = set()
        newsubclassof = set()

        def addinstance(instance, cls):
            newrdftype.add((instance, cls.name))
            for p in cls.parents:
                addinstance(instance, p)

        def addsubclassof(scls, cls):
            newsubclassof.add((scls.name, cls.name))
            for p in cls.parents:
                addsubclassof(scls, p)

        for name, cls in onto.items():
            for i in cls.instances:
                addinstance(i, cls)
            for p in cls.parents:
                addsubclassof(cls, p)

        newrdftype -= rdftype
        newsubclassof -= subclassof
        return newrdftype, newsubclassof



    ######################################################################
    ######################################################################
    def copydb(self):
        """ Tried several other options (with ATTACH DATABASE -> that would likely lock the shared database as well, with iterdump, we miss the 'OR IGNORE')
        """
        res = self.shareddb.execute("SELECT * FROM triples")
        with self.db:
            self.db.execute("DELETE FROM triples")
            self.db.executemany('''INSERT INTO triples
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                               res)

    def update_shared_db(self, stmts):

        logger.debug("Reasoner added %s new statements: %s" % (len(stmts), stmts))

        timestamp = datetime.datetime.now().isoformat()
        stmts = [[sqlhash(s,p,o,model), s, p, o, model, timestamp] for s,p,o,model in stmts]

        with self.shareddb:
            self.shareddb.executemany('''INSERT OR IGNORE INTO triples
                     (hash, subject, predicate, object, model, timestamp, inferred)
                     VALUES (?, ?, ?, ?, ?, ?, 1)''', stmts)


    def __call__(self, *args):

        try:
            while self.running:
                time.sleep(1./REASONER_RATE)
                self.classify()
        except KeyboardInterrupt:
            return

reasoner = None

def start_reasoner(db):
    global reasoner

    if not reasoner:
        reasoner = SQLiteSimpleRDFSReasoner()
    reasoner.running = True
    reasoner()

def stop_reasoner():

    if reasoner:
        reasoner.running = False

