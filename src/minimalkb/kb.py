import logging; logger = logging.getLogger("MinimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import ast

def api(fn):
    fn._api = True
    return fn

class MinimalKB:

    MEMORYPROFILE_DEFAULT = ""
    MEMORYPROFILE_SHORTTERM = "SHORTTERM"

    def __init__(self):
        _api = [getattr(self, fn) for fn in dir(self) if hasattr(getattr(self, fn), "_api")]
        self.api = {fn.__name__:fn for fn in _api}
        logger.info("Initializing the MinimalKB with the following API: " + \
                ", ".join(self.api.keys()))

    @api
    def listSimpleMethods(self):
        return self.api.keys()

    @api
    def lookup(self, concept):
        return (concept, "instance")

    def add(self, stmts, memoryprofile = MEMORYPROFILE_DEFAULT):
        stmts = ast.literal_eval(stmts)
        logger.info("Adding :\n\t- " + "\n\t- ".join(stmts))

    @api
    def revise(self, stmts, policy):
        stmts = ast.literal_eval(stmts)
        policy = ast.literal_eval(policy)
        logger.info("Revising :\n\t- " + "\n\t- ".join(stmts) + \
                    "\n applying this policy: " + str(policy))


    @api
    def findForAgent(self, agent, var, stmts):
        stmts = ast.literal_eval(stmts)
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

