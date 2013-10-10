import logging; logger = logging.getLogger("MinimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import shlex
import ast

def api(fn):
    fn._api = True
    return fn

class SQLStore:

    def __init__(self):
        self.conn = sqlite3.connect('kb.db')
        self.create_kb()

    def create_kb(self):
        c = self.conn.cursor()
    
        c.execute('''CREATE  TABLE  IF NOT EXISTS "triples" 
                  ("hash" INTEGER PRIMARY KEY NOT NULL  UNIQUE , 
                   "subject" TEXT NOT NULL , 
                   "predicate" TEXT NOT NULL , 
                   "object" TEXT NOT NULL , 
                   "model" TEXT NOT NULL )''')
        self.conn.commit()

    def add(self, stmts, model = "myself"):
        c = self.conn.cursor()
        
        stmts = [[hash(s + model)] + shlex.split(s) + [model] for s in stmts]

        c.executemany('''INSERT OR IGNORE INTO triples 
                     VALUES (?, ?, ?, ?, ?)''', stmts)
        self.conn.commit()

    def delete(self, stmts, model = "myself"):
        c = self.conn.cursor()
        
        hashes = [hash(s + model) for s in stmts]

        c.executemany('''DELETE FROM triples 
                     WHERE (hash=?)''', hashes)
        self.conn.commit()


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
    def find(self, vars, pattern, constraints = None, model = None):

        if not model:
            model = self.models
        stmts = ast.literal_eval(pattern)
        logger.info("Searching " + var + \
                    " in model <" + agent + \
                    "> matching:\n\t- " + "\n\t- ".join(stmts))

        return []

    def execute(self, name, *args):
        f = getattr(self, name)
        try:
            return f(*args)
        except TypeError:
            return f()

