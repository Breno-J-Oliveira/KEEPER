from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
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
    init_page(page, "KEEPER — Administração")
    state = {"user": None, "page": "dashboard"}

    def login():
        userf = text_field("Usuário ou e-mail", icon=ft.Icons.PERSON_OUTLINE)
        passf = text_field("Senha", password=True, icon=ft.Icons.LOCK_OUTLINE)
        err = ft.Text("", size=11, color=RED, text_align=ft.TextAlign.CENTER)
        entrar_btn, guardar_entrar = busy_primary("Entrar", "Verificando…", ft.Icons.LOGIN, 420)

        def enter(e):
            userf.error_text = None
            passf.error_text = None
            if not (userf.value or "").strip():
                userf.error_text = "Informe o usuário."
            if not passf.value:
                passf.error_text = "Informe a senha."
            if userf.error_text or passf.error_text:
                page.update(); return
            u, er = db.autenticar((userf.value or "").strip(), passf.value or "")
            if er or not u or u["tipo_acesso"] != "ADM":
                err.value = er or "Esta conta não é administradora."; page.update(); return
            state["user"] = u
            db.auditar(u["id_usuario"], "LOGIN", "ADM", u["id_usuario"], "Login no painel administrativo")
            show_dashboard()

        entrar_btn.on_click = guardar_entrar(enter)
        passf.on_submit = guardar_entrar(enter)
        shell(page, ft.Column([
            ft.Container(height=24), logo(small=True), ft.Container(height=10),
            ft.Text("Painel administrativo", size=27, weight=ft.FontWeight.W_800, color=INK),
            ft.Text("Gestão completa do ecossistema KEEPER.", size=12, color=MUTED, text_align=ft.TextAlign.CENTER),
            ft.Container(height=8), userf, passf, entrar_btn, err,
            ft.Text("Demo: admin / Admin@123", size=10, color=MUTED),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=9), 520)

    def nav(key):
        routes = {"dashboard": show_dashboard, "users": show_users, "vehicles": show_vehicles, "logs": show_logs, "gate": show_gate, "reports": show_reports, "audit": show_audit, "settings": show_settings, "security": show_security}
        routes.get(key, show_dashboard)()

    def bottom(selected):
        items = [
            ("dashboard", ft.Icons.GRID_VIEW_OUTLINED, "Visão"),
            ("users", ft.Icons.PEOPLE_OUTLINE, "Pessoas"),
            ("vehicles", ft.Icons.DIRECTIONS_CAR_OUTLINED, "Veículos"),
            ("logs", ft.Icons.RECEIPT_LONG_OUTLINED, "Acessos"),
            ("gate", ft.Icons.DNS_OUTLINED, "Máquina"),
        ]
        return bottom_nav(items, selected, nav)

    def stats_card(label, value, icon, accent=OLIVE_SOFT):
        return card(ft.Row([
            ft.Container(width=42, height=42, bgcolor=accent, border_radius=14, alignment=ft.alignment.center, content=ft.Icon(icon, color=INK)),
            ft.Column([ft.Text(str(value), size=22, weight=ft.FontWeight.W_800, color=INK), ft.Text(label, size=10, color=MUTED)], spacing=1, expand=True),
        ]), padding=13)

    def qa(text, cb, icon):
        b = secondary(text, cb, icon); b.expand = True   # ações rápidas: sempre a mesma largura
        return b

    def show_dashboard():
        state["page"] = "dashboard"; s = db.dashboard_resumo(); inside = db.presentes()
        first = []
        for p in inside[:12]:
            first.append(card(ft.Row([
                avatar(p["nome_completo"], 40),
                ft.Column([ft.Text(p["nome_completo"], weight=ft.FontWeight.W_700, color=INK), ft.Text(f"{p['placa']} · {p['data_hora_entrada']}", size=10, color=MUTED)], expand=True),
                pill("DENTRO", ft.Icons.CHECK_CIRCLE, OLIVE_SOFT, INK),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=11))
        if not first:
            first = [empty_state(ft.Icons.GROUP_OFF, "Ninguém dentro agora", "Os registros aparecem após a confirmação da entrada.")]

        body = ft.Column([
            ft.Row([ft.Column([ft.Text("KEEPER", size=12, weight=ft.FontWeight.W_800, color=OLIVE_DARK), ft.Text("Visão geral", size=25, weight=ft.FontWeight.W_800, color=INK)], spacing=0, expand=True), icon_button(ft.Icons.LOGOUT, lambda e: logout(), "Sair", RED)]),
            ft.Text(f"Olá, {state['user']['nome_completo'].split()[0]}. Tudo sob controle.", size=11, color=MUTED),
            ft.Row([kpi_card("Usuários", s["usuarios"], ft.Icons.PEOPLE_OUTLINE), kpi_card("Dentro agora", s["dentro"], ft.Icons.LOGIN)], spacing=10),
            ft.Row([kpi_card("Veículos", s["veiculos"], ft.Icons.DIRECTIONS_CAR), kpi_card("Acessos hoje", s["acessos_hoje"], ft.Icons.TODAY)], spacing=10),
            ft.Row([kpi_card("Pendências", s["pendentes"], ft.Icons.VERIFIED_USER_OUTLINED, BROWN_SOFT), kpi_card("Avisos", s["notificacoes"], ft.Icons.NOTIFICATIONS_NONE, BROWN_SOFT)], spacing=10),
            ft.Row([ft.Text("Presentes agora", size=15, weight=ft.FontWeight.W_800, color=INK), ft.Container(expand=True), ft.TextButton("Atualizar", on_click=lambda e: show_dashboard())]),
            *first,
            ft.Text("Ações rápidas", size=14, weight=ft.FontWeight.W_800, color=INK),
            ft.Row([qa("Novo funcionário", lambda e: new_user(), ft.Icons.PERSON_ADD_ALT_1), qa("Novo veículo", lambda e: new_vehicle(), ft.Icons.DIRECTIONS_CAR)], spacing=8),
            ft.Row([qa("Acesso manual", lambda e: manual_access(), ft.Icons.SWAP_VERT), qa("Abrir máquina", lambda e: open_machine(), ft.Icons.DNS)], spacing=8),
            ft.Row([qa("Relatórios", lambda e: show_reports(), ft.Icons.INSERT_CHART_OUTLINED), qa("Auditoria", lambda e: show_audit(), ft.Icons.HISTORY)], spacing=8),
            ft.Row([qa("Configurações", lambda e: show_settings(), ft.Icons.SETTINGS_OUTLINED)], spacing=8),
        ], spacing=8)
        shell(page, body, 820, bottom("dashboard"))

    def logout():
        if state["user"]:
            db.auditar(state["user"]["id_usuario"], "LOGOUT", "ADM", state["user"]["id_usuario"], "Logout do painel")
        state["user"] = None; login()

    def show_users():
        state["page"] = "users"; search = text_field("Pesquisar nome, username ou e-mail", icon=ft.Icons.SEARCH); include = ft.Switch(label="Mostrar inativos", value=True); box = ft.Column(spacing=7)
        def refresh(e=None):
            box.controls.clear(); rows = db.listar_usuarios(search.value or "", incluir_inativos=include.value)
            if not rows: box.controls.append(card(ft.Text("Nenhum usuário encontrado.", color=MUTED), padding=18))
            for u in rows:
                face_ok = bool(u.get("foto_facial_path") and Path(u["foto_facial_path"]).exists())
                box.controls.append(card(ft.Row([
                    avatar(u["nome_completo"], 42),
                    ft.Column([ft.Text(u["nome_completo"], weight=ft.FontWeight.W_700, color=INK), ft.Text(f"@{u['username']} · {u['email']}", size=9, color=MUTED), ft.Text(f"{u['total_veiculos']} veículo(s) · {u['total_acessos']} acesso(s) · face {'OK' if face_ok else 'PENDENTE'}", size=9, color=GREEN if face_ok else RED)], expand=True),
                    pill(u["tipo_acesso"], ft.Icons.SHIELD_OUTLINED if u["tipo_acesso"] == "ADM" else ft.Icons.PERSON_OUTLINE, BEIGE if u["tipo_acesso"] == "ADM" else OLIVE_SOFT, INK),
                    pill(u["status_conta"], None, OLIVE_SOFT if u["status_conta"] == "ATIVO" else BROWN_SOFT, INK),
                    icon_button(ft.Icons.VISIBILITY_OUTLINED, lambda e, u=u: user_details(u), "Detalhes"),
                    icon_button(ft.Icons.EDIT_OUTLINED, lambda e, u=u: edit_user(u), "Editar"),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=11))
            page.update()
        search.on_change = refresh; include.on_change = refresh; refresh()
        body = ft.Column([topbar("Usuários", "Criar, editar, ativar, inativar e administrar biometria", back=lambda e: show_dashboard(), action=primary("Novo", lambda e: new_user(), ft.Icons.PERSON_ADD_ALT_1)), search, include, box], spacing=8)
        shell(page, body, 840, bottom("users"))

    def validate_user(name, username, email, password=None):
        errors = []
        if len((name or '').strip()) < 3: errors.append("Informe o nome completo (mínimo 3 letras).")
        if not sec.RE_USER.fullmatch((username or '').strip()): errors.append("Username inválido: use 3–30 caracteres (letras, números, ponto ou sublinhado).")
        if not sec.RE_EMAIL.fullmatch((email or '').strip().lower()): errors.append("E-mail inválido: verifique o endereço digitado.")
        if password is not None and not sec.RE_SENHA.fullmatch(password or ''): errors.append("Senha fraca: use 8+ caracteres com maiúscula, minúscula e número.")
        return errors

    def face_capture_button(uid_holder: dict, status: ft.Text, button_holder: dict):
        async def capture(e):
            button_holder["button"].disabled = True; status.value = "Câmera aberta. ENTER/ESPAÇO salva."; status.color = MUTED; page.update()
            try:
                path = BASE / "data" / "faces" / f"admin_capture_{int(time.time()*1000)}.jpg"
                got = await asyncio.to_thread(sec.capturar_frame, path, int(db.get_config("camera_index", "0")), "KEEPER - Cadastro facial", True)
                if got and sec.foto_tem_rosto(got): uid_holder["path"] = got; status.value = "Rosto detectado e pronto."; status.color = GREEN
                else: status.value = "Nenhum rosto válido foi capturado."; status.color = RED
            except Exception as ex: status.value = str(ex); status.color = RED
            finally: button_holder["button"].disabled = False; page.update()
        button_holder["button"] = secondary("Capturar / recadastrar rosto", lambda e: page.run_task(capture, e), ft.Icons.FACE, 420)
        return button_holder["button"]

    def new_user():
        nome=text_field("Nome completo"); username=text_field("Username"); email=text_field("E-mail"); senha=text_field("Senha inicial", password=True); tipo=ft.Dropdown(label="Perfil", options=[ft.dropdown.Option("FUNCIONARIO"),ft.dropdown.Option("ADM")], value="FUNCIONARIO"); face_status=ft.Text("Biometria: não cadastrada",size=10,color=MUTED); err=ft.Text("",size=10,color=RED); holder={"path":None}; btn={}
        face_btn=face_capture_button(holder,face_status,btn)
        def save(e):
            errors=validate_user(nome.value,username.value,email.value,senha.value)
            if errors: err.value="\n".join(errors);page.update();return
            try:
                uid=db.criar_usuario(nome.value,username.value,email.value,senha.value,tipo.value or "FUNCIONARIO")
                if holder["path"]:
                    final=BASE/"data"/"faces"/f"usuario_{uid}.jpg"; final.parent.mkdir(parents=True,exist_ok=True); shutil.move(holder["path"],final); db.atualizar_foto_facial(uid,str(final))
                db.auditar(state["user"]["id_usuario"],"CREATE","USUARIO",uid,f"Conta {username.value}")
                page.close(d);notify(page,"Usuário criado.");show_users()
            except Exception as ex:err.value=str(ex);page.update()
        d=ft.AlertDialog(modal=True,title=ft.Text("Novo usuário",color=INK),content=ft.Column([nome,username,email,senha,tipo,face_btn,face_status,err],tight=True,scroll=ft.ScrollMode.AUTO),actions=[ft.TextButton("Cancelar",on_click=lambda e:page.close(d)),primary("Cadastrar",save)])
        page.open(d)

    def edit_user(u):
        face_ok=bool(u.get("foto_facial_path") and Path(u["foto_facial_path"]).exists())
        nome=text_field("Nome completo",value=u["nome_completo"]); username=text_field("Username",value=u["username"]); email=text_field("E-mail",value=u["email"]); tipo=ft.Dropdown(label="Perfil",options=[ft.dropdown.Option("FUNCIONARIO"),ft.dropdown.Option("ADM")],value=u["tipo_acesso"]); status=ft.Dropdown(label="Status",options=[ft.dropdown.Option("ATIVO"),ft.dropdown.Option("INATIVO")],value=u["status_conta"]); msg=ft.Text("",size=10,color=RED); face_holder={"path":None}; btn={}; face_status=ft.Text("Biometria cadastrada" if face_ok else "Biometria pendente",size=10,color=GREEN if face_ok else RED)
        face_btn=face_capture_button(face_holder,face_status,btn)
        def save(e):
            errors=validate_user(nome.value,username.value,email.value)
            if errors:msg.value="\n".join(errors);page.update();return
            try:
                db.atualizar_usuario(u["id_usuario"],nome.value,username.value,email.value,tipo.value or u["tipo_acesso"],status.value or u["status_conta"])
                if face_holder["path"]:
                    final=BASE/"data"/"faces"/f"usuario_{u['id_usuario']}.jpg";final.parent.mkdir(parents=True,exist_ok=True);shutil.move(face_holder["path"],final);db.atualizar_foto_facial(u["id_usuario"],str(final))
                db.auditar(state["user"]["id_usuario"],"UPDATE","USUARIO",u["id_usuario"],f"Edição da conta {username.value}")
                page.close(d);notify(page,"Usuário atualizado.");show_users()
            except Exception as ex:msg.value=str(ex);page.update()
        def reset_password(e):
            np=text_field("Nova senha",password=True);err=ft.Text("",size=10,color=RED)
            def ok(e2):
                if not sec.RE_SENHA.fullmatch(np.value or ""):err.value="Senha inválida.";page.update();return
                db.atualizar_senha(u["id_usuario"],np.value);db.auditar(state["user"]["id_usuario"],"UPDATE","USUARIO",u["id_usuario"],"Senha redefinida pelo ADM");page.close(dp);notify(page,"Senha redefinida.")
            dp=ft.AlertDialog(modal=True,title=ft.Text("Redefinir senha",color=INK),content=ft.Column([np,err],tight=True),actions=[ft.TextButton("Cancelar",on_click=lambda e2:page.close(dp)),primary("Redefinir",ok)])
            page.open(dp)
        def remove(e):
            if u["id_usuario"]==state["user"]["id_usuario"]:msg.value="Você não pode excluir a própria conta.";page.update();return
            try:db.excluir_usuario(u["id_usuario"]);db.auditar(state["user"]["id_usuario"],"DELETE","USUARIO",u["id_usuario"],u["username"]);page.close(d);notify(page,"Usuário excluído.");show_users()
            except Exception as ex:msg.value=str(ex);page.update()
        def remove_face(e):
            old=u.get("foto_facial_path")
            if old and Path(old).exists():
                try:Path(old).unlink()
                except Exception:pass
            db.atualizar_foto_facial(u["id_usuario"],None);db.auditar(state["user"]["id_usuario"],"DELETE","BIOMETRIA",u["id_usuario"],"Biometria removida pelo ADM");face_status.value="Biometria pendente";face_status.color=RED;page.update();notify(page,"Biometria removida.",False)
        actions=[ft.TextButton("Excluir",on_click=remove),ft.TextButton("Remover biometria",on_click=remove_face) if face_ok else ft.Container(width=0),ft.TextButton("Redefinir senha",on_click=reset_password),ft.TextButton("Cancelar",on_click=lambda e:page.close(d)),primary("Salvar",save)]
        d=ft.AlertDialog(modal=True,title=ft.Text("Editar usuário",color=INK),content=ft.Column([avatar(u["nome_completo"],52),nome,username,email,tipo,status,face_btn,face_status,msg],tight=True,scroll=ft.ScrollMode.AUTO),actions=actions)
        page.open(d)

    def user_details(u):
        fresh=db.usuario_por_id(u["id_usuario"]) or u; cars=db.listar_veiculos(fresh["id_usuario"],incluir_inativos=True); face_ok=bool(fresh.get("foto_facial_path") and Path(fresh["foto_facial_path"]).exists())
        face_status=ft.Text("Face cadastrada" if face_ok else "Face pendente",color=GREEN if face_ok else RED,size=11)
        items=[topbar("Detalhes",f"Usuário #{fresh['id_usuario']}",back=lambda e:show_users()),card(ft.Column([ft.Row([avatar(fresh["nome_completo"],60),ft.Column([ft.Text(fresh["nome_completo"],size=19,weight=ft.FontWeight.W_800,color=INK),ft.Text(f"@{fresh['username']} · {fresh['email']}",size=10,color=MUTED),pill(fresh["tipo_acesso"],ft.Icons.SHIELD_OUTLINED if fresh["tipo_acesso"]=="ADM" else ft.Icons.PERSON,BEIGE,INK)],expand=True)],vertical_alignment=ft.CrossAxisAlignment.CENTER),ft.Divider(color=LINE),ft.Text(f"Criado em: {fresh['criado_em']}",size=10,color=MUTED),ft.Text(f"Status: {fresh['status_conta']}",size=10,color=MUTED),ft.Text(f"Veículos ativos: {fresh.get('total_veiculos',0)}",size=10,color=MUTED),face_status],spacing=8),padding=15)]
        items.append(ft.Row([primary("Editar usuário",lambda e:edit_user(fresh),ft.Icons.EDIT,210),secondary("Novo veículo",lambda e:new_vehicle(prefill_uid=fresh["id_usuario"]),ft.Icons.ADD,210)],alignment=ft.MainAxisAlignment.CENTER))
        items.append(ft.Text("Veículos vinculados",size=15,weight=ft.FontWeight.W_800,color=INK))
        for v in cars:
            items.append(card(ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR,size=28,color=BROWN),ft.Column([ft.Text(v["placa"],size=17,weight=ft.FontWeight.W_800,color=INK),ft.Text(f"{v.get('modelo') or 'Modelo'} · {v.get('cor') or 'Sem cor'}",size=10,color=MUTED)],expand=True),pill("ATIVO" if v["ativo"] else "INATIVO",None,OLIVE_SOFT if v["ativo"] else BROWN_SOFT,INK),icon_button(ft.Icons.EDIT_OUTLINED,lambda e,v=v:edit_vehicle(v),"Editar")],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=11))
        if not cars:items.append(card(ft.Text("Nenhum veículo vinculado.",color=MUTED),padding=15))
        shell(page,ft.Column(items,spacing=8),780,bottom("users"))

    def show_vehicles():
        state["page"]="vehicles";search=text_field("Pesquisar placa, modelo ou funcionário",icon=ft.Icons.SEARCH);include=ft.Switch(label="Mostrar inativos",value=True);box=ft.Column(spacing=7)
        def refresh(e=None):
            box.controls.clear();rows=db.listar_veiculos(None,search.value or "",incluir_inativos=include.value)
            if not rows:box.controls.append(card(ft.Text("Nenhum veículo encontrado.",color=MUTED),padding=18))
            for v in rows:
                box.controls.append(card(ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR,size=30,color=BROWN if v["ativo"] else MUTED),ft.Column([ft.Text(v["placa"],size=18,weight=ft.FontWeight.W_800,color=INK),ft.Text(f"{v.get('modelo') or 'Modelo'} · {v.get('cor') or 'Sem cor'}",size=10,color=MUTED),ft.Text(v["nome_completo"],size=10,color=TEXT)],expand=True),pill("ATIVO" if v["ativo"] else "INATIVO",None,OLIVE_SOFT if v["ativo"] else BROWN_SOFT,INK),icon_button(ft.Icons.EDIT_OUTLINED,lambda e,v=v:edit_vehicle(v),"Editar")],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=11))
            page.update()
        search.on_change=refresh;include.on_change=refresh;refresh()
        shell(page,ft.Column([topbar("Veículos","Cadastro, vínculo, transferência e status",back=lambda e:show_dashboard(),action=primary("Novo",lambda e:new_vehicle(),ft.Icons.ADD)),search,include,box],spacing=8),820,bottom("vehicles"))

    def new_vehicle(prefill_uid=None):
        users=[u for u in db.listar_usuarios("",False) if u["status_conta"]=="ATIVO"]
        dono=ft.Dropdown(label="Funcionário",options=[ft.dropdown.Option(str(u["id_usuario"]),u["nome_completo"]) for u in users],value=str(prefill_uid) if prefill_uid else None);placa=text_field("Placa",hint="ABC1D23 ou ABC-1234");modelo=text_field("Modelo");cor=text_field("Cor");err=ft.Text("",size=10,color=RED)
        def save(e):
            p=(placa.value or '').strip().upper().replace('-','')
            if not dono.value or not sec.validar_placa(p):err.value="Selecione o funcionário e informe uma placa válida.";page.update();return
            try:
                vid=db.criar_veiculo(int(dono.value),p,modelo.value or '',cor.value or '');db.auditar(state['user']['id_usuario'],'CREATE','VEICULO',vid,f'Placa {p}');page.close(d);notify(page,'Veículo cadastrado.');show_vehicles()
            except Exception as ex:err.value=str(ex);page.update()
        d=ft.AlertDialog(modal=True,title=ft.Text('Novo veículo',color=INK),content=ft.Column([dono,placa,modelo,cor,err],tight=True),actions=[ft.TextButton('Cancelar',on_click=lambda e:page.close(d)),primary('Cadastrar',save)])
        page.open(d)

    def edit_vehicle(v):
        users=[u for u in db.listar_usuarios('',False) if u['status_conta']=='ATIVO'];dono=ft.Dropdown(label='Funcionário',options=[ft.dropdown.Option(str(u['id_usuario']),u['nome_completo']) for u in users],value=str(v['id_usuario']));placa=text_field('Placa',value=v['placa']);modelo=text_field('Modelo',value=v.get('modelo') or '');cor=text_field('Cor',value=v.get('cor') or '');err=ft.Text('',size=10,color=RED)
        def save(e):
            p=(placa.value or '').strip().upper().replace('-','')
            if not dono.value or not sec.validar_placa(p):err.value='Dados inválidos.';page.update();return
            try:db.atualizar_veiculo(v['id_veiculo'],p,modelo.value or '',cor.value or '',int(dono.value));db.auditar(state['user']['id_usuario'],'UPDATE','VEICULO',v['id_veiculo'],f'Placa {p} / dono {dono.value}');page.close(d);notify(page,'Veículo atualizado.');show_vehicles()
            except Exception as ex:err.value=str(ex);page.update()
        def toggle(e):db.definir_veiculo_status(v['id_veiculo'],not bool(v['ativo']));db.auditar(state['user']['id_usuario'],'ATIVAR' if not v['ativo'] else 'INATIVAR','VEICULO',v['id_veiculo'],v['placa']);page.close(d);notify(page,'Status do veículo atualizado.');show_vehicles()
        def remove(e):
            try:db.excluir_veiculo(v['id_veiculo']);db.auditar(state['user']['id_usuario'],'DELETE','VEICULO',v['id_veiculo'],v['placa']);page.close(d);notify(page,'Veículo excluído.');show_vehicles()
            except Exception as ex:err.value=str(ex);page.update()
        d=ft.AlertDialog(modal=True,title=ft.Text('Editar veículo',color=INK),content=ft.Column([dono,placa,modelo,cor,err],tight=True),actions=[ft.TextButton('Excluir',on_click=remove),ft.TextButton('Ativar' if not v['ativo'] else 'Inativar',on_click=toggle),ft.TextButton('Cancelar',on_click=lambda e:page.close(d)),primary('Salvar',save)])
        page.open(d)

    def show_logs():
        state['page'] = 'logs'; search = text_field('Filtrar nome, placa, portaria ou modelo', icon=ft.Icons.SEARCH); status = ft.Dropdown(label='Status', options=[ft.dropdown.Option('TODOS'), ft.dropdown.Option('DENTRO'), ft.dropdown.Option('FORA')], value='TODOS'); box = ft.Column(spacing=7)

        def refresh(e=None):
            box.controls.clear(); rows = db.historico(None, 500, search.value or '', status.value)
            if not rows:
                box.controls.append(empty_state(ft.Icons.RECEIPT_LONG_OUTLINED, "Nenhum acesso encontrado", "Ajuste o filtro ou aguarde novos registros."))
            for r in rows:
                live=r['status_presenca']=='DENTRO';box.controls.append(card(ft.Row([ft.Container(width=40,height=40,bgcolor=OLIVE_SOFT if live else BROWN_SOFT,border_radius=13,alignment=ft.alignment.center,content=ft.Icon(ft.Icons.LOGIN if live else ft.Icons.LOGOUT,color=OLIVE_DARK if live else BROWN)),ft.Column([ft.Text(r['nome_completo'],weight=ft.FontWeight.W_700,color=INK),ft.Text(f"{r['placa']} · {r['data_hora_entrada']} → {r['data_hora_saida'] or 'agora'}",size=10,color=MUTED),ft.Text(f"{r['metodo_validacao']} · {r['portaria']}{' · '+r['observacao'] if r.get('observacao') else ''}",size=9,color=MUTED)],expand=True),pill(r['status_presenca'],None,OLIVE_SOFT if live else BROWN_SOFT,INK)],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=11))
            page.update()
        search.on_change=refresh;status.on_change=refresh;refresh()
        shell(page,ft.Column([topbar('Acessos','Histórico completo',back=lambda e:show_dashboard(),action=primary('Exportar CSV',lambda e:export_csv(),ft.Icons.DOWNLOAD)),search,status,box],spacing=8),840,bottom('logs'))

    def manual_access():
        users=[u for u in db.listar_usuarios('',False) if u['status_conta']=='ATIVO'];user=ft.Dropdown(label='Funcionário',options=[ft.dropdown.Option(str(u['id_usuario']),u['nome_completo']) for u in users]);vehicle=ft.Dropdown(label='Veículo');direction=ft.Dropdown(label='Sentido',options=[ft.dropdown.Option('ENTRADA'),ft.dropdown.Option('SAIDA')],value='ENTRADA');obs=text_field('Observação');err=ft.Text('',size=10,color=RED)
        def load_vehicles(e=None):
            vehicle.options=[]
            if user.value:
                vs=db.listar_veiculos(int(user.value))
                vehicle.options=[ft.dropdown.Option(str(v['id_veiculo']),f"{v['placa']} · {v.get('modelo') or ''}") for v in vs]
            vehicle.value=None;page.update()
        user.on_change=load_vehicles;load_vehicles()
        def save(e):
            if not user.value or not vehicle.value:err.value='Selecione funcionário e veículo.';page.update();return
            try:
                uid=int(user.value);vid=int(vehicle.value);ok=db.registrar_entrada(uid,vid,'ADM_MANUAL',db.get_config('portaria_nome','PORTARIA 01'),obs.value or '') if direction.value=='ENTRADA' else db.registrar_saida(uid,vid,'ADM_MANUAL',db.get_config('portaria_nome','PORTARIA 01'),obs.value or '')
                if not ok:raise ValueError('A operação é incompatível com o estado atual de presença.')
                db.auditar(state['user']['id_usuario'],'CREATE','ACESSO',None,f'Operação manual {direction.value} para usuário {uid}');page.close(d);notify(page,'Acesso registrado.');show_dashboard()
            except Exception as ex:err.value=str(ex);page.update()
        d=ft.AlertDialog(modal=True,title=ft.Text('Registrar acesso manual',color=INK),content=ft.Column([user,vehicle,direction,obs,err],tight=True),actions=[ft.TextButton('Cancelar',on_click=lambda e:page.close(d)),primary('Registrar',save)])
        page.open(d)

    def show_gate():
        state['page']='gate';search=text_field('Filtrar solicitações',icon=ft.Icons.SEARCH);status=ft.Dropdown(label='Status',options=[ft.dropdown.Option(x) for x in ['TODOS','AGUARDANDO','CONFIRMADA','RECUSADA','FINALIZADA','EXPIRADA','CANCELADA']],value='TODOS');box=ft.Column(spacing=7)
        def refresh(e=None):
            box.controls.clear();rows=db.listar_solicitacoes(300,search.value or '',status.value)
            if not rows:box.controls.append(card(ft.Text('Nenhuma solicitação encontrada.',color=MUTED),padding=18))
            for r in rows:
                aguardando=r['status']=='AGUARDANDO';bg=OLIVE_SOFT if aguardando else (BROWN_SOFT if r['status'] in ('RECUSADA','EXPIRADA','CANCELADA') else BEIGE)
                actions=[]
                if aguardando:actions.append(icon_button(ft.Icons.CANCEL_OUTLINED,lambda e,sid=r['id_solicitacao']:cancel_request(sid),'Cancelar',RED))
                box.controls.append(card(ft.Row([avatar(r['nome_completo'],40),ft.Column([ft.Text(r['nome_completo'],weight=ft.FontWeight.W_700,color=INK),ft.Text(f"{r['placa']} · {r['sentido']} · score {r['score_facial'] if r['score_facial'] is not None else '-'}",size=10,color=MUTED),ft.Text(f"{r['portaria']} · {r['criado_em']}",size=9,color=MUTED)],expand=True),pill(r['status'],None,bg,INK),*actions],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=11))
            page.update()
        search.on_change=refresh;status.on_change=refresh;refresh()
        shell(page,ft.Column([topbar('Máquina / solicitações','Acompanhe a comunicação entre portaria e funcionário',back=lambda e:show_dashboard(),action=primary('Abrir máquina',lambda e:open_machine(),ft.Icons.OPEN_IN_NEW)),search,status,box],spacing=8),850,bottom('gate'))

    def cancel_request(sid):
        if db.cancelar_solicitacao(sid):db.auditar(state['user']['id_usuario'],'CANCELAR','SOLICITACAO',sid,'Cancelada pelo ADM');notify(page,'Solicitação cancelada.');show_gate()

    def show_reports():
        state['page']='reports';s=db.dashboard_resumo();days=db.estatisticas_diarias(7);rows=db.historico(None,1000);plate_count={}
        for r in rows:plate_count[r['placa']]=plate_count.get(r['placa'],0)+1
        top=sorted(plate_count.items(),key=lambda x:x[1],reverse=True)[:5]
        items=[topbar('Relatórios','Indicadores e exportações',back=lambda e:show_dashboard()),ft.Row([stats_card('Entradas',sum(1 for r in rows if r['status_presenca']=='DENTRO'),ft.Icons.LOGIN),stats_card('Saídas',sum(1 for r in rows if r['status_presenca']=='FORA'),ft.Icons.LOGOUT),stats_card('Usuários ativos',s['usuarios'],ft.Icons.PEOPLE)],spacing=7),stats_card('Presença atual',f"{(s['dentro']/max(1,s['funcionarios']))*100:.0f}%",ft.Icons.PIE_CHART_OUTLINE,KHAKI),ft.Text('Últimos 7 dias',size=15,weight=ft.FontWeight.W_800,color=INK)]
        for d in days:items.append(card(ft.Row([ft.Text(d['dia'],weight=ft.FontWeight.W_700,color=INK),ft.Container(expand=True),ft.Text(f"{d['entradas']} entradas",size=10,color=MUTED),ft.Text(f"{d['saidas']} saídas",size=10,color=MUTED)],spacing=12),padding=11))
        items += [ft.Text('Veículos mais utilizados',size=15,weight=ft.FontWeight.W_800,color=INK)]
        for p,n in top:items.append(card(ft.Row([ft.Icon(ft.Icons.DIRECTIONS_CAR,color=BROWN),ft.Text(p,weight=ft.FontWeight.W_700,color=INK),ft.Container(expand=True),ft.Text(str(n),color=MUTED)],spacing=7),padding=11))
        chart = ft.BarChart(bar_groups=[ft.BarChartGroup(x=i, bar_rods=[ft.BarChartRod(from_y=0, to_y=d['entradas'], width=13, color=OLIVE, border_radius=4), ft.BarChartRod(from_y=0, to_y=d['saidas'], width=13, color=KHAKI, border_radius=4)]) for i, d in enumerate(days)],
            bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=i, label=ft.Text(d['dia'][5:], size=9, color=MUTED)) for i, d in enumerate(days)], labels_size=26),
            left_axis=ft.ChartAxis(labels_size=24), horizontal_grid_lines=ft.ChartGridLines(color=LINE, width=1), height=190, interactive=True, max_y=max([3] + [max(d['entradas'], d['saidas']) + 1 for d in days]))
        items.insert(5, card(ft.Column([ft.Text('Gráfico de acessos (verde = entradas, areia = saídas)', size=10, color=MUTED), chart]), padding=12))
        items += [primary('Exportar relatório PDF', lambda e: export_pdf(), ft.Icons.PICTURE_AS_PDF, 420), secondary('Segurança, visitantes e senhas', lambda e: show_security(), ft.Icons.SHIELD_OUTLINED, 420)]
        items += [primary('Exportar acessos CSV',lambda e:export_csv(),ft.Icons.DOWNLOAD,420),secondary('Exportar auditoria CSV',lambda e:export_audit(),ft.Icons.SECURITY,420)]
        shell(page,ft.Column(items,spacing=8),820,bottom('dashboard'))

    def export_pdf():
        out = BASE / 'exports'; out.mkdir(exist_ok=True)
        try:
            path = extras.relatorio_pdf(str(out / 'relatorio_keeper.pdf')); notify(page, f'PDF salvo em {path}')
            try: os.startfile(path)
            except Exception: pass
        except Exception as ex: notify(page, f'Não foi possível gerar o PDF: {ex}', False)

    def show_security():
        state['page'] = 'security'
        pl, motivo = text_field('Placa a bloquear', icon=ft.Icons.BLOCK), text_field('Motivo')
        vn, vd, vp = text_field('Nome do visitante', icon=ft.Icons.PERSON_ADD_ALT_1), text_field('Documento (opcional)'), text_field('Placa do visitante (opcional)')
        vh = text_field('Validade em horas', value='4')
        code_box = ft.Text('', size=20, weight=ft.FontWeight.W_800, color=OLIVE_DARK, selectable=True)
        def run(fn, ok_msg):
            try: fn(); notify(page, ok_msg)
            except Exception as ex: notify(page, str(ex), False); return
            show_security()
        def novo_visitante(e):
            try: c = extras.criar_visitante(vn.value or '', vd.value or '', vp.value or '', int(vh.value or 4))
            except Exception as ex: notify(page, str(ex), False); return
            notify(page, f'Código do visitante: {c}'); show_security()
        def gerar(rid):
            code_box.value = 'Código: ' + extras.gerar_codigo_reset(rid) + ' (válido 15 min — informe ao usuário)'; page.update()
        items = [topbar('Segurança', 'Bloqueios, visitantes e senhas', back=lambda e: show_reports()),
                 ft.Text('Placas bloqueadas', size=15, weight=ft.FontWeight.W_800, color=INK), pl, motivo,
                 primary('Bloquear placa', lambda e: run(lambda: extras.bloquear_placa(pl.value or '', motivo.value or ''), 'Placa bloqueada.'), ft.Icons.BLOCK, 420)]
        for b in extras.listar_bloqueadas():
            items.append(card(ft.Row([ft.Icon(ft.Icons.BLOCK, color=RED), ft.Column([ft.Text(b['placa'], weight=ft.FontWeight.W_800, color=INK), ft.Text(b['motivo'] or '—', size=10, color=MUTED)], expand=True),
                           icon_button(ft.Icons.DELETE_OUTLINE, lambda e, p=b['placa']: run(lambda: extras.desbloquear_placa(p), 'Placa desbloqueada.'), 'Desbloquear')]), padding=10))
        items += [ft.Divider(), ft.Text('Visitantes', size=15, weight=ft.FontWeight.W_800, color=INK), vn, vd, vp, vh, primary('Gerar código de visitante', novo_visitante, ft.Icons.QR_CODE_2, 420)]
        for v in extras.listar_visitantes():
            items.append(card(ft.Row([ft.Column([ft.Text(f"{v['nome']} · {v['codigo']}", weight=ft.FontWeight.W_800, color=INK), ft.Text(f"{v['placa'] or 'sem placa'} · até {v['validade']}", size=10, color=MUTED)], expand=True),
                           pill(v['status'], None, OLIVE_SOFT if v['status'] == 'VÁLIDO' else BROWN_SOFT, INK)]), padding=10))
        items += [ft.Divider(), ft.Text('Pedidos de redefinição de senha', size=15, weight=ft.FontWeight.W_800, color=INK), code_box]
        pend = extras.reset_pendentes()
        if not pend: items.append(ft.Text('Nenhum pedido pendente.', size=11, color=MUTED))
        for r in pend:
            items.append(card(ft.Row([ft.Column([ft.Text(f"{r['nome_completo']} ({r['username']})", weight=ft.FontWeight.W_700, color=INK), ft.Text(f"Pedido em {r['criado_em']}", size=10, color=MUTED)], expand=True),
                           secondary('Gerar código', lambda e, i=r['id']: gerar(i), ft.Icons.KEY)]), padding=10))
        shell(page, ft.Column(items, spacing=8), 820, bottom('dashboard'))

    def export_csv():
        out=BASE/'exports';out.mkdir(exist_ok=True);path=out/'acessos_keeper.csv';path.write_text(db.exportar_csv(),encoding='utf-8-sig');notify(page,f'CSV salvo em {path}')
        try:os.startfile(out)
        except Exception:pass

    def export_audit():
        out=BASE/'exports';out.mkdir(exist_ok=True);path=out/'auditoria_keeper.csv';path.write_text(db.exportar_auditoria_csv(),encoding='utf-8-sig');notify(page,f'Auditoria salva em {path}')
        try:os.startfile(out)
        except Exception:pass

    def show_audit():
        state['page'] = 'audit'; search = text_field('Filtrar ação, entidade ou detalhe', icon=ft.Icons.SEARCH); box = ft.Column(spacing=7)

        def refresh(e=None):
            box.controls.clear()
            rows = db.auditoria(400, search.value or '')
            if not rows:
                box.controls.append(empty_state(ft.Icons.HISTORY, "Nenhum evento de auditoria", "As operações do sistema aparecem aqui."))
            for a in rows:
                box.controls.append(card(ft.Row([ft.Container(width=38,height=38,bgcolor=BEIGE,border_radius=12,alignment=ft.alignment.center,content=ft.Icon(ft.Icons.HISTORY,color=BROWN)),ft.Column([ft.Text(f"{a.get('nome_completo') or 'Sistema'} · {a['acao']}",weight=ft.FontWeight.W_700,color=INK),ft.Text(f"{a['entidade']} #{a.get('entidade_id') or '-'} · {a.get('detalhe') or ''}",size=10,color=MUTED),ft.Text(a['criado_em'],size=9,color=MUTED)],expand=True)],vertical_alignment=ft.CrossAxisAlignment.CENTER),padding=11))
            page.update()
        search.on_change=refresh;refresh()
        shell(page,ft.Column([topbar('Auditoria','Rastreabilidade das operações',back=lambda e:show_dashboard(),action=secondary('CSV',lambda e:export_audit(),ft.Icons.DOWNLOAD)),search,box],spacing=8),820,bottom('dashboard'))

    def show_settings():
        state['page']='settings';ci=text_field('Índice da câmera',value=db.get_config('camera_index','0'));threshold=text_field('Threshold facial',value=db.get_config('face_threshold','0.45'));port=text_field('Nome da portaria',value=db.get_config('portaria_nome','PORTARIA 01'));expire=text_field('Expiração de solicitação (s)',value=db.get_config('auto_expire_seconds','45'));ocr=text_field('Tempo máximo OCR (s)',value=db.get_config('ocr_timeout','25'));empresa=text_field('Nome da empresa',value=db.get_config('empresa_nome','KEEPER'));msg=ft.Text('',size=10,color=GREEN)
        def save(e):
            try:float(threshold.value or '0.363');int(ci.value or '0');int(expire.value or '45');int(ocr.value or '25')
            except ValueError:msg.value='Valores numéricos inválidos.';msg.color=RED;page.update();return
            for k,v in {'camera_index':ci.value,'face_threshold':threshold.value,'portaria_nome':port.value,'auto_expire_seconds':expire.value,'ocr_timeout':ocr.value,'empresa_nome':empresa.value}.items():db.set_config(k,v or '')
            db.auditar(state['user']['id_usuario'],'UPDATE','CONFIGURACAO',None,'Configurações alteradas');msg.value='Configurações salvas.';msg.color=GREEN;page.update()
        def backup(e):
            dest=BASE/'exports';dest.mkdir(exist_ok=True);name=dest/f"keeper_backup_{int(time.time())}.db";shutil.copy2(db.DB,name);notify(page,f'Backup criado em {name}')
        async def models(e):
            try:await asyncio.to_thread(sec.ensure_face_models,True);notify(page,'Modelos faciais prontos.')
            except Exception as ex:notify(page,str(ex),False)
        shell(page, ft.Column([topbar('Configurações', 'Hardware, segurança e operação', back=lambda e: show_dashboard()), card(ft.Column([ft.Text('Operação', weight=ft.FontWeight.W_800, color=INK), empresa, port, ci, ocr, expire, ft.Text('Reconhecimento facial', weight=ft.FontWeight.W_800, color=INK), threshold, primary('Salvar configurações', save, ft.Icons.SAVE, 420), msg], spacing=9), padding=15), secondary('Baixar / atualizar modelos faciais', lambda e: page.run_task(models, e), ft.Icons.DOWNLOAD, 420), secondary('Criar backup do banco SQLite', backup, ft.Icons.BACKUP_OUTLINED, 420), secondary('Abrir pasta de dados', lambda e: open_data_folder(), ft.Icons.FOLDER_OPEN, 420)], spacing=9), 760, bottom('dashboard'))

    def open_data_folder():
        try:os.startfile(BASE/'data')
        except Exception as ex:notify(page,str(ex),False)

    def open_machine():
        try:subprocess.Popen([sys.executable,str(BASE/'machine.py')],cwd=str(BASE));notify(page,'Máquina da portaria aberta.')
        except Exception as ex:notify(page,str(ex),False)

    login()


if __name__=='__main__':
    ft.app(target=main, assets_dir=str(__import__("pathlib").Path(__file__).resolve().parent / "assets"))
