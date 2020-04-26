"""
dash.py
https://github.com/sam210723/xrit-rx

Dashboard HTTP server
"""

from colorama import Fore, Back, Style
import http.server
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

        self.send_response(200)
        if self.path == "/": self.path = "index.html"
        
        # Handle API endpoints and local files
        if self.path.startswith("/api"):
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            content = self.handle_api(self.path)
        else:
            content = open(f"html\\{self.path}", 'rb').read()

        # Respond with file contents or API body
        self.wfile.write(content)
    

    def handle_api(self, path):
        """
        Handle API endpoint request
        """

        return path.encode('utf-8')


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """

        #super().log_message(format, *args)
        return
