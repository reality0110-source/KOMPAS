"""KOMPAS exe 만들기 — 프로그램 · 자료(data) · 지도 페이지(web)를 exe 한 파일로 묶고, 공식판 지문(SHA-256)을 옆에 적습니다.

  python tools/build_exe.py   → dist/KOMPAS.exe, dist/KOMPAS-<판>-windows.zip(exe + 라이선스 · 고지), dist/KOMPAS.exe.sha256.txt

exe 한 파일 안에 자료가 들어 있어 폴더에는 exe만 보입니다. 자료나 코드를 한 글자라도 바꿔 다시 묶으면 지문이 달라지므로,
공개한 지문과 같은 exe만 공식판입니다. 묶는 중간 파일은 임시 폴더에 두고 프로그램 폴더에는 dist/만 남깁니다.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
WORK = Path(tempfile.gettempdir()) / "kompas_build"
EXCLUDE = ["numpy", "matplotlib", "docx", "requests", "pandas", "scipy", "fitz", "PIL"]     # 쓰지 않는 부품이 딸려 들어가지 않게
NOTICES = ["LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"]      # exe 안과 배포 묶음(zip)에 함께 넣는 라이선스 · 고지


def app_version():
    m = re.search(r'APP_VER\s*=\s*"([^"]+)"', (ROOT / "KOMPAS.pyw").read_text(encoding="utf-8"))
    return m.group(1) if m else "?"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    sep = ";"   # Windows의 --add-data 구분자
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed", "--name", "KOMPAS",
           "--paths", str(ROOT / "ui"), "--paths", str(ROOT / "modules"), "--paths", str(ROOT),
           "--add-data", f"{ROOT / 'data'}{sep}data", "--add-data", f"{ROOT / 'web'}{sep}web",
           "--add-data", f"{ROOT / 'licenses'}{sep}licenses",
           *[a for n in NOTICES for a in ("--add-data", f"{ROOT / n}{sep}.")],
           "--collect-data", "customtkinter",
           "--distpath", str(DIST), "--workpath", str(WORK), "--specpath", str(WORK)]
    for m in EXCLUDE:
        cmd += ["--exclude-module", m]
    cmd.append(str(ROOT / "KOMPAS.pyw"))
    print("묶는 중... (몇 분 걸립니다)", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-3000:])
        sys.exit("exe를 만들지 못했습니다.")
    exe = DIST / "KOMPAS.exe"
    ver = app_version()
    # 배포 묶음: exe + 라이선스 · 고지 (Releases에 올리는 것)
    pack = DIST / f"KOMPAS-{ver}-windows.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, "KOMPAS/KOMPAS.exe")
        for n in NOTICES:
            z.write(ROOT / n, f"KOMPAS/{n}")
        for f in sorted((ROOT / "licenses").iterdir()):
            z.write(f, f"KOMPAS/licenses/{f.name}")
    lines = [f"KOMPAS {ver}"] + [f"SHA-256  {sha256(p)}  {p.name}" for p in (exe, pack)]
    (DIST / "KOMPAS.exe.sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"완료: {exe}  ({exe.stat().st_size / 1e6:.1f} MB), {pack.name}\n" + "\n".join(lines[1:]))


if __name__ == "__main__":
    main()
