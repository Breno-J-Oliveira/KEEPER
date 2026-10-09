from __future__ import annotations

import base64
import hashlib
import hmac
import io
import re
import shutil
import time
import urllib.request
from pathlib import Path

import qrcode

BASE = Path(__file__).resolve().parent
MODELS = BASE / "models"
DATA = BASE / "data"
FACES = DATA / "faces"
MODELS.mkdir(exist_ok=True)
FACES.mkdir(parents=True, exist_ok=True)

SECRET = b"KEEPER-DEMO-CHANGE-IN-PRODUCTION-2026"
FACE_COSINE_THRESHOLD = 0.45
FACE_MIN_THRESHOLD = 0.42      # piso: o ADM não consegue afrouxar abaixo disso
FACE_FRONTAL_FRAMES = 6        # quadros consecutivos exigidos
LIVENESS_MIN_TIMEOUT = 35      # segundos mínimos para concluir o desafio

RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
RE_PLACA = re.compile(r"^(?:[A-Z]{3}-?\d{4}|[A-Z]{3}\d[A-Z]\d{2})$")
RE_USER = re.compile(r"^[a-zA-Z0-9_.]{3,30}$")
RE_SENHA = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")

MODEL_URLS = {
    "face_detection_yunet_2023mar.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV não instalado. Rode: pip install opencv-contrib-python") from exc


def _np():
    try:
        import numpy as np
        return np
    except ImportError as exc:
        raise RuntimeError("NumPy não instalado. Rode: pip install numpy") from exc


