import hashlib
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from download_cli import filename_from_url, main


DATA = (b"download-cli-range-test\n" * 150_000)[:3_000_000]


class RangeHandler(http.server.BaseHTTPRequestHandler):
    ranges = []

    def do_GET(self):
        raw_range = self.headers.get("Range")
        if raw_range:
            start_text, _, end_text = raw_range.removeprefix("bytes=").partition("-")
            start = int(start_text)
            end = int(end_text) if end_text else len(DATA) - 1
            self.__class__.ranges.append((start, end))
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(DATA)}")
            body = DATA[start : end + 1]
        else:
            self.send_response(200)
            body = DATA
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, *_args):
        pass


class DownloadCliTests(unittest.TestCase):
    def test_filename_from_url(self):
        self.assertEqual(filename_from_url("https://example.com/files/a%20b.zip?token=123"), "a b.zip")

    def test_parallel_download_and_sha256(self):
        RangeHandler.ranges = []
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        with tempfile.TemporaryDirectory() as directory:
            url = f"http://127.0.0.1:{server.server_port}/sample.bin"
            result = main([url, "-d", directory, "-c", "3", "--sha256", hashlib.sha256(DATA).hexdigest()])
            self.assertEqual(result, 0)
            self.assertEqual((Path(directory) / "sample.bin").read_bytes(), DATA)
            self.assertGreaterEqual(len(RangeHandler.ranges), 2)


if __name__ == "__main__":
    unittest.main()
