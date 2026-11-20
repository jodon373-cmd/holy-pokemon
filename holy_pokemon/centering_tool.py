"""Automatic local v3 centering inspector. Upload a photo to measure.

Run: python -m holy_pokemon.centering_tool. Photos stay in memory on localhost.
"""
from __future__ import annotations
import argparse
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import webbrowser

import cv2
import numpy as np
from .centering_v3 import measure_bgr, compute_ratios, centering_eligibility, _order_quad

MAX_BODY = 32 * 1024 * 1024


def inspect(payload):
    raw = base64.b64decode(payload['image'].split(',', 1)[-1], validate=True)
    image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if image is None or max(image.shape[:2]) > 16000:
        raise ValueError('Unreadable or oversized photo')
    side = payload.get('side', 'auto')
    if side == 'auto':
        from .centering_geometry import detect_outer
        side = 'back' if detect_outer(image, 'back').get('outer_quad') else 'front'

    if payload.get('quad') is None:
        result = measure_bgr(image, side=side)
        return dict(result=result, side=side, original_sha256=__import__("hashlib").sha256(raw).hexdigest(), width=image.shape[1], height=image.shape[0])
    quad = _order_quad(payload['quad'])
    h, w = image.shape[:2]
    if np.any(quad < 0) or np.any(quad[:, 0] >= w) or np.any(quad[:, 1] >= h):
        raise ValueError('Card corners must stay inside the original photo')
    dest = np.float32([[0, 0], [699, 0], [699, 979], [0, 979]])
    matrix = cv2.getPerspectiveTransform(quad, dest)
    rect = cv2.warpPerspective(image, matrix, (700, 980))
    ok, encoded = cv2.imencode('.png', rect)
    if not ok:
        raise ValueError('Could not rectify photo')
    return dict(image='data:image/png;base64,' + base64.b64encode(encoded).decode(),
                width=700, height=980, quad=quad.tolist())


def manual_ratios(widths):
    values = [float(widths[k]) for k in ('left', 'right', 'top', 'bottom')]
    if not all(np.isfinite(values)) or min(values) <= 0:
        raise ValueError('All four borders must be finite and positive')
    if values[0]+values[1] >= 699 or values[2]+values[3] >= 979:
        raise ValueError('Inner borders must lie inside the card')
    return compute_ratios(*values)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send(self, value, status=200, kind='application/json'):
        raw = value.encode() if isinstance(value, str) else json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path != '/':
            return self.send({'error': 'Not found'}, 404)
        self.send(Path(__file__).with_name('centering_tool.html').read_text(), kind='text/html; charset=utf-8')

    def do_POST(self):
        # Browser requests must originate on this same local page.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.send({'error': 'Cross-origin request rejected'}, 403)
        length = int(self.headers.get('Content-Length', 0))
        if not 0 < length <= MAX_BODY:
            return self.send({'error': 'Photo request exceeds 32 MB'}, 413)
        try:
            payload = json.loads(self.rfile.read(length))
            if self.path == '/inspect':
                return self.send(inspect(payload))
            if self.path == '/ratios':
                ratios = {side: manual_ratios(payload[side]) if payload.get(side) else None for side in ('front', 'back')}
                return self.send(dict(ratios=ratios, eligibility=centering_eligibility(ratios['front'], ratios['back']),
                                      grade_prediction=None, measurement_basis='USER_CONFIRMED_GEOMETRY'))
            return self.send({'error': 'Not found'}, 404)
        except (ValueError, KeyError, TypeError, cv2.error) as exc:
            return self.send({'error': str(exc)}, 400)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--image', action='append', help='Measure a local image automatically; repeat for a batch')
    parser.add_argument('--side', choices=('auto','front','back'), default='auto')
    parser.add_argument('--output', help='Write automatic batch results as JSON')
    args = parser.parse_args(argv)
    if args.image:
        rows = []
        for name in args.image:
            raw = Path(name).read_bytes()
            result = inspect(dict(image=base64.b64encode(raw).decode(), side=args.side))
            rows.append(dict(path=name, **result))
        report = json.dumps(dict(mode='AUTOMATIC_CENTERING_V3', measurements=rows, grade_prediction=None), indent=2)
        if args.output:
            destination = Path(args.output)
            if any(destination.resolve() == Path(name).resolve() or (destination.exists() and destination.samefile(name)) for name in args.image):
                raise ValueError('Report cannot overwrite an original photo')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(report+'\n')
        print(report)
        return

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Centering inspector: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
