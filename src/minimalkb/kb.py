import logging; logger = logging.getLogger("MinimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import shlex
import ast
import traceback

from sqlite_store import SQLStore

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

