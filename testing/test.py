import logging
import unittest
import time
import kb

from Queue import Empty

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.kb = kb.KB()
        self.kb.clear()

    def tearDown(self):
        self.kb.close()

    def test_basics(self):

        self.kb.hello()

        with self.assertRaises(kb.KbError):
            self.kb.add()
        with self.assertRaises(kb.KbError):
            self.kb.add("toto")


    def test_modifications(self):

        # check no exception is raised
        self.kb.add(["johnny rdf:type Human", "johnny rdfs:label \"A que Johnny\""])
        self.kb += ["alfred rdf:type Human", "alfred likes icecream"]
        self.kb.retract(["alfred rdf:type Human", "alfred likes icecream"])
        self.kb -= ["johnny rdf:type Human"]

    def test_retrieval(self):

        self.assertFalse(self.kb.about("Human"))
        self.assertFalse(self.kb["* rdf:type Human"])

        self.kb += ["johnny rdf:type Human", "johnny rdfs:label \"A que Johnny\""]
        self.kb += ["alfred rdf:type Human", "alfred likes icecream"]

        self.assertItemsEqual(self.kb.about("Human"), 
                            [['johnny', 'rdf:type', 'Human'],
                             ['alfred', 'rdf:type', 'Human']])

        self.assertItemsEqual(self.kb["* rdf:type Human"],
                              ['johnny', 'alfred'])

        self.assertTrue('alfred' in self.kb)
        self.assertFalse('tartempion' in self.kb)

        self.assertTrue('alfred likes icecream' in self.kb)
        self.assertTrue('alfred likes *' in self.kb)
        self.assertTrue('alfred likes ?smthg' in self.kb)
        self.assertFalse('alfred likes mygrandmother' in self.kb)

        self.kb -= ["alfred rdf:type Human", "alfred likes icecream"]

        self.assertItemsEqual(self.kb["* rdf:type Human"],
                              ['johnny'])

        self.assertFalse('alfred likes icecream' in self.kb)
        self.assertFalse('alfred' in self.kb)

    def test_events(self):

        eventtriggered = [False]

        def onevent(evt):
            #py3 only! -> workaround is turning eventtriggered into a list
            #nonlocal eventtriggered
            print("In callback. Got evt %s" % evt)
            eventtriggered[0] = True

        self.kb.subscribe(["?o isIn room"], onevent)

        # should not trigger an event
        self.kb += ["alfred isIn garage"]
        time.sleep(0.1)
        self.assertFalse(eventtriggered[0])


        # should trigger an event
        self.kb += ["alfred isIn room"]
        time.sleep(0.1)
        self.assertTrue(eventtriggered[0])

        eventtriggered[0] = False

        # should not trigger an event
        self.kb += ["alfred leaves room"]
        time.sleep(0.1)
        self.assertFalse(eventtriggered[0])

        # alfred is already in garage, should not fire an event
        self.kb.subscribe(["?o isIn garage"], onevent)
        time.sleep(0.1)
        self.assertFalse(eventtriggered[0])

        # alfred is already in garage, should not fire an event
        self.kb += ["alfred isIn garage"]
        time.sleep(0.1)
        self.assertFalse(eventtriggered[0])

        self.kb += ["batman isIn garage"]
        time.sleep(0.1)
        self.assertTrue(eventtriggered[0])

    def test_polled_events(self):

        evtid = self.kb.subscribe(["?o isIn room"])

        # should not trigger an event
        self.kb += ["alfred isIn garage"]
        time.sleep(0.1)

        with self.assertRaises(Empty):
            self.kb.events.get_nowait()

        # should trigger an event
        self.kb += ["alfred isIn room"]
        time.sleep(0.1)

        id, value = self.kb.events.get_nowait()
        self.assertEqual(id, evtid)
        self.assertItemsEqual(value, [u"alfred"])

        # should not trigger an event
        self.kb += ["alfred leaves room"]
        time.sleep(0.1)

        with self.assertRaises(Empty):
            self.kb.events.get_nowait()


        # alfred is already in garage, should not fire an event
        evtid = self.kb.subscribe(["?o isIn garage"])
        time.sleep(0.1)

        with self.assertRaises(Empty):
            self.kb.events.get_nowait()

        # alfred is already in garage, should not fire an event
        self.kb += ["alfred isIn garage"]
        time.sleep(0.1)

        with self.assertRaises(Empty):
            self.kb.events.get_nowait()


        self.kb += ["batman isIn garage"]
        time.sleep(0.1)

        id, value = self.kb.events.get_nowait()
        self.assertEqual(id, evtid)
        self.assertItemsEqual(value, [u"batman"])

    def test_taxonomy_walking(self):

        self.assertFalse(self.kb.classesof("john"))
        self.kb += ["john rdf:type Human"]
        self.assertItemsEqual(self.kb.classesof("john"), [u'Human'])
        self.kb += ["john rdf:type Genius"]
        self.assertItemsEqual(self.kb.classesof("john"), [u'Human', u'Genius'])
        self.kb -= ["john rdf:type Human"]
        self.assertItemsEqual(self.kb.classesof("john"), [u'Genius'])

    def test_taxonomy_walking_inheritance(self):

        self.kb += ["john rdf:type Human"]
        self.assertItemsEqual(self.kb.classesof("john"), [u'Human'])
        self.kb += ["Human rdfs:subClassOf Animal"]
        time.sleep(0.2) # leave some time for the reasoner to classify
        self.assertItemsEqual(self.kb.classesof("john"), [u'Human', u'Animal'])
        self.assertItemsEqual(self.kb.classesof("john", True), [u'Human'])
        self.kb -= ["john rdf:type Human"]
        time.sleep(0.2) # leave some time for the reasoner to classify
        self.assertFalse(self.kb.classesof("john"))


if __name__ == '__main__':

    kblogger = logging.getLogger("kb")
    console = logging.StreamHandler()
    kblogger.setLevel(logging.DEBUG)
    kblogger.addHandler(console)
    
    unittest.main()
