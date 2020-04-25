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
    def __init__(self, port):
        self.port = port
        self.socket = socketserver.TCPServer(("", int(self.port)), Server)

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


class Server(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler
    """

    def do_GET(self):
        """
        Respond to GET requests
        """

        self.send_response(200)
        #self.send_header('Content-type', 'text/html')
        #self.end_headers()
        
        # Root path to index.html
        path = self.path
        if path == "/": path = "index.html"

        # Respond with file contents
        self.wfile.write(open(f"html\\{path}", 'rb').read())


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """
        return
