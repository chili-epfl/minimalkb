import logging; logger = logging.getLogger("MinimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import sqlite3
import shlex
import ast
import traceback

def api(fn):
    fn._api = True
    return fn

def compat(fn):
    fn._compat = True
    return fn

class KbServerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class SQLStore:

    def __init__(self):
        self.conn = sqlite3.connect('kb.db')
        self.create_kb()

    def hash(self, stmt, model):
        return hash(stmt+model)

    def create_kb(self):
    
        with self.conn:
            self.conn.execute('''CREATE  TABLE  IF NOT EXISTS "triples" 
                    ("hash" INTEGER PRIMARY KEY NOT NULL  UNIQUE , 
                    "subject" TEXT NOT NULL , 
                    "predicate" TEXT NOT NULL , 
                    "object" TEXT NOT NULL , 
                    "model" TEXT NOT NULL )''')

    def clear(self):
        with self.conn:
            self.conn.execute("DROP TABLE triples")

        self.create_kb()

    def add(self, stmts, model = "default"):

        stmts = [[self.hash(s, model)] + shlex.split(s) + [model] for s in stmts]

        with self.conn:
            self.conn.executemany('''INSERT OR IGNORE INTO triples 
                     VALUES (?, ?, ?, ?, ?)''', stmts)

    def delete(self, stmts, model = "default"):
        
        hashes = [[self.hash(s, model)] for s in stmts]

        with self.conn:
            self.conn.executemany('''DELETE FROM triples 
                        WHERE (hash=?)''', hashes)

    def about(self, resource, models):
        with self.conn:
            res = self.conn.execute('''
                SELECT subject, predicate, object 
                FROM triples
                WHERE (subject=:res OR predicate=:res OR object=:res)
                    AND model IN (:models)
                ''', {'res':  resource, 'models': ','.join(models)})
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

        if not candidates:
            return []

        #now, filter out!
        #TODO!
        return list(candidates)


    def has_stmt(self, pattern, models):
        """ Returns True if the given statment exist in
        *any* of the provided models.
        """

        query = "SELECT hash FROM triples WHERE hash=?"
        for m in models:
            if self.conn.execute(query, (self.hash(pattern, m),)).fetchone():
                return True

        return False
 

    def simplequery(self, pattern, models = []):

        def is_variable(s):
            return s[0] in ["*","?"]

        s,p,o = shlex.split(pattern)
        params = {'s':s,
                  'p':p,
                  'o':o,
                  'models': ','.join(models)
                 }

        query = "SELECT "
        if is_variable(s):
            query += "subject FROM triples WHERE (predicate=:p AND object=:o)"
        elif is_variable(p):
            query += "predicate FROM triples WHERE (subject=:s AND object=:o)"
        elif is_variable(o):
            query += "object FROM triples WHERE (subject=:s AND predicate=:p)"
        else:
            query += "hash FROM triples WHERE (subject=:s AND predicate=:p AND object=:o)"

        if models:
            query += " AND model IN (:models)"

        return {row[0] for row in self.conn.execute(query, params)}

    def nb_variables(self, s):
        return (s.count("?") + s.count("*"))


class MinimalKB:

    MEMORYPROFILE_DEFAULT = ""
    MEMORYPROFILE_SHORTTERM = "SHORTTERM"

    def __init__(self):
        _api = [getattr(self, fn) for fn in dir(self) if hasattr(getattr(self, fn), "_api")]
        self._api = {fn.__name__:fn for fn in _api}

        self.store = SQLStore()

        self.models = {"default"}

        apilist = [key + (" (compatibility)" if hasattr(val, "_compat") else "") for key, val in self._api.items()]

        logger.info("Initializing the MinimalKB with the following API: \n\t- " + \
                "\n\t- ".join(apilist))

    @api
    def load(self, filename):
        logger.info("Loading triples from %s" % filename)
        with open(filename, 'r') as triples:
            self.store.add([s.strip() for s in triples.readlines()])

    @api
    def clear(self):
        logger.warn("Clearing the knowledge base!")
        self.store.clear()

    @compat
    @api
    def listSimpleMethods(self):
        return self.methods()

    @api
    def methods(self):
        return self._api.keys()

    @api
    def about(self, resource, models = None):
        return self.store.about(resource, self.normalize_models(models))

    @api
    def lookup(self, resource, models = None):
        logger.info("Lookup for " + str(resource) + \
                    " in " + (str(models) if models else "any model."))

        about =  self.store.about(resource, self.normalize_models(models))
        if not about:
            return []

        return [(resource, "unknown")]

    @api
    def exist(self, stmts, models = None):
        stmts = self.parse_stmts(stmts)
        logger.info("Checking existence of " + str(stmts) + \
                    " in " + (str(models) if models else "any model."))
        return self.store.has(stmts,
                              self.normalize_models(models))

    @api
    def revise(self, stmts, policy):

        stmts = self.parse_stmts(stmts)
        
        if type(policy) != dict:
            policy= ast.literal_eval(policy)

        models = self.normalize_models(policy.get('models', []))

        if policy["method"] in ["add", "safe_add"]:
            logger.info("Adding to " + str(list(models)) + ":\n\t- " + "\n\t- ".join(stmts))
            for model in models:
                self.store.add(stmts, model)

        if policy["method"] == "retract":
            logger.info("Deleting from " + str(list(models)) +":\n\t- " + "\n\t- ".join(stmts))
            for model in models:
                self.store.delete(stmts, model)

    @api
    def add(self, stmts, models = None):
        return self.revise(stmts,
                           {"method": "add",
                            "models": models})

    @api
    def retract(self, stmts, models = None):
        return self.revise(stmts,
                           {"method": "retract",
                            "models": models})

    @compat
    @api
    def findForAgent(self, agent, var, stmts):
        return self.find([var], stmts, None, [agent])

    @api
    def find(self, vars, pattern, constraints = None, models = None):

        vars = ast.literal_eval(vars)
        pattern = self.parse_stmts(pattern)

        if not models:
            models = self.models

        logger.info("Searching " + str(vars) + \
                    " in models " + str(models) + \
                    " matching:\n\t- " + "\n\t- ".join(pattern))

        res = self.store.query(vars, pattern, models)
        
        logger.info("Found: " + str(res))
        return res

    @api
    def findmpe(self, vars, pattern, constraints = None, models = None):
        """ Finds the most probable explanation. Strictly equivalent to
        'find' until we support probabilities.
        """
        return find(self, vars, pattern, constraints = None, models = None)

    def parse_stmts(seld, stmts):
        try:
            return ast.literal_eval(stmts)
        except ValueError as e:
            raise KbServerError("Unable to parse the statements! %s" % e)

    def normalize_models(self, models):
        """ If 'models' is None, [] or contains 'all', then
        returns the set of all models known to the KB.
        Else, add the models to the list of all models, and return
        only the models passed as argument.
        """
        if models:
            if "all" in models:
                return self.models
            else:
                if isinstance(models, (str, unicode)):
                    models = [models]
                #add to the set of all models
                self.models = self.models | set(models)
                return set(models)
        else:
            return self.models

    def execute(self, name, *args):
        f = getattr(self, name)
        if hasattr(f, "_compat"):
                logger.warn("Using non-standard method %s. This may be " + \
                        "removed in the future!" % f.__name__)
        try:
            return f(*args)
        except TypeError:
            traceback.print_exc()
            return f()

