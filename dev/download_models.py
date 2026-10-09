from security import ensure_face_models

print("Baixando modelos de reconhecimento facial do OpenCV Zoo...")
paths = ensure_face_models(True)
for p in paths:
    print(f"OK: {p}")
print("Modelos prontos.")
