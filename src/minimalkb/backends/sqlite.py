import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import datetime
import shlex
import sqlite3

TRIPLETABLENAME = "triples"
TRIPLETABLE = '''CREATE TABLE IF NOT EXISTS %s
                    ("hash" INTEGER PRIMARY KEY NOT NULL  UNIQUE , 
                    "subject" TEXT NOT NULL , 
                    "predicate" TEXT NOT NULL , 
                    "object" TEXT NOT NULL , 
                    "model" TEXT NOT NULL ,
                    "timestamp" DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL ,
                    "expires" DATETIME ,
                    "inferred" BOOLEAN DEFAULT 0 NOT NULL)'''

def sqlhash(s,p,o,model):
    return hash("%s%s%s%s"%(s,p,o, model))

class SQLStore:

    def __init__(self):
        self.conn = sqlite3.connect('kb.db')
        self.create_kb()

    def create_kb(self):
    
        with self.conn:
            self.conn.execute(TRIPLETABLE % TRIPLETABLENAME)

    def clear(self):
        with self.conn:
            self.conn.execute("DROP TABLE %s" % TRIPLETABLENAME)

        self.create_kb()

    def add(self, stmts, model = "default"):

        timestamp = datetime.datetime.now().isoformat()
        stmts = [shlex.split(s) for s in stmts]
        stmts = [[sqlhash(s,p,o, model), s, p, o, model, timestamp] for s,p,o in stmts]


        with self.conn:
            self.conn.executemany('''INSERT OR IGNORE INTO %s
                     (hash, subject, predicate, object, model, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)''' % TRIPLETABLENAME, stmts)

    def delete(self, stmts, model = "default"):
        
        stmts = [shlex.split(s) for s in stmts]
        hashes = [[sqlhash(s,p,o, model)] for s,p,o in stmts]

        with self.conn:
            # removal is non-monotonic. Remove all inferred statements
            self.conn.execute("DELETE FROM %s WHERE inferred=1" % TRIPLETABLENAME)

            self.conn.executemany('''DELETE FROM %s 
                        WHERE (hash=?)''' % TRIPLETABLENAME, hashes)

    def update(self, stmts, model = "default"):

        logger.warn("With SQLite store, update is strictly equivalent to " + \
                    "add (ie, no functional property check")

        self.add(stmts, model)

    def about(self, resource, models):

        params = {'res':resource}
        # workaround to feed a variable number of models
        models = list(models)
        for i in range(len(models)):
            params["m%s"%i] = models[i]

        query = '''
                SELECT subject, predicate, object 
                FROM %s
                WHERE (subject=:res OR predicate=:res OR object=:res)
                AND model IN (%s)''' % (TRIPLETABLENAME, ",".join([":m%s" % i for i in range(len(models))]))
        with self.conn:
            res = self.conn.execute(query, params)
            return [[row[0], row[1], row[2]] for row in res]

    def has(self, stmts, models):

        for s in stmts:
            nbvars = self.nb_variables(s)
            if nbvars == 0:
                if not self.has_stmt(s, models):
                    return False
            elif nbvars == 1:
                if not self.simplequery(s, models):
                    return False
            else:
                raise NotImplementedError("Only a single variable in existence check is currently supported.")

        return True



    def query(self, vars, patterns, models):

        if len(vars) > 1:
            raise NotImplementedError("Only a single variable in queries is currently supported.")

        if len(patterns) == 1:
            return list(self.simplequery(patterns[0]))

        independentpatterns = {p for p in patterns if self.nb_variables(p) == 1}
        directpatterns = {p for p in patterns if vars[0] in p}

        # first, execute simple queries to determine potential candidates:
        # resolve patterns that contain *only* the desired output variable
        candidates = set()
        for p in (independentpatterns & directpatterns):
            if not candidates:
                candidates = self.simplequery(p)
            else:
                # intersection with previous candidates
                candidates = candidates & self.simplequery(p)

        if not candidates:
            return []

        #now, filter out!
        #TODO!
        return list(candidates)

    def classesof(self, concept, direct, models):
        if direct:
            logger.warn("Direct classes are assumed to be the asserted is-a relations")
            return list(self.simplequery("%s rdf:type *" % concept, models, assertedonly = True))
        return list(self.simplequery("%s rdf:type *" % concept, models))
    
    ###################################################################################

    def has_stmt(self, pattern, models):
        """ Returns True if the given statment exist in
        *any* of the provided models.
        """

        s,p,o = shlex.split(pattern)
        query = "SELECT hash FROM %s WHERE hash=?" % TRIPLETABLENAME
        for m in models:
            if self.conn.execute(query, (sqlhash(s, p ,o , m),)).fetchone():
                return True

        return False
 
    def simplequery(self, pattern, models = [], assertedonly = False):

        def is_variable(s):
            return s[0] in ["*","?"]

        s,p,o = shlex.split(pattern)
        params = {'s':s,
                  'p':p,
                  'o':o,
                 }
        # workaround to feed a variable number of models
        models = list(models)
        for i in range(len(models)):
            params["m%s"%i] = models[i]

        query = "SELECT "
        if is_variable(s):
            query += "subject FROM %s WHERE (predicate=:p AND object=:o)" % TRIPLETABLENAME
        elif is_variable(p):
            query += "predicate FROM %s WHERE (subject=:s AND object=:o)" % TRIPLETABLENAME
        elif is_variable(o):
            query += "object FROM %s WHERE (subject=:s AND predicate=:p)" % TRIPLETABLENAME
        else:
            query += "hash FROM %s WHERE (subject=:s AND predicate=:p AND object=:o)" % TRIPLETABLENAME

        if assertedonly:
            query += " AND inferred=0"
        if models:
            query += " AND model IN (%s)" % (",".join([":m%s" % i for i in range(len(models))]))

        return {row[0] for row in self.conn.execute(query, params)}

    def nb_variables(self, s):
        return (s.count("?") + s.count("*"))


