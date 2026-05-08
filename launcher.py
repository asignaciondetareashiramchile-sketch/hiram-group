"""Launcher: inicia el servidor y abre el navegador automáticamente."""
import subprocess
import webbrowser
import time
import sys
import os
import signal

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8000
URL = f"http://localhost:{PORT}"


def kill_port(port):
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        if result.stdout.strip():
            for pid in result.stdout.strip().split('\n'):
                try:
                    os.kill(int(pid.strip()), signal.SIGTERM)
                except:
                    pass
            time.sleep(1)
    except:
        pass


def main():
    print("=" * 55)
    print("  🏢 HIRAM GROUP – AI Enterprise Agent Platform")
    print("=" * 55)

    kill_port(PORT)

    print(f"  🚀 Iniciando servidor...")
    proc = subprocess.Popen(
        [sys.executable, "run.py"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # Wait until server is ready
    import urllib.request
    for i in range(15):
        time.sleep(1)
        try:
            urllib.request.urlopen(f"{URL}/api/health", timeout=2)
            break
        except:
            pass
    else:
        print("  ⚠️  El servidor tardó más de lo esperado. Abriendo igualmente...")

    print(f"  ✅ Servidor listo en {URL}")
    print(f"  🌐 Abriendo navegador...")
    webbrowser.open(URL)
    print(f"  👤 Usuario: admin  |  Contraseña: HiramGroup2024!")
    print("=" * 55)

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n  🛑 Cerrando plataforma...")
        proc.terminate()


if __name__ == "__main__":
    main()
