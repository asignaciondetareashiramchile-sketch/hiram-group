"""Entry point para Hiram Group AI Platform."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
from backend.config import PORT

if __name__ == "__main__":
    print("=" * 60)
    print("  HIRAM GROUP – AI Enterprise Agent Platform")
    print("  Hiram Chile · ProClean Facilities")
    print("=" * 60)
    print(f"  Iniciando servidor en http://localhost:{PORT}")
    print(f"  Usuario por defecto: admin / HiramGroup2024!")
    print("=" * 60)

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=PORT,
        reload=True,
        log_level="info",
    )
