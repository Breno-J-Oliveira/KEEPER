from __future__ import annotations

import asyncio
import time
from pathlib import Path

import flet as ft

import db
import extras
import security as sec
from ui import *


def dot(color, size=8):
    """Bolinha de status usada na barra CÂMERA / OCR / FACE / BANCO."""
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size)

BASE = Path(__file__).resolve().parent


extras.init()


def main(page: ft.Page):
    init_page(page, "KEEPER — Máquina de Portaria")
    state = {"step": 0, "sentido": "ENTRADA", "placa": "", "vehicle": None, "user": None, "token": "", "score": 0.0, "sid": None, "busy": False, "result": "", "plate_check": None, "plate_test_path": "", "plate_test_read": "", "plate_test_candidates": [], "plate_test_raw": "", "plate_test_expected": "", "plate_test_match": None, "sys": {"db": True, "ocr": False, "face": False, "cam": None}}

    def set_step(n: int):
        state["step"] = n; show()

    def reset(e=None):
        state.update(step=0, placa="", vehicle=None, user=None, token="", score=0.0, sid=None, result="", busy=False)
        show()

    async def _probe_system():
        """Verifica o estado real dos subsistemas (sem fingir disponibilidade)."""
        def probe():
            try:
                state["sys"]["db"] = bool(db.dashboard_resumo() or True)
            except Exception:
                state["sys"]["db"] = False
            state["sys"]["ocr"] = sec.ocr_disponivel()
            state["sys"]["face"] = sec.face_models_prontos()
            try:
                import cv2 as _cv
                cap = _cv.VideoCapture(int(db.get_config("camera_index", "0")))
                ok = cap.isOpened()
                if ok:
                    ok = bool(cap.read()[0])
                cap.release()
                state["sys"]["cam"] = bool(ok)
            except Exception:
                state["sys"]["cam"] = False
        await asyncio.to_thread(probe)
        try:
            page.update()
        except Exception:
            pass

    def system_strip():
        s = state["sys"]

        def item(label, ok):
            color = GREEN if ok else (MUTED if ok is None else RED)
            txt = "ONLINE" if ok else ("—" if ok is None else "OFFLINE")
            return ft.Row([dot(color), ft.Text(f"{label} {txt}", size=9, weight=ft.FontWeight.W_700, color=MUTED)], tight=True, spacing=4)

        db_ok = s.get("db", True)
        port = db.get_config("portaria_nome", "PORTARIA 01")
        return ft.Column([
            ft.Row([pill(port, ft.Icons.DNS, BEIGE, INK), ft.Container(expand=True), status_pill("ONLINE" if db_ok else "OFFLINE", db_ok)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([item("CÂMERA", s.get("cam")), item("OCR", s.get("ocr")), item("FACE", s.get("face")), item("BANCO", db_ok)], alignment=ft.MainAxisAlignment.START, wrap=True, spacing=10),
        ], spacing=6)

    def step_card(num, title, subtitle, active=False, done=False):
        bg = OLIVE_SOFT if done else (BEIGE if active else SURFACE_2)
        icon = ft.Icons.CHECK if done else (ft.Icons.RADIO_BUTTON_CHECKED if active else ft.Icons.RADIO_BUTTON_UNCHECKED)
        return card(ft.Row([
            ft.Container(width=42, height=42, bgcolor=bg, border_radius=14, alignment=ft.alignment.center, content=ft.Icon(icon, color=OLIVE_DARK if done or active else MUTED)),
            ft.Column([ft.Text(f"{num}. {title}", size=13, weight=ft.FontWeight.W_800, color=INK), ft.Text(subtitle, size=9, color=MUTED)], expand=True),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=12)

    async def scan_plate_camera(e):
        if state["busy"]: return
        state["busy"] = True; show()
        try:
            p = await asyncio.to_thread(sec.capture_plate_ocr, int(db.get_config("camera_index", "0")), int(db.get_config("ocr_timeout", "25")))
            if p: await accept_plate(p)
            else: notify(page, "OCR não encontrou a placa. Você pode informar manualmente.", False)
        except Exception as ex: notify(page, f"OCR: {ex}", False)
        finally: state["busy"] = False; show()

    def manual_plate(e):
        f = text_field("Placa", hint="ABC1D23 ou ABC-1234"); err = ft.Text("", size=10, color=RED)
        def save(e2):
            p = sec.normalizar_placa(f.value or "")
            if not sec.validar_placa(p): err.value = "Formato de placa inválido."; page.update(); return
            page.close(d); page.run_task(accept_plate, p)
        d = ft.AlertDialog(modal=True, title=ft.Text("Informar placa", color=INK), content=ft.Column([f, err], tight=True), actions=[ft.TextButton("Cancelar", on_click=lambda e2: page.close(d)), primary("Continuar", save)])
        page.open(d)

    async def accept_plate(p):
        """Valida a placa e avança para o QR somente com veículo+usuário válidos."""
        p = sec.normalizar_placa(p); state["placa"] = p
        state["plate_check"] = None
        bloq = extras.placa_bloqueada(p)
        if bloq:
            state["plate_check"] = {"ok": False, "identificada": p, "cadastrada": "—", "motivo": f"Placa BLOQUEADA: {bloq}"}
            state["vehicle"] = None; state["user"] = None
            db.auditar(None, "NEGADO", "PLACA", None, f"Placa bloqueada {p}")
            set_step(0); notify(page, f"Placa bloqueada: {bloq}", False); return
        v = db.veiculo_por_placa(p)
        if not v:
            state["plate_check"] = {"ok": False, "identificada": p, "cadastrada": "—", "motivo": "Placa não cadastrada ou veículo inativo."}
            state["vehicle"] = None; state["user"] = None
            set_step(0); notify(page, "Placa não cadastrada ou veículo inativo.", False); return
        u = db.usuario_por_id(v["id_usuario"])
        if not u or u["status_conta"] != "ATIVO":
            state["plate_check"] = {"ok": False, "identificada": p, "cadastrada": p, "motivo": "O proprietário desta placa está com a conta inativa."}
            state["vehicle"] = None; state["user"] = None
            set_step(0); notify(page, "O proprietário desta placa está com a conta inativa.", False); return
        if state["sentido"] == "ENTRADA" and db.esta_dentro(u["id_usuario"]):
            state["plate_check"] = {"ok": False, "identificada": p, "cadastrada": p, "motivo": "Este funcionário já está dentro da empresa."}
            state["vehicle"] = None; state["user"] = None
            set_step(0); notify(page, "Este funcionário já está dentro da empresa.", False); return
        if state["sentido"] == "SAIDA" and not db.esta_dentro(u["id_usuario"]):
            state["plate_check"] = {"ok": False, "identificada": p, "cadastrada": p, "motivo": "Este funcionário não está registrado dentro."}
            state["vehicle"] = None; state["user"] = None
            set_step(0); notify(page, "Este funcionário não está registrado dentro.", False); return
        state["vehicle"] = v; state["user"] = u
        state["plate_check"] = {"ok": True, "identificada": p, "cadastrada": p, "motivo": f"Veículo identificado: {u['nome_completo']}."}
        set_step(1); notify(page, f"Veículo identificado: {u['nome_completo']}.")

    def plate_check_card():
        """Painel de comparação: IMAGEM/IDENTIFICADA × CADASTRADA × RESULTADO."""
        c = state.get("plate_check")
        if not c:
            return ft.Container(height=0)
        ok = bool(c.get("ok"))
        return card(ft.Column([
            ft.Text("VERIFICAÇÃO DE PLACA", size=10, color=MUTED, weight=ft.FontWeight.W_700),
            ft.Row([
                ft.Column([ft.Text("PLACA IDENTIFICADA", size=9, color=MUTED), ft.Text(c.get("identificada") or "—", size=22, weight=ft.FontWeight.W_800, color=INK)], spacing=1, expand=True),
                ft.Column([ft.Text("PLACA CADASTRADA", size=9, color=MUTED), ft.Text(c.get("cadastrada") or "—", size=22, weight=ft.FontWeight.W_800, color=INK)], spacing=1, expand=True),
            ], spacing=12),
            ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if ok else ft.Icons.CANCEL, color=GREEN if ok else RED, size=20),
                ft.Text("CORRESPONDENTE" if ok else "NÃO CORRESPONDE", size=13, weight=ft.FontWeight.W_800, color=GREEN if ok else RED),
            ], tight=True, spacing=6),
            ft.Text(c.get("motivo") or "", size=10, color=MUTED),
        ], spacing=7), padding=14)

    async def scan_qr_camera(e):
        if not state["vehicle"] or state["busy"]: return
        state["busy"] = True; show()
        try:
            token = await asyncio.to_thread(sec.capture_qr, int(db.get_config("camera_index", "0")))
            if token: await accept_qr(token)
            else: notify(page, "QR não lido. Tente novamente ou informe o token manualmente.", False)
        except Exception as ex: notify(page, f"Leitor QR: {ex}", False)
        finally: state["busy"] = False; show()

    def manual_qr(e):
        f = text_field("Token da credencial QR", hint="Cole o conteúdo do QR"); err = ft.Text("", size=10, color=RED)
        def save(e2):
            if not sec.validar_token(f.value or ""): err.value = "Token inválido, adulterado ou expirado."; page.update(); return
            page.close(d); page.run_task(accept_qr, f.value.strip())
        d = ft.AlertDialog(modal=True, title=ft.Text("Informar QR", color=INK), content=ft.Column([f, err], tight=True), actions=[ft.TextButton("Cancelar", on_click=lambda e2: page.close(d)), primary("Validar", save)])
        page.open(d)

    async def accept_qr(token):
        uid = sec.validar_token(token); state["token"] = token or ""
        if uid is None:
            notify(page, "QR inválido, adulterado ou expirado.", False); return
        if not state["vehicle"] or uid != state["vehicle"]["id_usuario"]:
            notify(page, "QR pertence a outro funcionário. O acesso foi bloqueado.", False); return
        state["user"] = db.usuario_por_id(uid) or state["user"]
        set_step(2); notify(page, "QR validado. Iniciando reconhecimento facial.")

    async def recognize(e):
        u = state["user"]
        if not u: return
        ref = u.get("foto_facial_path")
        if not ref or not Path(ref).exists():
            notify(page, "Este funcionário não possui rosto cadastrado. O ADM ou o funcionário deve cadastrar/recadastrar a biometria.", False); return
        state["busy"] = True; show()
        try:
            outras = [x["foto_facial_path"] for x in db.listar_usuarios("", False) if x["id_usuario"] != u["id_usuario"] and x.get("foto_facial_path") and Path(x["foto_facial_path"]).exists()]
            ok, score, msg = await asyncio.to_thread(sec.recognize_camera_against, ref, int(db.get_config("camera_index", "0")), 25, float(db.get_config("face_threshold", "0.45")), outras)
            state["score"] = score
            if ok:
                state["result"] = msg; set_step(3); notify(page, f"Rosto confirmado. Similaridade {score:.3f}.")
            else:
                notify(page, f"{msg}. Melhor similaridade: {score:.3f}.", False)
        except Exception as ex: notify(page, f"Reconhecimento facial: {ex}", False)
        finally:
            state["busy"] = False; show()

    def create_request(e):
        if state.get("busy_request"):
            return
        if not state["user"] or not state["vehicle"] or not state["token"]:
            notify(page, "Complete placa, QR e rosto antes de enviar o pedido.", False); return
        if state["step"] < 3:
            notify(page, "O reconhecimento facial ainda não foi concluído.", False); return
        if state.get("sid"):
            notify(page, "Já existe um pedido em andamento.", False); return
        state["busy_request"] = True
        try:
            sid = db.criar_solicitacao(state["user"]["id_usuario"], state["vehicle"]["id_veiculo"], state["placa"], state["token"], state["score"], state["sentido"], db.get_config("portaria_nome", "PORTARIA 01"))
            db.auditar(None, "CREATE", "SOLICITACAO", sid, f"Máquina criou solicitação {state['sentido']}")
            state["sid"] = sid; state["step"] = 4; show(); page.run_task(wait_for_response, sid)
        except Exception as ex: notify(page, str(ex), False)
        finally: state["busy_request"] = False

    async def wait_for_response(sid: int):
        """Polling do estado da solicitação com término garantido (nunca trava)."""
        try:
            uid = int(state["user"]["id_usuario"]) if state.get("user") else None
            vid = int(state["vehicle"]["id_veiculo"]) if state.get("vehicle") else None
            sentido = state.get("sentido", "ENTRADA")
            portaria = db.get_config("portaria_nome", "PORTARIA 01")
        except Exception:
            return
        if uid is None or vid is None:
            return
        deadline = time.time() + int(db.get_config("auto_expire_seconds", "45")) + 8
        while time.time() < deadline:
            if state.get("sid") != sid:
                return  # Atendimento foi cancelado ou reiniciado: encerra silenciosamente.
            try:
                req = db.solicitacao_por_id(sid)
                if not req:
                    state["result"] = "Solicitação não encontrada."
                    state["step"] = 6
                    state["sid"] = None
                    show()
                    notify(page, state["result"], False)
                    return

                if req["status"] == "CONFIRMADA":
                    # Pequena janela de retentativa para dar tempo ao SQLite de liberar
                    # qualquer transação concorrente entre os dois processos.
                    finalized = False
                    for _ in range(8):
                        if state.get("sid") != sid:
                            return
                        finalized = db.finalizar_solicitacao(sid, uid, vid, sentido, portaria)
                        if finalized:
                            break
                        await asyncio.sleep(0.5)
                        refreshed = db.solicitacao_por_id(sid)
                        if not refreshed or refreshed["status"] != "CONFIRMADA":
                            finalized = refreshed is not None and refreshed["status"] == "FINALIZADA"
                            break
                    if state.get("sid") != sid:
                        return
                    acao = "entrada" if sentido == "ENTRADA" else "saída"
                    state["result"] = f"Portão aberto e {acao} registrada." if finalized else "Confirmação recebida, mas o registro não foi concluído."
                    try:
                        db.auditar(None, "FINALIZE", "SOLICITACAO", sid, state["result"])
                    except Exception:
                        pass
                    state["step"] = 5 if finalized else 6
                    state["sid"] = None
                    show()
                    notify(page, state["result"], finalized)
                    return

                if req["status"] in ("RECUSADA", "EXPIRADA", "CANCELADA"):
                    if state.get("sid") != sid:
                        return
                    state["result"] = {"RECUSADA": "Recusado pelo funcionário.", "EXPIRADA": "Solicitação expirada.", "CANCELADA": "Solicitação cancelada pelo ADM."}[req["status"]]
                    state["step"] = 6
                    state["sid"] = None
                    show()
                    notify(page, state["result"], False)
                    return
            except Exception as ex:
                print("KEEPER gate polling:", ex)
            await asyncio.sleep(0.6)
        if state.get("sid") != sid:
            return
        state["result"] = "Tempo expirado sem confirmação."
        state["step"] = 6
        state["sid"] = None
        show()
        notify(page, state["result"], False)

    async def test_plate_photo(e):
        """Teste de placa por foto: imagem → preview → OCR → leitura → esperado → comparação."""
        if state.get("busy"):
            return
        state["busy"] = True
        try:
            path = await asyncio.to_thread(sec.escolher_imagem_placa)
        except Exception as ex:
            state["busy"] = False; show(); notify(page, f"Seletor de arquivos: {ex}", False); return
        if not path:
            state["busy"] = False; show(); return
        state["plate_test_path"] = path
        state["plate_test_read"] = ""
        state["plate_test_candidates"] = []
        state["plate_test_raw"] = ""
        state["plate_test_match"] = None
        state["plate_test_expected"] = state.get("placa") or ""
        show()
        try:
            read, candidates, raw = await asyncio.to_thread(sec.ocr_placa_foto, path)
            state["plate_test_read"] = read or ""
            state["plate_test_candidates"] = list(candidates or [])
            state["plate_test_raw"] = raw or ""
            if read:
                notify(page, f"OCR identificou a placa {read}.")
            else:
                notify(page, "O OCR não identificou uma placa válida nesta imagem.", False)
        except Exception as ex:
            notify(page, f"OCR: {ex}", False)
        finally:
            state["busy"] = False; show()

    def plate_test_preview():
        try:
            import base64 as _b64
            data = Path(state["plate_test_path"]).read_bytes()
            return ft.Image(src_base64=_b64.b64encode(data).decode("ascii"), width=460, height=260, fit=ft.ImageFit.CONTAIN, border_radius=R_MD)
        except Exception:
            return ft.Container(width=460, height=120, bgcolor=SURFACE_2, border_radius=R_MD, alignment=ft.alignment.center, content=ft.Text(state["plate_test_path"] or "Imagem indisponível", size=10, color=MUTED, text_align=ft.TextAlign.CENTER))

    def compare_plate_test(e):
        expected = sec.normalizar_placa(plate_expected.value or "")
        if not sec.validar_placa(expected):
            plate_err.value = "Informe uma placa esperada válida (ex.: ABC1D23)."; page.update(); return
        plate_err.value = ""
        if not state["plate_test_read"]:
            state["plate_test_match"] = False
            plate_result.value = "O OCR não identificou nenhuma placa para comparar."
        elif state["plate_test_read"] == expected:
            state["plate_test_match"] = True
            plate_result.value = "✓ CORRESPONDE — a leitura é igual à placa esperada."
        else:
            state["plate_test_match"] = False
            plate_result.value = "✕ NÃO CORRESPONDE — a leitura difere da placa esperada."
        plate_result.color = GREEN if state["plate_test_match"] else RED
        page.update()

    def use_plate_test(e):
        read = state.get("plate_test_read") or ""
        if not read or not sec.validar_placa(read):
            notify(page, "Não há uma leitura válida para continuar.", False); return
        state.update(plate_test_path="", plate_test_read="", plate_test_candidates=[], plate_test_raw="", plate_test_expected="", plate_test_match=None)
        page.run_task(accept_plate, read)

    def new_plate_test(e):
        state.update(plate_test_path="", plate_test_read="", plate_test_candidates=[], plate_test_raw="", plate_test_expected="", plate_test_match=None)
        page.run_task(test_plate_photo, e)

    def reset_plate_test(e=None):
        state.update(plate_test_path="", plate_test_read="", plate_test_candidates=[], plate_test_raw="", plate_test_expected="", plate_test_match=None)
        plate_expected.value = ""
        plate_err.value = ""
        plate_result.value = ""
        if e is not None:
            show()

    plate_expected = text_field("Placa esperada", hint="ABC1D23 ou ABC-1234")
    plate_err = ft.Text("", size=10, color=RED)
    plate_result = ft.Text("", size=12, weight=ft.FontWeight.W_800)

    def plate_test_panel():
        kids = [
            ft.Text("TESTE DE PLACA POR FOTO", size=10, color=MUTED, weight=ft.FontWeight.W_700),
            ft.Text("Selecione uma imagem, confira a leitura do OCR e compare com a placa esperada.", size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
            plate_test_preview(),
        ]
        if state["busy"]:
            kids.append(ft.Row([ft.ProgressRing(color=OLIVE, width=22, height=22), ft.Text("Processando imagem…", size=11, color=MUTED)], alignment=ft.MainAxisAlignment.CENTER, spacing=8))
        if state["plate_test_read"] or state["plate_test_candidates"]:
            read_ok = bool(state["plate_test_read"]) and sec.validar_placa(state["plate_test_read"])
            kids.append(ft.Row([
                ft.Column([ft.Text("PLACA IDENTIFICADA", size=9, color=MUTED), ft.Text(state["plate_test_read"] or "—", size=24, weight=ft.FontWeight.W_800, color=INK)], spacing=1, expand=True),
                status_pill("VÁLIDA" if read_ok else "NÃO IDENTIFICADA", read_ok),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
            if state["plate_test_candidates"]:
                kids.append(ft.Text("Candidatos: " + ", ".join(state["plate_test_candidates"]), size=10, color=MUTED, text_align=ft.TextAlign.CENTER))
            if (state["plate_test_raw"] or "").strip():
                kids.append(ft.Text("OCR bruto: " + state["plate_test_raw"][:160], size=9, color=MUTED, text_align=ft.TextAlign.CENTER))
            if not plate_expected.value:
                plate_expected.value = state.get("plate_test_expected") or state.get("placa") or ""
            kids += [plate_expected, plate_err, primary("Comparar com placa esperada", compare_plate_test, ft.Icons.COMPARE_ARROWS, 360), plate_result]
        kids += [ft.Row([secondary("Nova imagem", new_plate_test, ft.Icons.IMAGE_OUTLINED), secondary("Fechar", reset_plate_test, ft.Icons.CLOSE)], alignment=ft.MainAxisAlignment.CENTER, spacing=8, wrap=True)]
        if state["plate_test_read"] and sec.validar_placa(state["plate_test_read"]):
            kids.append(primary("Continuar com esta placa", use_plate_test, ft.Icons.ARROW_FORWARD, 360))
        return card(ft.Column(kids, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8), padding=22)

    def demo_entry(e):
        users = [u for u in db.listar_usuarios('', False) if u['tipo_acesso'] == 'FUNCIONARIO']
        options = []
        for u in users:
            cars=db.listar_veiculos(u['id_usuario'])
            if cars:
                options.append((u,cars[0]))
        if not options: notify(page,"Nenhum funcionário/veículo ativo disponível.",False);return
        userdd=ft.Dropdown(label='Funcionário / veículo',options=[ft.dropdown.Option(str(u['id_usuario']),f"{u['nome_completo']} · {v['placa']}") for u,v in options])
        direction=ft.Dropdown(label='Sentido',options=[ft.dropdown.Option('ENTRADA'),ft.dropdown.Option('SAIDA')],value=state['sentido'])
        def go(e2):
            pair=next((x for x in options if x[0]['id_usuario']==int(userdd.value)),None)
            if not pair:return
            u,v=pair
            state.update(placa=v['placa'],vehicle=v,user=u,token=sec.gerar_token(u['id_usuario']),score=1.0,step=3,result='Modo demonstração',sentido=direction.value or 'ENTRADA')
            page.close(d);show()
        d=ft.AlertDialog(modal=True,title=ft.Text('Demonstração controlada',color=INK),content=ft.Column([userdd,direction],tight=True),actions=[ft.TextButton('Cancelar',on_click=lambda e2:page.close(d)),primary('Continuar',go)])
        page.open(d)

    def show():
        # Máquina de estados do atendimento.
        # IDLE(0) → PLACA(1) → QR(2) → FACE(3) → AGUARDANDO(4) → OK(5)/BLOQUEADO(6).
        step = state['step']; v = state['vehicle']; u = state['user']
        status_title = {0: 'Aguardando veículo', 1: 'Placa validada', 2: 'QR validado', 3: 'Identidade confirmada', 4: 'Aguardando confirmação', 5: 'Portão aberto', 6: 'Acesso bloqueado'}.get(step, 'Aguardando')
        status_color = GREEN if step in (3, 5) else (RED if step == 6 else OLIVE_DARK)
        header = ft.Column([
            ft.Row([ft.Column([ft.Text('KEEPER', size=12, weight=ft.FontWeight.W_800, color=OLIVE_DARK), ft.Text('Terminal de portaria', size=25, weight=ft.FontWeight.W_800, color=INK)], spacing=0, expand=True), pill(f'ETAPA {step}/5', None, BEIGE, INK)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            system_strip(),
        ], spacing=8)
        mode = ft.Row([pill('ENTRADA' if state['sentido'] == 'ENTRADA' else 'SAÍDA', ft.Icons.LOGIN if state['sentido'] == 'ENTRADA' else ft.Icons.LOGOUT, OLIVE_SOFT if state['sentido'] == 'ENTRADA' else BROWN_SOFT, INK), ft.Container(expand=True), ft.TextButton('Trocar sentido', on_click=lambda e: toggle_direction())], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        if state.get("plate_test_path"):
            center = plate_test_panel()
        elif step == 0:
            center = ft.Column([
                card(ft.Column([
                    ft.Container(width=90, height=90, bgcolor=OLIVE_SOFT, border_radius=45, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.DIRECTIONS_CAR, size=50, color=OLIVE_DARK)),
                    ft.Text('Aproxime o veículo', size=24, weight=ft.FontWeight.W_800, color=INK, text_align=ft.TextAlign.CENTER),
                    ft.Text('A máquina valida placa, QR Code, rosto e só então pede a confirmação no celular.', size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
                    primary('Ler placa pela câmera', lambda e: page.run_task(scan_plate_camera, e), ft.Icons.CAMERA_ALT, 360),
                    secondary('Informar placa manualmente', manual_plate, ft.Icons.KEYBOARD, 360),
                    secondary('Testar placa por foto', lambda e: page.run_task(test_plate_photo, e), ft.Icons.IMAGE_OUTLINED, 360),
                    ft.TextButton('Abrir modo demonstração', on_click=demo_entry),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8), padding=24),
                plate_check_card(),
            ], spacing=8)
        elif step==1:
            center=ft.Column([step_card(1,'Placa reconhecida',f"{state['placa']} · {v['modelo'] if v else ''}",True,True),step_card(2,'Ler QR Code','Escaneie a credencial que aparece no app do funcionário.',True,False),primary('Abrir leitor QR',lambda e:page.run_task(scan_qr_camera,e),ft.Icons.QR_CODE_SCANNER,360),secondary('Informar QR manualmente',manual_qr,ft.Icons.KEYBOARD,360),card(ft.Row([avatar(u['nome_completo'],40),ft.Column([ft.Text(u['nome_completo'],weight=ft.FontWeight.W_700,color=INK),ft.Text(f"{state['placa']} · {v.get('modelo') if v else ''}",size=10,color=MUTED)],expand=True),pill('VEÍCULO OK',ft.Icons.CHECK_CIRCLE,OLIVE_SOFT,INK)],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=12)],spacing=8)
        elif step==2:
            center=ft.Column([step_card(1,'Placa',state['placa'],False,True),step_card(2,'QR Code','Credencial vinculada ao proprietário da placa.',False,True),step_card(3,'Reconhecimento facial','Compare o rosto capturado com o cadastro biométrico.',True,False),primary('Iniciar reconhecimento facial',recognize,ft.Icons.FACE,360),secondary('Voltar para QR',lambda e:set_step(1),ft.Icons.ARROW_BACK,360)],spacing=8)
        elif step==3:
            center=ft.Column([card(ft.Column([ft.Container(width=84,height=84,bgcolor=OLIVE_SOFT,border_radius=42,alignment=ft.alignment.center,content=ft.Icon(ft.Icons.VERIFIED_USER,size=48,color=OLIVE_DARK)),ft.Text('IDENTIDADE CONFIRMADA',size=22,weight=ft.FontWeight.W_800,color=INK,text_align=ft.TextAlign.CENTER),ft.Text(f"{u['nome_completo']} · {state['placa']}",size=11,color=MUTED),pill(f"FACE {state['score']:.3f}",ft.Icons.FACE,OLIVE_SOFT,INK)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8),padding=24),primary('Enviar pedido ao funcionário',create_request,ft.Icons.PHONE_ANDROID,360),secondary('Reiniciar',reset,ft.Icons.RESTART_ALT,360)],spacing=8)
        elif step==4:
            center=ft.Column([step_card(1,'Placa',state['placa'],False,True),step_card(2,'QR Code','Validado',False,True),step_card(3,'Face',f"Validado · {state['score']:.3f}",False,True),card(ft.Column([ft.ProgressRing(color=OLIVE),ft.Text('Aguardando confirmação no celular…',size=17,weight=ft.FontWeight.W_800,color=INK,text_align=ft.TextAlign.CENTER),ft.Text('O funcionário precisa confirmar a passagem.',size=10,color=MUTED,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8),padding=24),secondary('Cancelar atendimento',lambda e:cancel_current(),ft.Icons.CANCEL_OUTLINED,360)],spacing=8)
        elif step == 5:
            who = f"{u['nome_completo']} · {state['placa']}" if u else state['placa']
            center = card(ft.Column([ft.Container(width=100, height=100, bgcolor=OLIVE_SOFT, border_radius=50, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.GARAGE, size=58, color=OLIVE_DARK)), ft.Text('PORTÃO ABERTO', size=26, weight=ft.FontWeight.W_800, color=INK), ft.Text(who, size=11, color=MUTED, text_align=ft.TextAlign.CENTER), pill('REGISTRADO NO BANCO', ft.Icons.STORAGE, OLIVE_SOFT, INK), primary('Novo atendimento', reset, ft.Icons.RESTART_ALT, 360)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=30)
        else:
            center = card(ft.Column([ft.Container(width=94, height=94, bgcolor=BROWN_SOFT, border_radius=47, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.BLOCK, size=54, color=BROWN)), ft.Text('ACESSO BLOQUEADO', size=24, weight=ft.FontWeight.W_800, color=INK, text_align=ft.TextAlign.CENTER), ft.Text(state['result'] or 'Operação não concluída.', size=11, color=MUTED, text_align=ft.TextAlign.CENTER), secondary('Tentar novamente', reset, ft.Icons.RESTART_ALT, 360)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=30)
        info = ft.Column([step_card(1, 'Placa', state['placa'] or 'Aguardando', False, step >= 1), step_card(2, 'QR Code', 'Validado' if step >= 2 else 'Aguardando', False, step >= 2), step_card(3, 'Face', f"{state['score']:.3f}" if step >= 3 else 'Aguardando', False, step >= 3)], spacing=7)
        body = ft.Column([header, mode, center, ft.Text('Validação', size=14, weight=ft.FontWeight.W_800, color=INK), info, ft.Divider(color=LINE), ft.Text('Últimos acessos', size=14, weight=ft.FontWeight.W_800, color=INK), *recent_events(), ft.Row([pill(f'ETAPA {step}/5', None, BEIGE, INK), ft.Container(expand=True), ft.Text(status_title, size=10, weight=ft.FontWeight.W_700, color=status_color)])], spacing=8)
        shell(page, body, 820)

    def recent_events():
        rows=db.historico(None,5)
        if not rows:return [card(ft.Text('Ainda não há registros.',size=10,color=MUTED),padding=10)]
        out=[]
        for r in rows:
            live=r['status_presenca']=='DENTRO';out.append(card(ft.Row([ft.Icon(ft.Icons.LOGIN if live else ft.Icons.LOGOUT,color=OLIVE_DARK if live else BROWN),ft.Column([ft.Text(f"{r['nome_completo']} · {r['placa']}",size=10,weight=ft.FontWeight.W_700,color=INK),ft.Text(f"{r['data_hora_entrada']} · {r['portaria']}",size=9,color=MUTED)],expand=True),pill(r['status_presenca'],None,OLIVE_SOFT if live else BROWN_SOFT,INK)],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=9))
        return out

    def cancel_current():
        sid = state.get('sid')
        if sid and db.cancelar_solicitacao(sid):
            try:
                db.auditar(None, 'CANCELAR', 'SOLICITACAO', sid, 'Cancelada na máquina')
            except Exception:
                pass
            notify(page, 'Atendimento cancelado.'); reset()
        else: notify(page, 'Não havia solicitação pendente.', False)

    def toggle_direction():
        state['sentido'] = 'SAIDA' if state['sentido'] == 'ENTRADA' else 'ENTRADA'
        reset()

    show()
    page.run_task(_probe_system)


if __name__=='__main__':
    ft.app(target=main, assets_dir=str(__import__("pathlib").Path(__file__).resolve().parent / "assets"))