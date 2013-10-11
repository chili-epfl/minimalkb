minimalKB
=========

minimalKB is a SQLite-backed minimalistic knowledge based for robotic
application.

It stores triples (like RDF/OWL triples), and provides a mostly conformant
[KB-API](http://homepages.laas.fr/slemaign/wiki/doku.php?id=kb_api_robotics) API accessible via a simple socket protocol.

[pykb](https://github.com/severin-lemaignan/pykb) provides an idiomatic Python binding, making easy to
integrate the knowledge base in your applications.

It has almost no features (like no reasoning whatsoever), except it is fast and
simple.

Written in Python. The only dependency is sqlite3.

