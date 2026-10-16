"""Голосовая модель: скачивание, ошибки и ручная установка. Без интернета: локальный HTTP-сервер."""
import http.server, io, os as _os, shutil, sys, tempfile, threading, zipfile
ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import voicemodel as M

def check(cond, msg=""):
    if not cond:
        raise AssertionError(msg)

def _model_zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{M.MODEL_NAME}/am/final.mdl", b"model")
        z.writestr(f"{M.MODEL_NAME}/graph/HCLG.fst", b"graph")
        z.writestr(f"{M.MODEL_NAME}/conf/model.conf", b"conf")

class _Srv:
    def __init__(self, files):
        files = dict(files)
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path not in files:
                    self.send_error(404)
                    return
                body = files[self.path]
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *a):
                pass
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
    def stop(self):
        self.httpd.shutdown()

def _zip_bytes(tmp):
    p = _os.path.join(tmp, "src.zip")
    _model_zip(p)
    return open(p, "rb").read()

def test_download_installs_the_model_and_reports_progress():
    tmp = tempfile.mkdtemp()
    srv = _Srv({"/m.zip": _zip_bytes(tmp)})
    seen = []
    try:
        ok, path = M.fetch_model(tmp, url=srv.url + "/m.zip", progress=lambda d, t: seen.append(d))
    finally:
        srv.stop()
    check(ok and M.is_installed(path), path)
    check(seen and seen[-1] > 0, "прогресс сообщается")
    check(not _os.path.exists(_os.path.join(tmp, M.MODEL_NAME + ".zip")), "архив удалён после установки")

def test_404_says_the_address_is_missing():
    tmp = tempfile.mkdtemp()
    srv = _Srv({})
    try:
        ok, msg = M.fetch_model(tmp, url=srv.url + "/nope.zip")
    finally:
        srv.stop()
    check(not ok and "404" in msg and "адрес" in msg, msg)

def test_no_connection_is_explained():
    tmp = tempfile.mkdtemp()
    ok, msg = M.fetch_model(tmp, url="http://127.0.0.1:1/x.zip")
    check(not ok and "нет соединения" in msg, msg)

def test_broken_file_is_explained_not_installed():
    tmp = tempfile.mkdtemp()
    srv = _Srv({"/bad.zip": "это не архив".encode("utf-8")})
    try:
        ok, msg = M.fetch_model(tmp, url=srv.url + "/bad.zip")
    finally:
        srv.stop()
    check(not ok and "повреждён" in msg, msg)

def test_low_disk_space_is_explained_before_download():
    tmp = tempfile.mkdtemp()
    orig = M.free_mb
    M.free_mb = lambda folder: 5
    try:
        ok, msg = M.fetch_model(tmp, url="http://127.0.0.1:1/x.zip")
    finally:
        M.free_mb = orig
    check(not ok and "не хватает места" in msg and "МБ" in msg, msg)

def test_manual_install_from_zip_and_from_folder():
    tmp = tempfile.mkdtemp()
    zp = _os.path.join(tmp, "manual.zip")
    _model_zip(zp)
    ok, path = M.install_from_file(zp, tmp)
    check(ok and M.is_installed(path), path)
    shutil.rmtree(path)
    folder = _os.path.join(tmp, "other", "model")
    _os.makedirs(_os.path.join(folder, "am"))
    _os.makedirs(_os.path.join(folder, "graph"))
    open(_os.path.join(folder, "am", "final.mdl"), "wb").write(b"m")
    ok2, path2 = M.install_from_file(folder, tmp)
    check(ok2 and M.is_installed(path2), path2)

def test_manual_install_explains_wrong_choice():
    tmp = tempfile.mkdtemp()
    ok, msg = M.install_from_file(_os.path.join(tmp, "empty"), tmp)
    check(not ok and "выбери" in msg, msg)
    txt = _os.path.join(tmp, "notes.txt")
    open(txt, "w").write("x")
    ok2, msg2 = M.install_from_file(txt, tmp)
    check(not ok2 and "архив" in msg2, msg2)

if __name__ == "__main__":
    for n in [x for x in dict(globals()) if x.startswith("test_")]:
        globals()[n]()
        print("OK", n)
