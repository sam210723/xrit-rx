"""
dash.py
https://github.com/sam210723/xrit-rx

Dashboard HTTP server
"""

import http.server
import json
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

        self.socket = socketserver.TCPServer(("", int(dash_config.port)), Handler)

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

        self.socket.shutdown()


class Handler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler
    """

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)


    def do_GET(self):
        """
        Respond to GET requests
        """

        # Respond with index.html content on root path requests
        if self.path == "/": self.path = "index.html"
        
        if self.path.startswith("/api"):        # API endpoint requests
            content, status = self.handle_api(self.path)

            self.send_response(status)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(content)
        else:                                   # Local file requests
            self.path = "html/{}".format(self.path)

            if os.path.isfile(self.path):       # Requested file exists (HTTP 200)
                self.send_response(200)
                self.end_headers()

                self.wfile.write(
                    open(self.path, 'rb').read()
                )
            else:                               # Requested file not found (HTTP 404)
                self.send_response(404)
                self.end_headers()
    

    def handle_api(self, path):
        """
        Handle API endpoint request
        """

        # Base response object
        content = {}
        status = 404

        # Requested endpoint path
        path = path.replace("/api", "").split("/")
        path = None if len(path) == 1 else path[1:]

        if path == None:            # Root API endpoint
            content.update({
                'version': float(dash_config.version),
                'spacecraft': dash_config.spacecraft,
                'downlink': dash_config.downlink,
                'vcid_blacklist': dash_config.blacklist,
                'output_path': dash_config.output,
                'images': dash_config.images,
                'xrit': dash_config.xrit,
                'interval': int(dash_config.interval)
            })

        elif path[0] == "current" and len(path) == 2:
            if path[1] == "vcid":
                content.update({
                    'vcid': demuxer_instance.currentVCID
                })

        elif path[0] == "last" and len(path) == 2:
            if path[1] == "image":
                content.update({
                    'image': demuxer_instance.lastImage
                })
            elif path[1] == "xrit":
                content.update({
                    'xrit': demuxer_instance.lastXRIT
                })
        
        # Send HTTP 200 OK if content has been updated
        if content != {}: status = 200

        # Convert response object to UTF-8 encoded JSON string
        return json.dumps(content, sort_keys=False).encode('utf-8'), status


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """

        #super().log_message(format, *args)
        return
