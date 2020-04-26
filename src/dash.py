"""
dash.py
https://github.com/sam210723/xrit-rx

Dashboard HTTP server
"""

from colorama import Fore, Back, Style
import http.server
import json
import os
import socketserver
from threading import Thread

class Dashboard:
    def __init__(self, config):
        self.config = config
        self.socket = socketserver.TCPServer(("", int(self.config.port)), Handler)

        # Start HTTP server thread
        self.httpd_thread = Thread()
        self.httpd_thread.name = "HTTP SERVER"
        self.httpd_thread.run = self.http_server
        self.httpd_thread.start()


    def http_server(self):
        """
        HTTP server and request handler thread
        """

        #print(Fore.GREEN + Style.BRIGHT + f"DASHBOARD SERVER RUNNING (127.0.0.1:{self.port})")
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
            path = "html/{}".format(self.path)

            if os.path.isfile(path):            # Requested file exists (HTTP 200)
                self.send_response(200)
                self.end_headers()

                self.wfile.write(
                    open(path, 'rb').read()
                )
            else:                               # Requested file not found (HTTP 404)
                self.send_response(404)
                self.end_headers()
    

    def handle_api(self, path):
        """
        Handle API endpoint request
        """

        path = path.replace("/api", "")

        # Base response object
        content = {
            'version': ''
        }

        # Handle requests based on path
        if path == "":              # Root API endpoint
            content.update({
                'interval': 1,
                'status': 200
            })
        elif path == "/xrit-rx":    # xrit-rx info endpoint
            content.update({
                'satellite': 'GK-2A',
                'status': 200
            })
        else:                       # Catch invalid endpoints
            content.update({
                'status': 404
            })

        # Convert response object to UTF-8 encoded JSON string
        return json.dumps(content, sort_keys=True).encode('utf-8'), content['status']


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """

        #super().log_message(format, *args)
        return
