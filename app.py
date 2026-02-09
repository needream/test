from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        web_root = Path(__file__).parent / "web"
        super().__init__(*args, directory=str(web_root), **kwargs)


def main() -> None:
    host = "0.0.0.0"
    port = 7860
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"App running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