def gerar_token(uid: int) -> str:
    janela = int(time.time() // 30)
    payload = f"{uid}.{janela}"
    sig = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()[:20]
    return f"{payload}.{sig}"


def validar_token(token: str | None) -> int | None:
    try:
        uid, janela, sig = (token or "").strip().split(".")
        payload = f"{uid}.{janela}"
        expected = hmac.new(SECRET, payload.encode(), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(sig, expected):
            return None
        now = int(time.time() // 30)
        if abs(now - int(janela)) <= 2:
            return int(uid)
    except (ValueError, TypeError):
        return None
    return None


def qr_base64(texto: str) -> str:
    buf = io.BytesIO()
    qrcode.make(texto).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def normalizar_placa(texto: str) -> str:
    t = re.sub(r"[^A-Z0-9]", "", (texto or "").upper())
    if len(t) == 7 and re.fullmatch(r"[A-Z]{3}\d{4}", t):
        return t
    if len(t) == 7 and re.fullmatch(r"[A-Z]{3}\d[A-Z]\d{2}", t):
        return t
    return t


def validar_placa(texto: str) -> bool:
    p = (texto or "").upper().replace(" ", "")
    return bool(RE_PLACA.fullmatch(p))


def ensure_face_models(download: bool = True) -> tuple[Path, Path]:
    detector = MODELS / "face_detection_yunet_2023mar.onnx"
    recognizer = MODELS / "face_recognition_sface_2021dec.onnx"
    missing = [p for p in (detector, recognizer) if not p.exists()]
    if missing and download:
        for p in missing:
            url = MODEL_URLS[p.name]
            try:
                print(f"[KEEPER] Baixando modelo: {p.name}")
                urllib.request.urlretrieve(url, p)
            except Exception as exc:
                if p.exists() and p.stat().st_size < 100_000:
                    p.unlink(missing_ok=True)
                raise RuntimeError(f"Não consegui baixar o modelo {p.name}: {exc}") from exc
    if not detector.exists() or not recognizer.exists():
        raise FileNotFoundError("Modelos de face não encontrados. Rode python download_models.py")
    return detector, recognizer


def _open_camera(index: int = 0):
    cv2 = _cv2()
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir a câmera {index}.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def capturar_frame(output_path: str | Path, camera_index: int = 0, title: str = "KEEPER - Câmera", face_box: bool = False) -> str:
    cv2 = _cv2()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cap = _open_camera(camera_index)
    detector = None
    if face_box:
        try:
            det_model, _ = ensure_face_models(True)
            detector = cv2.FaceDetectorYN.create(str(det_model), "", (320, 320), 0.75, 0.3, 5000)
        except Exception:
            detector = None
    saved = ""
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            raw_frame = frame.copy()
            if detector is not None:
                detector.setInputSize((frame.shape[1], frame.shape[0]))
                _, faces = detector.detect(frame)
                if faces is not None:
                    for f in faces:
                        x, y, w, h = [int(v) for v in f[:4]]
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (52, 160, 52), 2)
            cv2.rectangle(frame, (max(0, frame.shape[1]//2-180), max(0, frame.shape[0]//2-220)), (min(frame.shape[1], frame.shape[1]//2+180), min(frame.shape[0], frame.shape[0]//2+220)), (220, 220, 220), 2)
            cv2.putText(frame, "ENTER/ESPACO = capturar   ESC = cancelar", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)
            cv2.imshow(title, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (13, 32):
                if cv2.imwrite(str(output_path), raw_frame):
                    saved = str(output_path)
                break
            if key == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return saved



def _tesseract_cmd():
    try:
        found = shutil.which("tesseract")
        if found:
            return found
    except Exception:
        pass
    candidates = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path.home() / r"AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
    ]
    for exe in candidates:
        if exe.exists():
            return str(exe)
    return None


def configurar_tesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("pytesseract não instalado. Rode: pip install pytesseract") from exc
    exe = _tesseract_cmd()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe
    return pytesseract


def ocr_disponivel() -> bool:
    """Verifica se o OCR está realmente operacional (lib + binário)."""
    try:
        configurar_tesseract()
    except Exception:
        return False
    return _tesseract_cmd() is not None


def face_models_prontos() -> bool:
    """Verifica se os modelos faciais já estão baixados localmente."""
    try:
        return all((MODELS / name).exists() for name in MODEL_URLS)
    except Exception:
        return False


def escolher_imagem_placa() -> str:
    """Abre o seletor de arquivos do Windows e devolve o caminho escolhido."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError(f"Não foi possível abrir o seletor de arquivos: {exc}") from exc
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(
            title="KEEPER — Escolher foto da placa",
            filetypes=[
                ("Imagens", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        return str(path or "")
    finally:
        root.destroy()


def ocr_placa_foto(image_path: str | Path) -> tuple[str, list[str], str]:
    """Executa OCR em uma foto estática e retorna (melhor_placa, candidatos, texto_bruto)."""
    cv2 = _cv2()
    pytesseract = configurar_tesseract()
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError("Não foi possível abrir a imagem selecionada.")

    # Testamos a foto inteira e uma região central porque imagens de placas
    # podem vir tanto recortadas quanto com o veículo inteiro.
    h, w = img.shape[:2]
    regions = [img]
    if w > 500 and h > 300:
        regions.append(img[int(h * 0.30):int(h * 0.72), int(w * 0.12):int(w * 0.88)])

    candidates: list[str] = []
    raw_texts: list[str] = []
    for region in regions:
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
        variants = [
            gray,
            cv2.GaussianBlur(gray, (3, 3), 0),
        ]
        # Contraste/local threshold costuma ajudar quando a placa tem sombra.
        variants.append(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
        variants.append(cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        variants.append(cv2.morphologyEx(variants[2], cv2.MORPH_CLOSE, kernel))

        for variant in variants:
            try:
                raw = pytesseract.image_to_string(
                    variant,
                    config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                )
            except Exception:
                raw = ""
            raw_texts.append(raw.strip())
            norm = normalizar_placa(raw)
            if validar_placa(norm):
                candidates.append(norm)

    # Maioria simples: o texto que mais se repete nas tentativas tende a ser o melhor.
    if candidates:
        best = max(set(candidates), key=candidates.count)
        return best, sorted(set(candidates)), " | ".join(x for x in raw_texts if x)
    return "", [], " | ".join(x for x in raw_texts if x)


def capture_plate_ocr(camera_index: int = 0, timeout: int = 25) -> str:
    """OCR real de placa. Mostra câmera e tenta ler uma placa válida usando Tesseract.
    Pressione ESC para cancelar. Se o OCR não estiver disponível, retorna vazio.
    """
    cv2 = _cv2()
    try:
        pytesseract = configurar_tesseract()
    except Exception:
        return ""
    cap = _open_camera(camera_index)
    start = time.time()
    last_text = ""
    try:
        while time.time() - start < timeout:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            # Region of interest centered for a plate.
            x1, x2 = int(w * 0.22), int(w * 0.78)
            y1, y2 = int(h * 0.38), int(h * 0.62)
            roi = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
            _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            config = "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            try:
                raw = pytesseract.image_to_string(th, config=config)
            except Exception:
                raw = ""
            compact = normalizar_placa(raw)
            if validar_placa(compact):
                last_text = compact
                cv2.putText(frame, f"PLACA: {compact}", (x1, max(25, y1-12)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (70, 220, 70), 2, cv2.LINE_AA)
                cv2.imshow("KEEPER - OCR de placa", frame)
                cv2.waitKey(500)
                return compact
            cv2.rectangle(frame, (x1, y1), (x2, y2), (220, 220, 220), 2)
            cv2.putText(frame, "Centralize a placa no retangulo", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)
            if last_text:
                cv2.putText(frame, f"Leitura parcial: {last_text}", (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2, cv2.LINE_AA)
            cv2.imshow("KEEPER - OCR de placa", frame)
            if (cv2.waitKey(1) & 0xFF) == 27:
                return ""
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return ""


def capture_qr(camera_index: int = 0, timeout: int = 25) -> str:
    cv2 = _cv2()
    cap = _open_camera(camera_index)
    detector = cv2.QRCodeDetector()
    start = time.time()
    try:
        while time.time() - start < timeout:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            data, points, _ = detector.detectAndDecode(frame)
            if points is not None:
                pts = points.astype(int).reshape(-1, 2)
                for i in range(len(pts)):
                    cv2.line(frame, tuple(pts[i]), tuple(pts[(i+1)%len(pts)]), (60, 210, 70), 3)
            cv2.putText(frame, "Aponte o QR do KEEPER | ESC = cancelar", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2, cv2.LINE_AA)
            cv2.imshow("KEEPER - Leitor QR", frame)
            if data:
                return data.strip()
            if (cv2.waitKey(1) & 0xFF) == 27:
                return ""
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return ""


def _detect_face(img):
    cv2 = _cv2()
    detector_model, _ = ensure_face_models(True)
    detector = cv2.FaceDetectorYN.create(str(detector_model), "", (320, 320), 0.75, 0.3, 5000)
    detector.setInputSize((img.shape[1], img.shape[0]))
    _, faces = detector.detect(img)
    if faces is None or len(faces) == 0:
        return None
    faces = sorted(faces, key=lambda f: float(f[2] * f[3]), reverse=True)
    return faces[0]


def foto_tem_rosto(caminho: str | Path) -> bool:
    cv2 = _cv2()
    img = cv2.imread(str(caminho))
    if img is None:
        return False
    return _detect_face(img) is not None


def face_similarity(reference_path: str | Path, query_path: str | Path) -> tuple[bool, float]:
    cv2 = _cv2()
    ref = cv2.imread(str(reference_path))
    query = cv2.imread(str(query_path))
    if ref is None or query is None:
        raise ValueError("Não foi possível abrir a foto facial.")
    _, rec_model = ensure_face_models(True)
    face1 = _detect_face(ref)
    face2 = _detect_face(query)
    if face1 is None or face2 is None:
        return False, 0.0
    recognizer = cv2.FaceRecognizerSF.create(str(rec_model), "")
    crop1 = recognizer.alignCrop(ref, face1)
    crop2 = recognizer.alignCrop(query, face2)
    f1 = recognizer.feature(crop1)
    f2 = recognizer.feature(crop2)
    score = float(recognizer.match(f1, f2, cv2.FaceRecognizerSF_FR_COSINE))
    return score >= FACE_COSINE_THRESHOLD, score


def _yaw(face) -> float:
    """Giro horizontal da cabeça (0 = de frente) a partir dos pontos do YuNet."""
    re_x, le_x, nose_x = float(face[4]), float(face[6]), float(face[8])
    return (nose_x - (re_x + le_x) / 2.0) / (abs(le_x - re_x) or 1.0)


def _qualidade_face(frame, face) -> tuple[bool, str]:
    cv2 = _cv2()
    x, y, w, h = [int(v) for v in face[:4]]
    if float(face[14]) < 0.85 or w < frame.shape[1] * 0.14:
        return False, "Aproxime o rosto da câmera"
    crop = frame[max(0, y):y + h, max(0, x):x + w]
    if crop.size == 0:
        return False, "Rosto cortado: centralize"
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if cv2.Laplacian(gray, cv2.CV_64F).var() < 35:
        return False, "Imagem borrada: fique parado"
    if gray.mean() < 45 or gray.mean() > 215:
        return False, "Ajuste a iluminação"
    return True, ""


def qualidade_foto(caminho: str | Path) -> tuple[bool, str]:
    """Valida a foto de cadastro: um rosto, grande, nítido e bem iluminado, de frente."""
    cv2 = _cv2()
    img = cv2.imread(str(caminho))
    if img is None:
        return False, "Não foi possível abrir a foto."
    det, _ = ensure_face_models(True)
    d = cv2.FaceDetectorYN.create(str(det), "", (320, 320), 0.8, 0.3, 5000)
    d.setInputSize((img.shape[1], img.shape[0]))
    _, faces = d.detect(img)
    if faces is None or len(faces) == 0:
        return False, "Nenhum rosto detectado."
    if len(faces) > 1:
        return False, "Há mais de um rosto na foto."
    ok, msg = _qualidade_face(img, faces[0])
    if ok and abs(_yaw(faces[0])) > 0.25:
        return False, "Olhe de frente para a câmera."
    return ok, msg or "Foto adequada."


def recognize_camera_against(reference_path, camera_index: int = 0, timeout: int = 25,
                             threshold: float | None = None, others=None) -> tuple[bool, float, str]:
    """Face ID em 3 fases: (1) rosto confere em vários quadros seguidos e com qualidade;
    (2) prova de vida: girar a cabeça para um lado sorteado (foto/tela não gira);
    (3) volta de frente e reconfirma. Depois checa margem contra outros usuários."""
    import random
    cv2 = _cv2()
    det_model, rec_model = ensure_face_models(True)
    ref = cv2.imread(str(reference_path))
    if ref is None:
        raise ValueError("Foto facial cadastrada não encontrada.")
    detector = cv2.FaceDetectorYN.create(str(det_model), "", (320, 320), 0.8, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(rec_model), "")

    def feature_of(img):
        detector.setInputSize((img.shape[1], img.shape[0]))
        _, ff = detector.detect(img)
        if ff is None or len(ff) == 0:
            return None
        f0 = sorted(ff, key=lambda f: float(f[2] * f[3]), reverse=True)[0]
        return recognizer.feature(recognizer.alignCrop(img, f0))

    ref_feat = feature_of(ref)
    if ref_feat is None:
        raise ValueError("A foto cadastrada não contém um rosto detectável.")
    thr = max(FACE_MIN_THRESHOLD, FACE_COSINE_THRESHOLD if threshold is None else float(threshold))
    others_feats = []
    for op in others or []:
        try:
            o = cv2.imread(str(op))
            f = feature_of(o) if o is not None else None
            if f is not None:
                others_feats.append(f)
        except Exception:
            continue

    cap = _open_camera(camera_index)
    alvo = random.choice([("esquerda", -1), ("direita", 1)])
    fase, seq, frontais, best, last_feat = "frente", [], [], 0.0, None
    start, limite = time.time(), max(int(timeout), LIVENESS_MIN_TIMEOUT)
    win = "KEEPER - Reconhecimento facial"
    try:
        while time.time() - start < limite:
            ok, frame = cap.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            detector.setInputSize((frame.shape[1], frame.shape[0]))
            _, faces = detector.detect(frame)
            hud, cor = "Olhe de frente para a camera", (240, 240, 240)
            if faces is not None and len(faces) > 0:
                face = sorted(faces, key=lambda f: float(f[2] * f[3]), reverse=True)[0]
                q_ok, q_msg = _qualidade_face(frame, face)
                yaw = _yaw(face)
                feat = recognizer.feature(recognizer.alignCrop(frame, face))
                score = float(recognizer.match(ref_feat, feat, cv2.FaceRecognizerSF_FR_COSINE))
                best = max(best, score)
                x, y, w, h = [int(v) for v in face[:4]]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (60, 210, 70) if score >= thr else (60, 80, 220), 3)
                if not q_ok:
                    hud, seq = q_msg, []
                elif fase == "frente":
                    if score >= thr and abs(yaw) < 0.18:
                        seq.append(score); last_feat = feat
                    else:
                        seq = []
                    hud = f"Confirmando rosto {len(seq)}/{FACE_FRONTAL_FRAMES}"
                    if len(seq) >= FACE_FRONTAL_FRAMES:
                        frontais, fase, seq = seq[:], "virar", []
                elif fase == "virar":
                    hud, cor = f"PROVA DE VIDA: vire a cabeca para a {alvo[0].upper()}", (80, 200, 255)
                    if yaw * alvo[1] >= 0.30 and score >= thr - 0.12:
                        fase, seq = "voltar", []
                else:  # voltar
                    hud = f"Volte de frente {len(seq)}/3"
                    if score >= thr and abs(yaw) < 0.18:
                        seq.append(score); last_feat = feat
                    else:
                        seq = []
                    if len(seq) >= 3:
                        final = float(sum(frontais + seq) / len(frontais + seq))
                        for of in others_feats:
                            if float(recognizer.match(of, last_feat, cv2.FaceRecognizerSF_FR_COSINE)) >= final - 0.05:
                                return False, final, "Rosto ambíguo com outro usuário: acesso negado"
                        cv2.putText(frame, "ROSTO CONFIRMADO", (x, y + h + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 220, 70), 2, cv2.LINE_AA)
                        cv2.imshow(win, frame); cv2.waitKey(700)
                        return True, final, "Rosto reconhecido com prova de vida"
                cv2.putText(frame, f"SIMILARIDADE: {score:.3f}", (x, max(22, y - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2, cv2.LINE_AA)
            cv2.putText(frame, hud, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2, cv2.LINE_AA)
            cv2.putText(frame, "ESC = cancelar", (20, frame.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
            cv2.imshow(win, frame)
            if (cv2.waitKey(1) & 0xFF) == 27:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    if fase == "frente":
        return False, best, "Rosto não reconhecido"
    return False, best, "Prova de vida não concluída"
