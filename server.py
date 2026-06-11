import json
import os
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, HTTPServer

PORT = 8000
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

class ProxyHandler(SimpleHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_POST(self):
        if self.path != '/claude':
            self.send_error(404, 'Not Found')
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            return

        prompt = payload.get('prompt', '').strip()
        if not prompt:
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'No prompt provided'}).encode())
            return

        api_key = os.environ.get('GROQ_API_KEY', '').strip()
        if not api_key:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': 'GROQ_API_KEY not set. Run: set GROQ_API_KEY=your_key_here'}).encode())
            return

        request_body = json.dumps({
            'model': 'llama-3.3-70b-versatile',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1000,
            'temperature': 0.3
        }).encode('utf-8')

        req = urllib.request.Request(
            GROQ_URL,
            data=request_body,
            headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                api_response = json.loads(resp.read().decode('utf-8'))
                text = api_response['choices'][0]['message']['content']
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    'content': [{'text': text}]
                }).encode('utf-8'))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            try:
                msg = json.loads(error_body).get('error', {}).get('message', error_body)
            except:
                msg = error_body
            self._set_headers(e.code)
            self.wfile.write(json.dumps({'error': msg}).encode())

        except urllib.error.URLError as e:
            self._set_headers(503)
            self.wfile.write(json.dumps({'error': 'Could not reach Groq API: ' + str(e.reason)}).encode())

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def log_message(self, format, *args):
        print(f'[TrueVoice] {self.address_string()} - {format % args}')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    key = os.environ.get('GROQ_API_KEY', '')
    if not key:
        print('⚠  WARNING: GROQ_API_KEY not set!')
        print('   Run this first:')
        print('   Windows CMD:        set GROQ_API_KEY=your_key_here')
        print('   Windows PowerShell: $env:GROQ_API_KEY="your_key_here"')
    else:
        print(f'✓  Groq API key loaded (ends in ...{key[-4:]})')
    print(f'✓  Serving on http://localhost:{PORT}')
    print('   Press CTRL+C to stop.\n')
    server = HTTPServer(('', PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[TrueVoice] Server stopped.')