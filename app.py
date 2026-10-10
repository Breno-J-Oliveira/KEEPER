from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import flet as ft

import db
from ui import *

BASE=Path(__file__).resolve().parent


def main(page:ft.Page):
    init_page(page,"KEEPER — Central")

    def open_app(filename):
        try:
            subprocess.Popen([sys.executable,str(BASE/filename)],cwd=str(BASE))
            notify(page,f"{filename} aberto.")
        except Exception as ex:notify(page,f"Não foi possível abrir {filename}: {ex}",False)

    s=db.dashboard_resumo()
    body = ft.Column([
        ft.Container(height=22), logo(), ft.Container(height=14),
        ft.Text("Ecossistema KEEPER", size=27, weight=ft.FontWeight.W_800, color=INK, text_align=ft.TextAlign.CENTER),
        ft.Text("Abra cada visão como um aplicativo independente. Todos compartilham o mesmo banco SQLite.", size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
        ft.Container(height=10),
        card(ft.Column([ft.Text("FUNCIONÁRIO", size=11, weight=ft.FontWeight.W_800, color=OLIVE_DARK), ft.Text("Credencial QR, acessos, veículos e confirmação no celular.", size=10, color=MUTED), primary("Abrir App do Funcionário", lambda e: open_app("employee.py"), ft.Icons.SMARTPHONE, 420)], spacing=7), padding=14),
        card(ft.Column([ft.Text("MÁQUINA / PORTARIA", size=11, weight=ft.FontWeight.W_800, color=BROWN), ft.Text("Placa → QR → Reconhecimento Facial → confirmação → abertura.", size=10, color=MUTED), primary("Abrir Máquina KEEPER", lambda e: open_app("machine.py"), ft.Icons.DNS, 420)], spacing=7), padding=14),
        card(ft.Column([ft.Text("ADMINISTRADOR", size=11, weight=ft.FontWeight.W_800, color=OLIVE_DARK), ft.Text("Presença em tempo real, CRUD, logs, relatórios e configurações.", size=10, color=MUTED), primary("Abrir Painel ADM", lambda e: open_app("admin.py"), ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, 420)], spacing=7), padding=14),
        ft.Row([pill(f"{s['usuarios']} usuários", ft.Icons.PEOPLE, OLIVE_SOFT, INK), pill(f"{s['veiculos']} veículos", ft.Icons.DIRECTIONS_CAR, BEIGE, INK), pill(f"{s['dentro']} dentro", ft.Icons.LOGIN, OLIVE_SOFT, INK)], alignment=ft.MainAxisAlignment.CENTER, wrap=True),
        secondary("Baixar modelos faciais", lambda e: download(), ft.Icons.DOWNLOAD, 420),
        ft.Text("Demo: funcionário breno / Breno@123 · ADM admin / Admin@123", size=10, color=MUTED, text_align=ft.TextAlign.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=9)

    def download():
        import asyncio
        async def go():
            try:
                import security as sec
                await asyncio.to_thread(sec.ensure_face_models,True);notify(page,"Modelos de face baixados com sucesso.")
            except Exception as ex:notify(page,str(ex),False)
        page.run_task(go)

    shell(page,body,600)

if __name__=="__main__":ft.app(target=main, assets_dir=str(__import__("pathlib").Path(__file__).resolve().parent / "assets"))
