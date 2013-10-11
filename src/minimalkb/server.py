import logging; logger = logging.getLogger("MinimalKB");

DEBUG_LEVEL=logging.DEBUG

import sys
import asyncore, asynchat
import os, socket, string
import traceback

import json

from kb import MinimalKB

PORT = 6969

class MinimalKBChannel(asynchat.async_chat):

    def __init__(self, server, sock, addr, kb):
        asynchat.async_chat.__init__(self, sock)
        self.set_terminator("#end#")
        self.request = None
        self.data = ""
        self.shutdown = 0

        self.kb = kb

    def parse_request(self, req):
        tokens = [a.strip() for a in req.strip().split("\n")]
        if len(tokens) == 1:
            return tokens[0], []
        else:
            return tokens[0], tokens[1:]

    def collect_incoming_data(self, data):
        self.data = self.data + data

    def found_terminator(self):

        res = None
        request, args = self.parse_request(self.data)
        self.data = ""
        logger.debug("Got request " + request + "(" + ", ".join(args) + ")")
        try:
            res = self.kb.execute(request, *args)
        except NotImplementedError as nie:
            msg = str(nie)
            logger.error("Request failed: " + msg)
            self.push("error\n")
            self.push("NotImplementedError\n")
            self.push(msg + "\n")
            self.push("#end#\n")
        except AttributeError:
            traceback.print_exc()
            msg = "Method " + request + " is not implemented."
            logger.error("Request failed: " + msg)
            self.push("error\n")
            self.push("AttributeError\n")
            self.push(msg + "\n")
            self.push("#end#\n")
        except TypeError:
            traceback.print_exc()
            msg = "Method " + request + " is not implemented " + \
                  "with these arguments: " + str(args) + "."
            logger.error("Request failed: " + msg)
            self.push("error\n")
            self.push("TypeError\n")
            self.push(msg + "\n")
            self.push("#end#\n")



        logger.debug("Returned " + str(res))
        self.push("ok\n")
        if res is not None:
            self.push(json.dumps(res))
        self.push("\n#end#\n")

class MinimalKBServer(asyncore.dispatcher):

    def __init__(self, port, kb):
        asyncore.dispatcher.__init__(self)

        self.kb = kb

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(("", port))
        self.listen(5)

    def handle_accept(self):
        conn, addr = self.accept()
        MinimalKBChannel(self, conn, addr, kb)

if __name__ == '__main__':

    console = logging.StreamHandler()
    logger.setLevel(DEBUG_LEVEL)
    formatter = logging.Formatter('%(asctime)-15s %(name)s: %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    kb = MinimalKB()
    s = MinimalKBServer(PORT, kb)
    print "serving at port", PORT, "..."
    asyncore.loop()
