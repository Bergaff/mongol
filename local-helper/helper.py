"""Local PDF importer. Binds only to loopback; does not expose stored text via HTTP."""
import argparse
import hashlib
import io
import json
import secrets
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from uuid import uuid4
from pypdf import PdfReader

MAX_SIZE = 50 * 1024 * 1024
DATA_DIR = Path.home() / 'mongol-library'


def run():
    parser = argparse.ArgumentParser(description='Локальный импорт PDF для Монгол хэл')
    parser.add_argument('--origin', required=True, help='Точный адрес сайта, например https://mongol-b2s.pages.dev')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    origin = urlparse(args.origin)
    if origin.scheme != 'https' or not origin.netloc or origin.path not in ('', '/') or origin.query or origin.fragment or origin.username or origin.password:
        parser.error('Укажите точный HTTPS origin сайта без пути')
    allowed_origin = f'{origin.scheme}://{origin.netloc}'
    token = secrets.token_urlsafe(32)
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
        def origin_ok(self):
            return self.headers.get('Origin') == allowed_origin and self.headers.get('Host') == f'127.0.0.1:{args.port}'
        def headers_for(self, status, content_type='application/json'):
            self.send_response(status)
            self.send_header('Access-Control-Allow-Origin', allowed_origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Type', content_type)
            self.end_headers()
        def respond(self, status, obj):
            self.headers_for(status)
            self.wfile.write(json.dumps(obj, ensure_ascii=False).encode('utf-8'))
        def authorized(self):
            return self.origin_ok() and secrets.compare_digest(self.headers.get('X-Mongol-Token', ''), token)
        def do_OPTIONS(self):
            if not self.origin_ok():
                self.send_error(403)
                return
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin', allowed_origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Mongol-Token')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.end_headers()
        def do_GET(self):
            if not self.authorized():
                return self.respond(403, {'error': 'Нет доступа'})
            if self.path != '/health':
                return self.respond(404, {'error': 'Не найдено'})
            self.respond(200, {'ok': True})
        def do_POST(self):
            if not self.authorized():
                return self.respond(403, {'error': 'Нет доступа'})
            parsed = urlparse(self.path)
            if parsed.path != '/import':
                return self.respond(404, {'error': 'Не найдено'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 1 or size > MAX_SIZE:
                    return self.respond(413, {'error': 'PDF должен быть не больше 50 МБ'})
                data = self.rfile.read(size)
                if not data.startswith(b'%PDF-'):
                    return self.respond(400, {'error': 'Ожидается PDF'})
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    return self.respond(400, {'error': 'Зашифрованный PDF не поддерживается'})
                pages = [page.extract_text() or '' for page in reader.pages]
                name = Path(parse_qs(parsed.query).get('name', ['Источник.pdf'])[0]).name[:200]
                doc = {'id': uuid4().hex, 'name': name, 'sha256': hashlib.sha256(data).hexdigest(), 'created_at': datetime.now(timezone.utc).isoformat(), 'pages': pages}
                target = DATA_DIR / (doc['id'] + '.json')
                with target.open('x', encoding='utf-8') as out:
                    json.dump(doc, out, ensure_ascii=False)
                target.chmod(0o600)
                self.respond(200, {'name': name, 'pages': len(pages), 'characters': sum(map(len, pages)), 'empty_pages': sum(not p.strip() for p in pages)})
            except Exception:
                self.respond(400, {'error': 'Не удалось прочитать PDF. Проверьте файл.'})
    print(f'Адрес сайта: {allowed_origin}\nТокен подключения (не публикуйте): {token}\nБиблиотека: {DATA_DIR}\nДля остановки нажмите Ctrl+C', flush=True)
    try:
        ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\nПомощник остановлен.')

if __name__ == '__main__':
    run()
