import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.argv = ['serve']
from http.server import HTTPServer, SimpleHTTPRequestHandler
HTTPServer(('127.0.0.1', 3131), SimpleHTTPRequestHandler).serve_forever()
