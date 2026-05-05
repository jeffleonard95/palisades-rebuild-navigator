import http.server
import socketserver
PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("Open your browser to: http://localhost:8000")
    httpd.serve_forever()
