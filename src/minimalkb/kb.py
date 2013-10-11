import logging; logger = logging.getLogger("MinimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import shlex
import ast
import traceback

def api(fn):
    fn._api = True
    return fn

class SQLStore:

    def __init__(self):
        self.conn = sqlite3.connect('kb.db')
        self.create_kb()

    def create_kb(self):
    
        with self.conn:
            self.conn.execute('''CREATE  TABLE  IF NOT EXISTS "triples" 
                    ("hash" INTEGER PRIMARY KEY NOT NULL  UNIQUE , 
                    "subject" TEXT NOT NULL , 
                    "predicate" TEXT NOT NULL , 
                    "object" TEXT NOT NULL , 
                    "model" TEXT NOT NULL )''')

    def add(self, stmts, model = "myself"):

        stmts = [[hash(s + model)] + shlex.split(s) + [model] for s in stmts]

        with self.conn:
            self.conn.executemany('''INSERT OR IGNORE INTO triples 
                     VALUES (?, ?, ?, ?, ?)''', stmts)

    def delete(self, stmts, model = "myself"):
        
        hashes = [hash(s + model) for s in stmts]

        with self.conn:
            self.conn.executemany('''DELETE FROM triples 
                        WHERE (hash=?)''', hashes)

    def query(self, vars, patterns, models):

        def nb_variables(s):
            return (s.count("?") + s.count("*"))

        if len(vars) > 1:
            raise NotImplementedError("Only a single variable in queries is currently supported.")

        if len(patterns) == 1:
            return list(self.simplequery(patterns[0]))

        independentpatterns = {p for p in patterns if nb_variables(p) == 1}
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
            logger.info("Pattern " + p +" -> candidates are: " + str(list(candidates)))

        if not candidates:
            return []

        #now, filter out!
        return list(candidates)

    def simplequery(self, pattern):

        def is_variable(s):
            return s[0] in ["*","?"]

        s,p,o = shlex.split(pattern)

        query = "SELECT "
        if is_variable(s):
            query += "subject FROM triples WHERE (predicate=? AND object=?)"
            return {row[0] for row in self.conn.execute(query, (p,o))}
        if is_variable(p):
            query += "predicate FROM triples WHERE (subject=? AND object=?)"
            return {row[0] for row in self.conn.execute(query, (s,o))}
        if is_variable(o):
            query += "object FROM triples WHERE (subject=? AND predicate=?)"
            return {row[0] for raw in self.conn.execute(query, (s,p))}


class MinimalKB:

    MEMORYPROFILE_DEFAULT = ""
    MEMORYPROFILE_SHORTTERM = "SHORTTERM"

    def __init__(self):
        _api = [getattr(self, fn) for fn in dir(self) if hasattr(getattr(self, fn), "_api")]
        self.api = {fn.__name__:fn for fn in _api}

        self.store = SQLStore()

        self.models = {"myself"}

        logger.info("Initializing the MinimalKB with the following API: " + \
                ", ".join(self.api.keys()))

    @api
    def load(self, filename):
        logger.info("Loading triples from %s" % filename)
        with open(filename, 'r') as triples:
            self.store.add([s.strip() for s in triples.readlines()])

    @api
    def listSimpleMethods(self):
        return self.api.keys()

    @api
    def lookup(self, concept):
        return (concept, "instance")

    @api
    def revise(self, stmts, policy):
        stmts = ast.literal_eval(stmts)
        policy = ast.literal_eval(policy)

        models = set(policy.get('models', []))
        if models:
            #add to the set of all models
            self.models = self.models | models
        else:
            models = self.models

        if policy["method"] in ["add", "safe_add"]:
            logger.info("Adding to " + str(list(models)) + ":\n\t- " + "\n\t- ".join(stmts))
            for model in models:
                self.store.add(stmts, model)

        if policy["method"] == "retract":
            logger.info("Deleting from " + str(list(models)) +":\n\t- " + "\n\t- ".join(stmts))
            for model in models:
                self.store.delete(stmts, model)


    @api
    def findForAgent(self, agent, var, stmts):
        return self.find([var], stmts, None, [agent])

    @api
    def find(self, vars, pattern, constraints = None, models = None):

        pattern = ast.literal_eval(pattern)
        if not models:
            models = self.models

        logger.info("Searching " + str(vars) + \
                    " in models " + str(models) + \
                    " matching:\n\t- " + "\n\t- ".join(pattern))

        res = self.store.query(vars, pattern, models)
        
        logger.info("Found: " + str(res))
        return res

    def execute(self, name, *args):
        f = getattr(self, name)
        try:
            return f(*args)
        except TypeError:
            traceback.print_exc()
            return f()

