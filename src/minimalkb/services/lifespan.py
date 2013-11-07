import logging; logger = logging.getLogger("minimalKB."+__name__);
DEBUG_LEVEL=logging.DEBUG

import time
import datetime
import sqlite3

CLEANING_RATE = 2 #Hz

class SQLiteLifespanManager:

    def __init__(self, database = "kb.db"):
        self.db = sqlite3.connect(database)

        self.running = True
        logger.info("Knowledge lifespan manager started. Running at %sHz" % CLEANING_RATE)

    ####################################################################
    ####################################################################
    def clean(self):
        starttime = time.time()

        timestamp = datetime.datetime.now().isoformat()

        stmts_to_remove = [(row[0],) for row in self.db.execute(
                '''SELECT hash FROM triples 
                    WHERE (expires<?)
                ''', (timestamp,))]

        if stmts_to_remove:
            with self.db:
                self.db.executemany('''DELETE FROM triples WHERE hash=?''', 
                                    stmts_to_remove)


            logger.info("Cleaning %s stmts (took %fsec)." % (len(stmts_to_remove), time.time() - starttime))

    def __call__(self, *args):

        try:
            while self.running:
                time.sleep(1./CLEANING_RATE)
                self.clean()
        except KeyboardInterrupt:
            return

manager = None

def start_service(db):
    global manager

    if not manager:
        manager = SQLiteLifespanManager()
    manager.running = True
    manager()

def stop_service():

    if manager:
        manager.running = False

