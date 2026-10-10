import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raiz do projeto

from security import ensure_face_models

print("Baixando modelos de reconhecimento facial do OpenCV Zoo...")
paths = ensure_face_models(True)
for p in paths:
    print(f"OK: {p}")
print("Modelos prontos.")
