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
from pathlib import Path
import socketserver
from threading import Thread

config = None
demuxer = None

class Dashboard:
    def __init__(self, c, d):
        global config
        global demuxer
        config = c
        demuxer = d

        try:
            self.socket = socketserver.TCPServer(("", int(config.port)), Handler)
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
    Custom HTTP request handler for static files and JSON API
    """

    def __init__(self, req, addr, server):
        """
        Initialise HTTP request handler
        """

        self.close_connection = True
        self.custom_routes = {
            "/": "/index.html"
        }

        try:
            super().__init__(req, addr, server)
        except ConnectionResetError:
            print(f"[HTTP] Connection to {self.client_address[0]} reset")
            return


    def do_GET(self):
        """
        Handle HTTP GET requests
        """

        # Check for custom routes associated with path
        if self.path in self.custom_routes:
            self.path = self.custom_routes[self.path]

        try:
            # Handle API requests
            if self.path.startswith("/api"):
                code, mime, data = self.do_API()

                self.send_response(code)
                self.send_header("Content-type", mime)
                self.end_headers()
                self.wfile.write(data)
            
            # Handle static file requests
            else:
                file_path = Path(f"html{self.path}")

                # Requested file exists
                if file_path.is_file():
                    self.send_response(200)

                    # Send file MIME Type
                    mime = mimetypes.guess_type(file_path)[0]
                    self.send_header("Content-type", mime)
                    self.end_headers()

                    # Send file contents
                    data = open(file_path, "rb")
                    self.wfile.write(data.read())
                    data.close()

                # Requested file not found
                else:
                    self.send_response_only(404)
                    self.end_headers()

        except ConnectionResetError:
            print(f"[HTTP] Connection to {self.client_address[0]} reset")
            return


    def do_API(self):
        """
        Handle API endpoint requests
        """

        # Base response object
        code = 404
        mime = "application/json"
        data = b''

        # API endpoint path
        api_path = self.path.replace("/api", "")
        
        # Root endpoint
        if api_path == "":
            data = {
                'version':        config.version,
                'spacecraft':     config.spacecraft,
                'downlink':       config.downlink,
                'vcid_blacklist': config.blacklist,
                'images':         config.images,
                'xrit':           config.xrit,
                'interval':       int(config.interval)
            }

        # Received data endpoint
        elif api_path.startswith("/received"):
            # Get relative path of requested file
            api_path = api_path.replace("/received", "")
            file_path = Path(config.output + api_path)

            # Read file from disk if it exists
            if file_path.is_file():
                mime = mimetypes.guess_type(file_path)[0]
                file_obj = open(file_path, "rb")
                data = file_obj.read()
                file_obj.close()

        # Simple value endpoints
        elif api_path == "/current/vcid": data = { "vcid":  demuxer.vcid }
        elif api_path == "/latest/image": data = { "image": demuxer.latest_img }
        elif api_path == "/latest/xrit":  data = { "xrit":  demuxer.latest_xrit }

        # Send HTTP 200 OK if content has been updated
        if data != b'': code = 200

        # Convert Python dict into JSON string
        if type(data) is dict: data = json.dumps(data, sort_keys=False).encode('utf-8')

        # Return HTTP status code, content MIME type and response body
        return code, mime, data


    def log_message(self, format, *args):
        """
        Silence HTTP server log messages
        """

        #super().log_message(format, *args)
        return
