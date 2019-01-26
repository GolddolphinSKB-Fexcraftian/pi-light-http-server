from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from PiUtils import *
from LightThreadWorker import LightWorker

class Server(BaseHTTPRequestHandler):
    def __init__(self, lights, animations, instructions, currentArgs, currentProgram, currentRefreshRate, *args):
        # Important: A new handler is created for every request.
        self.lights = lights
        self.animations = animations
        self.animArgs = currentArgs
        self.instructionQueue = instructions
        self.currentProgram = currentProgram
        self.currentRefreshRate = currentRefreshRate
        print(id(self.currentProgram))
        print(id(currentProgram))
        # *laughs in pass by reference*
        super().__init__(*args)
        
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        print(self.currentProgram)
        self._set_headers()
        ne = {"arguments": self.animArgs, "CPU": getCPU(), "RAM": getRAM(), "TEMP": getTemp(), "PROGRAM": self.currentProgram}
        if self.path.endswith("fetchAnimations"):
            ne["animations"] = self.animations

        rn = json.dumps(ne)
        self.wfile.write(rn.encode("UTF-8"))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode("UTF-8")

        self._set_headers()
        try:
            retData = json.loads(post_data[7:])

            status = ""
            if post_data[0:7] == "SETPROG":
                if retData["newProg"] in self.animations:
                    self.currentProgram = retData["newProg"]
                    print(self.currentProgram)
                    self.animArgs = self.animations[retData["newProg"]]["defaultArgs"]
                    print(self.animArgs)
                    self.instructionQueue.put(("UPANIM", self.animations[retData["newProg"]]["func"], self.animArgs))
                    status = "OK"  
            elif post_data[0:7] == "SETARGS":
                self.instructionQueue.put(("CHANGEARGS", retData))
                self.animArgs = retData
                status = "OK"
            elif post_data[0:7] == "SETRFSH":
                self.instructionQueue.put(("CHANGERFSH", int(retData["refresh"])))
            else:
                status = "BAD"
        except:
            status = "Data Invalid"
        self.wfile.write(status.encode("UTF-8"))

def run(instructions, animations, defaultAnim, server_class=HTTPServer, port=8000):
    # Some funny buisiness with defining everything here, but sure.
    lights = LightWorker(instructions, defaultAnim, 60)
    lights.start()
    currentProgram = ""
    currentArgs = {}
    currentRefreshRate = 30
    def makeHandler(*args):
        Server(lights, animations, instructions,currentArgs, currentProgram, currentRefreshRate, *args)
    server_address = ('', port)
    httpd = server_class(server_address, makeHandler)
    print('Starting httpd...')
    try:
        httpd.serve_forever()
    except:
        httpd.server_close()
        print("Closing server")
        instructions.put(("STOP", None))
