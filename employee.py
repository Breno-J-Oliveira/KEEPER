from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

import flet as ft

import db
import extras
import security as sec
from ui import *

BASE = Path(__file__).resolve().parent


extras.init()


def main(page: ft.Page):
    init_page(page, "KEEPER — Funcionário")
    state = {"user": None, "page": "home", "polling": False, "shown_sid": None, "dialog": None, "qr_gen": 0, "busy_login": False}

    EMP_NAV = [("home", ft.Icons.HOME_OUTLINED, "Início"), ("access", ft.Icons.RECEIPT_LONG_OUTLINED, "Acessos"), ("vehicles", ft.Icons.DIRECTIONS_CAR_OUTLINED, "Veículos"), ("account", ft.Icons.PERSON_OUTLINE, "Conta"), ("notifications", ft.Icons.NOTIFICATIONS_NONE, "Avisos")]

    def emp_nav(selected):
        return bottom_nav(EMP_NAV, selected, nav)

    def refresh_user():
        if state["user"]:
            fresh = db.usuario_por_id(state["user"]["id_usuario"])
            if fresh:
                state["user"] = fresh

    def go_login(_=None):
        state["user"] = None
        login = text_field("E-mail ou usuário", icon=ft.Icons.PERSON_OUTLINE)
        senha = text_field("Senha", password=True, icon=ft.Icons.LOCK_OUTLINE)
        error = ft.Text("", size=11, color=RED, text_align=ft.TextAlign.CENTER)
        entrar_btn, guardar_entrar = busy_primary("Entrar", "Verificando…", ft.Icons.LOGIN, 420)

        def entrar(e):
            login.error_text = None
            senha.error_text = None
            if not (login.value or "").strip():
                login.error_text = "Informe o usuário."
            if not senha.value:
                senha.error_text = "Informe a senha."
            if login.error_text or senha.error_text:
                page.update(); return
            user, err = db.autenticar(login.value.strip(), senha.value)
            if err:
                error.value = err; page.update(); return
            if user["tipo_acesso"] != "FUNCIONARIO":
                error.value = "Esta visão é exclusiva do funcionário."; page.update(); return
            state["user"] = user
            try:
                db.auditar(user["id_usuario"], "LOGIN", "FUNCIONARIO", user["id_usuario"], "Login no app do funcionário")
            except Exception:
                pass
            ensure_polling()
            show_home()

        entrar_btn.on_click = guardar_entrar(entrar)
        senha.on_submit = guardar_entrar(entrar)
        body = ft.Column([
            ft.Container(height=18), logo(small=True), ft.Container(height=14),
            ft.Text("Acessar conta", size=27, weight=ft.FontWeight.W_800, color=INK),
            ft.Text("Sua credencial, veículos e histórico em um só lugar.", size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
            ft.Container(height=7), login, senha,
            ft.Container(content=ft.TextButton("Esqueci minha senha", on_click=lambda e: show_forgot()), alignment=ft.alignment.center_right),
            entrar_btn, error,
            card(ft.Column([ft.Text("Contas de demonstração", size=11, weight=ft.FontWeight.W_700, color=INK), ft.Text("breno / Breno@123", size=10, color=MUTED)], spacing=3), padding=12, bgcolor=SURFACE_2),
            ft.TextButton("Criar conta", on_click=show_register),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=9)
        shell(page, body, 520)

    def show_forgot(e=None):
        login = text_field("E-mail ou usuário", icon=ft.Icons.PERSON_OUTLINE)
        codigo = text_field("Código de 6 dígitos (fornecido pelo administrador)", icon=ft.Icons.KEY)
        nova = text_field("Nova senha", password=True, icon=ft.Icons.LOCK_OUTLINE)
        msg = ft.Text("", size=11, color=RED, text_align=ft.TextAlign.CENTER)
        def pedir(ev):
            if not (login.value or "").strip(): msg.value = "Informe seu e-mail ou usuário."; page.update(); return
            extras.pedir_reset(login.value)  # resposta igual exista ou não a conta
            msg.color = GREEN; msg.value = "Pedido enviado. Solicite o código ao administrador e preencha abaixo."; page.update()
        def trocar(ev):
            erro = extras.redefinir_senha(login.value or "", codigo.value or "", nova.value or "")
            if erro: msg.color = RED; msg.value = erro; page.update(); return
            notify(page, "Senha redefinida. Faça login."); go_login()
        body = ft.Column([topbar("Esqueci minha senha", "Redefinição segura por código", back=lambda ev: go_login()), login,
                          secondary("1. Pedir redefinição", pedir, ft.Icons.SEND, 420), codigo, nova, primary("2. Trocar senha", trocar, ft.Icons.LOCK_RESET, 420), msg], spacing=9)
        shell(page, body, 520)

    def show_register(e=None):
        nome = text_field("Nome completo", icon=ft.Icons.PERSON_OUTLINE)
        username = text_field("Username", hint="3–30 caracteres", icon=ft.Icons.ALTERNATE_EMAIL)
        email = text_field("E-mail", icon=ft.Icons.EMAIL_OUTLINED)
        senha = text_field("Senha", password=True, icon=ft.Icons.LOCK_OUTLINE)
        confirmar = text_field("Confirmar senha", password=True, icon=ft.Icons.LOCK_OUTLINE)
        placa = text_field("Placa do veículo (opcional)", hint="ABC1D23 ou ABC-1234", icon=ft.Icons.DIRECTIONS_CAR_OUTLINED)
        modelo = text_field("Modelo (ex.: Honda Civic)", icon=ft.Icons.TIME_TO_LEAVE_OUTLINED)
        cor = text_field("Cor (ex.: Prata)", icon=ft.Icons.PALETTE_OUTLINED)
        face_status = ft.Text("Foto facial: não cadastrada", size=11, color=MUTED, text_align=ft.TextAlign.CENTER)
        error = ft.Text("", size=10, color=RED, text_align=ft.TextAlign.CENTER)
        face = {"path": None}

        async def capture(e):
            if page.web:
                face_status.value = "No celular, cadastre o rosto depois pelo computador/portaria (Conta → Rosto)"; face_status.color = RED; page.update(); return
            capture_button.disabled = True
            face_status.value = "Câmera aberta. ENTER/ESPAÇO salva a foto."
            face_status.color = MUTED
            page.update()
            try:
                path = BASE / "data" / "faces" / f"temp_{int(time.time()*1000)}.jpg"
                got = await asyncio.to_thread(sec.capturar_frame, path, int(db.get_config("camera_index", "0")), "KEEPER - Cadastro facial", True)
                q_ok, q_msg = sec.qualidade_foto(got) if got else (False, "")
                if got and q_ok:
                    face["path"] = got
                    face_status.value = "Rosto aprovado (nítido, de frente, bem iluminado)."
                    face_status.color = GREEN
                elif got:
                    face["path"] = None
                    face_status.value = f"Foto recusada: {q_msg} Tente novamente."
                    face_status.color = RED
                else:
                    face_status.value = "Captura cancelada."
                    face_status.color = RED
            except Exception as ex:
                face_status.value = f"Câmera: {ex}"
                face_status.color = RED
            finally:
                capture_button.disabled = False
                page.update()

        capture_button = secondary("Cadastrar foto facial", lambda e: page.run_task(capture, e), ft.Icons.CAMERA_ALT, 420)

        def create(e):
            n = (nome.value or "").strip(); u = (username.value or "").strip(); em = (email.value or "").strip().lower(); pw = senha.value or ""
            errors = []
            if len(n) < 3: errors.append("Informe o nome completo (mínimo 3 letras).")
            if not sec.RE_USER.fullmatch(u): errors.append("Username inválido: use 3–30 caracteres (letras, números, ponto ou sublinhado).")
            if not sec.RE_EMAIL.fullmatch(em): errors.append("E-mail inválido: verifique o endereço digitado.")
            if not sec.RE_SENHA.fullmatch(pw): errors.append("Senha fraca: use 8+ caracteres com maiúscula, minúscula e número.")
            if pw != (confirmar.value or ""): errors.append("As senhas não conferem. Digite novamente.")
            pl = sec.normalizar_placa(placa.value or "")
            if pl and not sec.validar_placa(pl): errors.append("Placa inválida: use ABC1D23 ou ABC-1234.")
            if errors:
                error.value = "\n".join(errors); page.update(); return
            create_btn.disabled = True; create_btn.text = "Criando conta…"; page.update()
            try:
                uid = db.criar_usuario(n, u, em, pw, "FUNCIONARIO")
                if face["path"]:
                    final = BASE / "data" / "faces" / f"usuario_{uid}.jpg"
                    shutil.move(face["path"], final)
                    db.atualizar_foto_facial(uid, str(final))
                if pl:
                    db.criar_veiculo(uid, pl, (modelo.value or "").strip(), (cor.value or "").strip())
                db.auditar(uid, "CREATE", "USUARIO", uid, "Cadastro pelo app do funcionário")
            except Exception as ex:
                error.value = f"Não foi possível criar a conta: {ex}"; page.update(); return
            finally:
                create_btn.disabled = False; create_btn.text = "Criar conta"
                try: page.update()
                except Exception: pass
            notify(page, "Conta criada. Agora faça login.")
            go_login()

        create_btn = primary("Criar conta", create, ft.Icons.PERSON_ADD_ALT_1, 420)

        body = ft.Column([
            topbar("Criar conta", "Novo funcionário", back=lambda e: go_login()), ft.Container(height=5),
            nome, username, email, senha, confirmar,
            ft.Text("Seu veículo", size=11, weight=ft.FontWeight.W_800, color=OLIVE_DARK), placa, modelo, cor,
            ft.Text("Reconhecimento facial", size=11, weight=ft.FontWeight.W_800, color=OLIVE_DARK), capture_button, face_status, error,
            ft.Text("A biometria é opcional agora e pode ser cadastrada depois em Conta.", size=9, color=MUTED, text_align=ft.TextAlign.CENTER),
            create_btn,
        ], spacing=9)
        shell(page, body, 520)

    def ensure_polling():
        if state["polling"]: return
        state["polling"] = True
        page.run_task(notification_loop)

    async def notification_loop():
        while state["user"]:
            try:
                refresh_user()
                pending = db.solicitacoes_pendentes_usuario(state["user"]["id_usuario"])
                pending_ids = {r["id_solicitacao"] for r in pending}
                if state["shown_sid"] is not None and state["shown_sid"] not in pending_ids:
                    # A solicitação expirou/foi respondida com o diálogo aberto: fecha.
                    try:
                        if state["dialog"] is not None:
                            page.close(state["dialog"])
                    except Exception:
                        pass
                    state["dialog"] = None
                    state["shown_sid"] = None
                if pending:
                    show_gate_confirmation(pending[0])
            except Exception as ex:
                log.warning("KEEPER notification polling: %s", ex)
            await asyncio.sleep(1.0)
        state["polling"] = False

    def show_gate_confirmation(req):
        if state["shown_sid"] == req["id_solicitacao"]:
            return
        # Fecha um diálogo anterior antes de abrir o novo.
        try:
            if state["dialog"] is not None:
                page.close(state["dialog"])
        except Exception:
            pass
        state["shown_sid"] = req["id_solicitacao"]
        sid = req["id_solicitacao"]; sentido = req["sentido"]
        title = "Confirme sua entrada" if sentido == "ENTRADA" else "Confirme sua saída"
        action_text = "Confirmar entrada" if sentido == "ENTRADA" else "Confirmar saída"
        answered = {"ok": False}

        def answer(ok):
            if answered["ok"]:
                return
            answered["ok"] = True
            try:
                if db.responder_solicitacao(sid, ok):
                    notify(page, "Confirmação enviada à portaria." if ok else "Acesso recusado.", ok)
                else:
                    notify(page, "Esta solicitação já expirou ou foi respondida.", False)
            except Exception as ex:
                notify(page, f"Não foi possível responder: {ex}", False)
            try:
                page.close(dialog)
            except Exception:
                pass
            state["dialog"] = None
            state["dialog"] = None
            state["shown_sid"] = None
            show_notifications()

        radar_box, rings = radar()
        u = state["user"]
        dialog = ft.AlertDialog(
            modal=True, bgcolor=BG, shape=ft.RoundedRectangleBorder(radius=22),
            content=ft.Container(width=340, content=ft.Column([
                ft.Text("Acesso detectado", size=22, weight=ft.FontWeight.W_800, color=INK),
                ft.Text(f"{req['portaria']} está sendo acionado.", size=12, color=MUTED),
                radar_box,
                card(ft.Row([car_image(req.get("modelo"), req.get("cor"), 96), ft.Column([ft.Text("Seu veículo", size=10, color=MUTED), ft.Text(req["placa"], size=24, weight=ft.FontWeight.W_900, color=INK),
                     ft.Text(f"{req.get('modelo') or ''} {('· ' + req['cor']) if req.get('cor') else ''}".strip(), size=11, color=MUTED)], spacing=0, expand=True)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=12),
                ft.Text(title + "?", weight=ft.FontWeight.W_800, color=INK),
                ft.Text("Ao confirmar, o portão será liberado. Placa + QR Code + face já foram validados.", size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
                primary(action_text, lambda e: answer(True), ft.Icons.CHECK_CIRCLE_OUTLINE, 340),
                ft.TextButton("Recusar", on_click=lambda e: answer(False)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10, tight=True)),
        )
        state["dialog"] = dialog
        page.open(dialog)
        page.run_task(pulse_rings, page, rings, lambda: not answered["ok"])

    async def refresh_qr(img, token_text, timer_text, status_text, updated_text, uid, gen):
        while state["user"] and state["user"]["id_usuario"] == uid and state["page"] == "home" and state["qr_gen"] == gen:
            try:
                token = sec.gerar_token(uid)
                remaining = 30 - int(time.time()) % 30
                img.src_base64 = sec.qr_base64(token)
                token_text.value = f"Token: {token[:16]}…"
                timer_text.value = f"Atualiza em 00:{remaining:02d}"
                updated_text.value = f"Última atualização: {time.strftime('%H:%M:%S')}"
                page.update()
            except Exception as ex:
                log.warning("refresh_qr: %s", ex)
            await asyncio.sleep(1)

    def show_home():
        refresh_user(); state["page"] = "home"; u = state["user"]
        cars = db.listar_veiculos(u["id_usuario"])
        inside = db.esta_dentro(u["id_usuario"])
        current = db.veiculo_dentro(u["id_usuario"])
        unread = db.contador_notificacoes(u["id_usuario"])
        qr = ft.Image(width=215, height=215, fit=ft.ImageFit.CONTAIN)
        token = ft.Text("", size=9, color=MUTED, text_align=ft.TextAlign.CENTER)
        countdown = ft.Text("", size=11, color=OLIVE_DARK, weight=ft.FontWeight.W_700)
        updated = ft.Text("Última atualização: —", size=9, color=MUTED, text_align=ft.TextAlign.CENTER)
        cred_status = ft.Row([ft.Container(width=0)], tight=True)

        def out(e):
            if current and db.registrar_saida(u["id_usuario"], current["id_veiculo"], "SAIDA_MANUAL", "APP FUNCIONARIO"):
                db.auditar(u["id_usuario"], "CREATE", "ACESSO", current["id_registro"], "Saída manual pelo aplicativo")
                notify(page, "Saída registrada."); show_home()
            else:
                notify(page, "Não foi possível registrar a saída.", False)

        first = cars[0] if cars else None
        body = ft.Column([
            ft.Row([ft.Column([ft.Text("Olá,", size=12, color=MUTED), ft.Text(u["nome_completo"].split()[0], size=24, weight=ft.FontWeight.W_800, color=INK)], spacing=0, expand=True), avatar(u["nome_completo"])], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([pill("PRESENÇA: DENTRO" if inside else "PRESENÇA: FORA", ft.Icons.CHECK_CIRCLE if inside else ft.Icons.LOGOUT, OLIVE_SOFT if inside else BEIGE, INK), ft.Container(expand=True), ft.IconButton(ft.Icons.NOTIFICATIONS_NONE, on_click=lambda e: show_notifications(), icon_color=OLIVE_DARK, tooltip="Notificações") , ft.Text(str(db.contador_notificacoes(u["id_usuario"])), size=10, color=OLIVE_DARK, weight=ft.FontWeight.W_800) if db.contador_notificacoes(u["id_usuario"]) else ft.Container(width=0)], spacing=4),
            card(ft.Column([
                ft.Row([ft.Text("CREDENCIAL KEEPER", size=10, color=MUTED, weight=ft.FontWeight.W_700), ft.Container(expand=True), status_pill("DENTRO" if inside else "VÁLIDA", True)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(content=qr, alignment=ft.alignment.center, bgcolor=WHITE, border_radius=18, padding=8),
                countdown, token, updated,
                ft.Text(f"{u['nome_completo']} · @{u['username']}", size=10, color=MUTED, text_align=ft.TextAlign.CENTER),
                ft.Text("Apresente este QR na máquina de portaria.", size=10, color=MUTED, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=7), padding=16),
            ft.Row([ft.Text("Veículos", size=15, weight=ft.FontWeight.W_800, color=INK), ft.Container(expand=True), ft.TextButton("Gerenciar", on_click=lambda e: show_vehicles())]),
            card(ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR_FILLED, size=30, color=BROWN), ft.Column([ft.Text(first["placa"], size=18, weight=ft.FontWeight.W_800, color=INK), ft.Text(f"{first.get('modelo') or 'Modelo não informado'} · {first.get('cor') or 'Cor não informada'}", size=10, color=MUTED)], expand=True), pill("ATIVO", None, OLIVE_SOFT, INK)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=14) if first else card(ft.Column([ft.Text("Nenhum veículo vinculado.", weight=ft.FontWeight.W_700, color=INK), ft.Text("Cadastre um veículo pelo menu Veículos.", size=10, color=MUTED)], spacing=3), padding=14),
            primary("Registrar saída" if inside else "Entrada pela portaria", out if inside else (lambda e: notify(page, "A entrada começa pela máquina da portaria.")), ft.Icons.LOGOUT if inside else ft.Icons.QR_CODE, 420),
        ], spacing=9)
        shell(page, body, 520, emp_nav("home"))
        state["qr_gen"] += 1
        page.run_task(refresh_qr, qr, token, countdown, cred_status, updated, u["id_usuario"], state["qr_gen"])

    def nav(key):
        routes = {"home": show_home, "access": show_access, "vehicles": show_vehicles, "account": show_account, "notifications": show_notifications}
        routes.get(key, show_home)()

    def show_access():
        state["page"] = "access"; rows = db.historico(state["user"]["id_usuario"], 100)
        items = [topbar("Acessos", "Seu histórico de entradas e saídas", back=lambda e: show_home())]
        if not rows:
            items.append(card(ft.Column([ft.Icon(ft.Icons.HISTORY, size=32, color=MUTED), ft.Text("Nenhum acesso registrado", weight=ft.FontWeight.W_700, color=INK)], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=22))
        for r in rows:
            live = r["status_presenca"] == "DENTRO"
            items.append(card(ft.Row([ft.Container(width=42, height=42, bgcolor=OLIVE_SOFT if live else BROWN_SOFT, border_radius=14, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.LOGIN if live else ft.Icons.LOGOUT, color=OLIVE_DARK if live else BROWN)), ft.Column([ft.Text(r["placa"], size=16, weight=ft.FontWeight.W_800, color=INK), ft.Text(f"{r['data_hora_entrada']} → {r['data_hora_saida'] or 'ainda dentro'}", size=10, color=MUTED), ft.Text(f"{r['metodo_validacao']} · {r['portaria']}", size=9, color=MUTED)], expand=True), pill(r["status_presenca"], None, OLIVE_SOFT if live else BROWN_SOFT, INK)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=11))
        shell(page, ft.Column(items, spacing=8), 650, emp_nav("access"))

    def show_vehicles():
        state["page"] = "vehicles"; uid = state["user"]["id_usuario"]
        search = text_field("Pesquisar placa ou modelo", icon=ft.Icons.SEARCH)
        box = ft.Column(spacing=7)

        def refresh(e=None):
            box.controls.clear()
            rows = db.listar_veiculos(uid, search.value or "", incluir_inativos=True)
            if not rows:
                box.controls.append(empty_state(ft.Icons.DIRECTIONS_CAR_OUTLINED, "Nenhum veículo encontrado", "Cadastre um veículo para vincular à sua conta."))
            for v in rows:
                bg = OLIVE_SOFT if v["ativo"] else BROWN_SOFT
                box.controls.append(card(ft.Row([
                    ft.Container(car_image(v.get("modelo"), v.get("cor"), 92), opacity=1 if v["ativo"] else 0.45),
                    ft.Column([ft.Text(v["placa"], size=17, weight=ft.FontWeight.W_800, color=INK), ft.Text(f"{v.get('modelo') or 'Modelo não informado'} · {v.get('cor') or 'Sem cor'}", size=10, color=MUTED)], expand=True),
                    pill("ATIVO" if v["ativo"] else "INATIVO", None, bg, INK),
                    icon_button(ft.Icons.EDIT_OUTLINED, lambda e, v=v: edit_my_vehicle(v), "Editar"),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=11))
            page.update()
        search.on_change = refresh; refresh()
        body = ft.Column([topbar("Veículos", "Gerencie as placas vinculadas à sua conta", back=lambda e: show_home(), action=primary("Novo", lambda e: add_my_vehicle(), ft.Icons.ADD)), search, box], spacing=9)
        shell(page, body, 700, emp_nav("vehicles"))

    def add_my_vehicle():
        placa = text_field("Placa", hint="ABC1D23 ou ABC-1234"); modelo = text_field("Modelo"); cor = text_field("Cor"); err = ft.Text("", size=10, color=RED)
        def save(e):
            p = (placa.value or "").strip().upper().replace("-", "")
            if not sec.validar_placa(p): err.value = "Placa inválida."; page.update(); return
            try:
                vid = db.criar_veiculo(state["user"]["id_usuario"], p, modelo.value or "", cor.value or "")
                db.auditar(state["user"]["id_usuario"], "CREATE", "VEICULO", vid, f"Placa {p}")
                page.close(d); notify(page, "Veículo cadastrado."); show_vehicles()
            except Exception as ex: err.value = f"Não foi possível cadastrar: {ex}"; page.update()
        d = ft.AlertDialog(modal=True, title=ft.Text("Novo veículo", color=INK), content=ft.Column([placa, modelo, cor, err], tight=True), actions=[ft.TextButton("Cancelar", on_click=lambda e: page.close(d)), primary("Cadastrar", save)])
        page.open(d)

    def edit_my_vehicle(v):
        placa = text_field("Placa", value=v["placa"]); modelo = text_field("Modelo", value=v.get("modelo") or ""); cor = text_field("Cor", value=v.get("cor") or ""); err = ft.Text("", size=10, color=RED)
        def save(e):
            p = (placa.value or "").strip().upper().replace("-", "")
            if not sec.validar_placa(p): err.value = "Placa inválida."; page.update(); return
            try:
                db.atualizar_veiculo(v["id_veiculo"], p, modelo.value or "", cor.value or "")
                db.auditar(state["user"]["id_usuario"], "UPDATE", "VEICULO", v["id_veiculo"], f"Placa {p}")
                page.close(d); notify(page, "Veículo atualizado."); show_vehicles()
            except Exception as ex: err.value = str(ex); page.update()
        def disable(e):
            db.definir_veiculo_status(v["id_veiculo"], False); db.auditar(state["user"]["id_usuario"], "INATIVAR", "VEICULO", v["id_veiculo"], v["placa"]); page.close(d); notify(page, "Veículo inativado."); show_vehicles()
        def activate(e):
            db.definir_veiculo_status(v["id_veiculo"], True); db.auditar(state["user"]["id_usuario"], "ATIVAR", "VEICULO", v["id_veiculo"], v["placa"]); page.close(d); notify(page, "Veículo reativado."); show_vehicles()
        toggle = activate if not v["ativo"] else disable
        d = ft.AlertDialog(modal=True, title=ft.Text("Editar veículo", color=INK), content=ft.Column([placa, modelo, cor, err], tight=True), actions=[ft.TextButton("Ativar" if not v["ativo"] else "Inativar", on_click=toggle), ft.TextButton("Cancelar", on_click=lambda e: page.close(d)), primary("Salvar", save)])
        page.open(d)

    def show_account():
        refresh_user(); state["page"] = "account"; u = state["user"]
        face_ok = bool(u.get("foto_facial_path") and Path(u["foto_facial_path"]).exists())
        face_status = ft.Text("Reconhecimento facial cadastrado" if face_ok else "Reconhecimento facial não cadastrado", color=GREEN if face_ok else RED, size=11)
        name = text_field("Nome completo", value=u["nome_completo"]); username = text_field("Username", value=u["username"]); email = text_field("E-mail", value=u["email"])
        msg = ft.Text("", size=10, color=RED)

        def save_profile(e):
            if len((name.value or "").strip()) < 3 or not sec.RE_USER.fullmatch((username.value or "").strip()) or not sec.RE_EMAIL.fullmatch((email.value or "").strip().lower()):
                msg.value = "Revise nome, username e e-mail."; page.update(); return
            try:
                db.atualizar_usuario(u["id_usuario"], name.value, username.value, email.value, "FUNCIONARIO", u["status_conta"])
                db.auditar(u["id_usuario"], "UPDATE", "USUARIO", u["id_usuario"], "Perfil atualizado pelo funcionário")
                refresh_user(); notify(page, "Perfil atualizado."); show_account()
            except Exception as ex: msg.value = str(ex); page.update()

        def change_password(e):
            old = text_field("Senha atual", password=True); new = text_field("Nova senha", password=True); conf = text_field("Confirmar nova senha", password=True); err = ft.Text("", size=10, color=RED)
            def save(e2):
                check, er = db.autenticar(u["username"], old.value or "")
                if er or not check: err.value = "Senha atual incorreta."; page.update(); return
                if not sec.RE_SENHA.fullmatch(new.value or "") or new.value != conf.value: err.value = "A nova senha não atende à política ou não confere."; page.update(); return
                db.atualizar_senha(u["id_usuario"], new.value); db.auditar(u["id_usuario"], "UPDATE", "USUARIO", u["id_usuario"], "Senha alterada pelo funcionário"); page.close(d); notify(page, "Senha alterada.")
            d = ft.AlertDialog(modal=True, title=ft.Text("Alterar senha", color=INK), content=ft.Column([old, new, conf, err], tight=True), actions=[ft.TextButton("Cancelar", on_click=lambda e2: page.close(d)), primary("Salvar", save)])
            page.open(d)

        async def recapture(e):
            b.disabled = True; page.update()
            try:
                path = BASE / "data" / "faces" / f"recapture_{u['id_usuario']}_{int(time.time()*1000)}.jpg"
                got = await asyncio.to_thread(sec.capturar_frame, path, int(db.get_config("camera_index", "0")), "KEEPER - Recadastro facial", True)
                if not got or not sec.foto_tem_rosto(got):
                    notify(page, "Não foi possível cadastrar um rosto válido.", False); return
                final = BASE / "data" / "faces" / f"usuario_{u['id_usuario']}.jpg"
                if final.exists(): final.unlink(missing_ok=True)
                shutil.move(got, final)
                db.atualizar_foto_facial(u["id_usuario"], str(final)); db.auditar(u["id_usuario"], "UPDATE", "BIOMETRIA", u["id_usuario"], "Rosto recadastrado pelo funcionário"); notify(page, "Rosto recadastrado com sucesso."); show_account()
            except Exception as ex: notify(page, str(ex), False)
            finally: b.disabled = False; page.update()

        b = secondary("Cadastrar / recadastrar rosto pela câmera", lambda e: page.run_task(recapture, e), ft.Icons.FACE, 420)
        def remove_face(e):
            old = u.get("foto_facial_path")
            if old and Path(old).exists():
                try: Path(old).unlink()
                except Exception: pass
            db.atualizar_foto_facial(u["id_usuario"], None)
            db.auditar(u["id_usuario"], "DELETE", "BIOMETRIA", u["id_usuario"], "Cadastro facial removido")
            notify(page, "Biometria removida. Será necessário cadastrar novamente para reconhecimento facial.", False)
            show_account()
        remove_face_btn = secondary("Remover biometria", remove_face, ft.Icons.DELETE_OUTLINE, 420) if face_ok else ft.Container(height=0)
        body = ft.Column([
            topbar("Minha conta", "Perfil e segurança", back=lambda e: show_home()),
            card(ft.Row([avatar(u["nome_completo"], 58), ft.Column([ft.Text(u["nome_completo"], size=18, weight=ft.FontWeight.W_800, color=INK), ft.Text(u["email"], size=10, color=MUTED), pill("FUNCIONÁRIO", ft.Icons.PERSON, BEIGE, INK)], expand=True)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=14),
            ft.Text("Dados pessoais", size=14, weight=ft.FontWeight.W_800, color=INK), name, username, email, primary("Salvar perfil", save_profile, ft.Icons.SAVE, 420), msg,
            ft.Text("Segurança biométrica", size=14, weight=ft.FontWeight.W_800, color=INK), face_status, b,
            secondary("Alterar senha", change_password, ft.Icons.LOCK_RESET, 420),
            secondary("Sair da conta", lambda e: go_login(), ft.Icons.LOGOUT, 420),
        ], spacing=9)
        shell(page, body, 540, emp_nav("account"))

    def show_notifications():
        state["page"] = "notifications"; uid = state["user"]["id_usuario"]; rows = db.notificacoes(uid, 50)
        def read_all(e): db.marcar_todas_notificacoes_lidas(uid); show_notifications()
        items = [topbar("Notificações", "Confirmações e alertas do KEEPER", back=lambda e: show_home(), action=ft.TextButton("Marcar lidas", on_click=read_all))]
        if not rows:
            items.append(card(ft.Column([ft.Icon(ft.Icons.NOTIFICATIONS_NONE, size=32, color=MUTED), ft.Text("Tudo em dia", weight=ft.FontWeight.W_700, color=INK), ft.Text("Nenhuma notificação encontrada.", size=10, color=MUTED)], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=22))
        for n in rows:
            bg = OLIVE_SOFT if not n["lida"] else SURFACE
            items.append(card(ft.Row([ft.Container(width=40, height=40, bgcolor=OLIVE_SOFT if not n["lida"] else BEIGE, border_radius=13, alignment=ft.alignment.center, content=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE if not n["lida"] else ft.Icons.NOTIFICATIONS_NONE, color=OLIVE_DARK)), ft.Column([ft.Text(n["titulo"], weight=ft.FontWeight.W_700, color=INK), ft.Text(n["mensagem"], size=10, color=MUTED), ft.Text(n["criado_em"], size=9, color=MUTED)], expand=True), ft.TextButton("Lida", on_click=lambda e, nid=n["id_notificacao"]: (db.marcar_notificacao_lida(nid), show_notifications())) if not n["lida"] else ft.Container(width=35)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=11, bgcolor=bg))
        shell(page, ft.Column(items, spacing=8), 680, emp_nav("notifications"))

    go_login()


if __name__ == "__main__":
    ft.app(target=main, assets_dir=str(__import__("pathlib").Path(__file__).resolve().parent / "assets"))
