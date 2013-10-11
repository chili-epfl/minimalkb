import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import shlex
import sqlite3

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


