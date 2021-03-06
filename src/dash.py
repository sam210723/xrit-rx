"""
dash.py
https://github.com/sam210723/xrit-rx

Dashboard HTTP server
"""

from colorama import Fore, Back, Style
import http.server
import json
import mimetypes
import os
import socketserver
from threading import Thread

dash_config = None
demuxer_instance = None

class Dashboard:
    def __init__(self, config, demuxer):
        global dash_config
        global demuxer_instance

        dash_config = config
        demuxer_instance = demuxer

        try:
            self.socket = socketserver.TCPServer(("", int(dash_config.port)), Handler)
        except OSError as e:
            if e.errno == 10048:
                print("\n" + Fore.WHITE + Back.RED + Style.BRIGHT + "DASHBOARD NOT STARTED: PORT ALREADY IN USE")
            else:
                print(e)
            return

        # Start HTTP server thread
        self.httpd_thread = Thread()
        self.httpd_thread.name = "HTTP SERVER"
        self.httpd_thread.run = self.http_server
        self.httpd_thread.start()


    def http_server(self):
        """
        HTTP server and request handler thread
        """

        self.socket.serve_forever()
    

    def stop(self):
        """
        Stops the HTTP server thread
        """

        try:
            self.socket.shutdown()
        except AttributeError:
            return


class Handler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler
    """

    def __init__(self, request, client_address, server):
        try:
            super().__init__(request, client_address, server)
        except ConnectionResetError:
            return


    def do_GET(self):
        """
        Respond to GET requests
        """

        # Respond with index.html content on root path requests
        if self.path == "/": self.path = "index.html"
        
        try:
            if self.path.startswith("/api/") or self.path == "/api":    # API endpoint requests
                content, status, mime = self.handle_api(self.path)

                self.send_response(status)
                self.send_header('Content-type', mime)
                self.end_headers()
                self.wfile.write(content)
            else:                                                       # Local file requests
                self.path = "html/{}".format(self.path)

                if os.path.isfile(self.path):                           # Requested file exists (HTTP 200)
                    self.send_response(200)
                    mime = mimetypes.guess_type(self.path)[0]
                    self.send_header('Content-type', mime)
                    self.end_headers()

                    self.wfile.write(
                        open(self.path, 'rb').read()
                    )
                else:                                                   # Requested file not found (HTTP 404)
                    self.send_response(404)
                    self.end_headers()
        except ConnectionAbortedError:
            return
    

    def handle_api(self, path):
        """
        Handle API endpoint request
        """

        # Base response object
        content = b''
        status = 404
        mime = "application/json"

        # Requested endpoint path
        path = path.replace("/api", "").split("/")
        path = None if len(path) == 1 else path[1:]

        if path == None:                                        # Root API endpoint
            content = {
                'version': dash_config.version,
                'spacecraft': dash_config.spacecraft,
                'downlink': dash_config.downlink,
                'vcid_blacklist': dash_config.blacklist,
                'output_path': dash_config.output,
                'images': dash_config.images,
                'xrit': dash_config.xrit,
                'interval': int(dash_config.interval)
            }
        
        elif "/".join(path).startswith(dash_config.output):     # Endpoint starts with demuxer output root path
            path = "/".join(path)
            if (os.path.isfile(path)):
                mime = mimetypes.guess_type(path)[0]
                content = open(path, 'rb').read()

        elif path[0] == "current" and len(path) == 2:
            if path[1] == "vcid":
                content = {
                    'vcid': demuxer_instance.vcid
                }

        elif path[0] == "latest" and len(path) == 2:
            if path[1] == "image":
                content = {
                    'image': demuxer_instance.latest_img
                }
            elif path[1] == "xrit":
                content = {
                    'xrit': demuxer_instance.latest_xrit
                }
        
        # Send HTTP 200 OK if content has been updated
        if content != b'': status = 200

        # Convert Python dict into JSON string
        if type(content) is dict:
            content = json.dumps(content, sort_keys=False).encode('utf-8')

        # Return response bytes, HTTP status code and content MIME type
        return content, status, mime


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """

        #super().log_message(format, *args)
        return
