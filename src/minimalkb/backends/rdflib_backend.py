import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import shlex
from rdflib import Graph, URIRef
from rdflib.namespace import Namespace, NamespaceManager, RDF, RDFS, OWL, XSD


class RDFlibStore:

    def __init__(self):

        self.models = {}

    def clear(self):
        """ Empties all knowledge models.
        """
        self.models = {}

    def add(self, stmts, model = "default"):
        """ Add the given statements to the given model.
        """

        # creates a model if necessary
        graph = self.models.setdefault(model, Graph())

        for stmt in stmts:
            graph.add(self._parse_stmt(stmt))

    def delete(self, stmts, model = "default"):
        """ remove the given statements from the given model.
        """
        if not model in self.models:
            logger.warn("Trying to remove statements from an unexisting model!")
            return

        for stmt in stmts:
            self.models[model].remove(self._parse_stmt(stmt))

    def update(self, stmts, model = "default"):
        """ Add the given statements to the given model, updating the statements
        with a functional predicate.
        """
        raise NotImplementedError()

    def about(self, resource, models):
        """ Returns all statements involving the resource.
        """
        raise NotImplementedError()

    def has(self, stmts, models):
        """ Returns true if the statements or partial statements
        are present in the knowledge models.
        """
        raise NotImplementedError()


    def query(self, vars, patterns, models):
        raise NotImplementedError()

    def classesof(self, concept, direct, models):
        """ Returns the RDF classes of the concept.
        """
        raise NotImplementedError()

    #############################################################################

    def _parse_stmt(self, stmt):
        s,p,o = shlex.split(stmt)
        return (self._parse_resource(s), 
                self._parse_resource(p), 
                self._parse_resource(o))

    def _parse_resource(self, resource):
        tokens = resource.split(':')
        if len(tokens) == 1:
            return URIRef(resource)
        
        ns, resource = tokens

        if ns == "rdf":
            return RDF[resource]
        elif ns == "rdfs":
            return RDFS[resource]
        elif ns == "owl":
            return OWL[resource]

        return URIRef(resource)
        #elif ns == "xsd":
        #    return XSD[resource]
    
    def __str__(self):
        res = ""
        for name, graph in self.models.items():
            res += name + "\n"
            for s,p,o in graph:
                res += "[" + ", ".join([s,p,o]) + "]\n"
        return res
        
