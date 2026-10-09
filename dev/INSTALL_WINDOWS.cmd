@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo      KEEPER - INSTALADOR COMPLETO WINDOWS
echo ============================================

if not exist .venv (
  echo [1/7] Criando ambiente virtual...
  py -3.13 -m venv .venv
  if errorlevel 1 python -m venv .venv
) else (
  echo [1/7] Ambiente virtual ja existe.
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo ERRO: nao foi possivel ativar o ambiente.
  pause
  exit /b 1
)

echo [2/7] Atualizando pip...
python -m pip install --upgrade pip

echo [3/7] Removendo variantes conflitantes do OpenCV...
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python-headless >nul 2>&1

echo [4/7] Instalando dependencias Python...
pip install -r requirements.txt
if errorlevel 1 (
  echo ERRO na instalacao das dependencias Python.
  pause
  exit /b 1
)

echo [5/7] Instalando Tesseract OCR (se Winget estiver disponivel)...
where winget >nul 2>nul
if %errorlevel%==0 (
  winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
) else (
  echo Winget nao encontrado. Instale Tesseract manualmente para OCR de placas.
)

echo [6/7] Baixando modelos YuNet + SFace...
python download_models.py
if errorlevel 1 echo AVISO: modelos nao foram baixados. Rode depois: python download_models.py

echo [7/7] Validando instalacao...
python -c "import flet,bcrypt,qrcode,cv2,numpy,PIL,pytesseract; print('PYTHON OK'); print('OpenCV:',cv2.__version__); print('FaceDetectorYN:',hasattr(cv2,'FaceDetectorYN')); print('FaceRecognizerSF:',hasattr(cv2,'FaceRecognizerSF')); print('QRCodeDetector:',hasattr(cv2,'QRCodeDetector'))"

if errorlevel 1 (
  echo ERRO: validacao falhou.
  pause
  exit /b 1
)

echo.
echo ============================================
echo INSTALACAO CONCLUIDA.
echo ============================================
echo Rode: RUN_DEMO.cmd
pause
endlocal
