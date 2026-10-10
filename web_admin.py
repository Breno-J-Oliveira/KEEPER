"""KEEPER ADM como site (porta 8551): abra no navegador de qualquer computador da rede."""
from pathlib import Path
import flet as ft
import admin
from mobile import lan_ip

PORT = 8551

if __name__ == "__main__":
    print("\n" + "=" * 54 + f"\n  KEEPER ADM — abra no navegador:\n  http://{lan_ip()}:{PORT}\n" + "=" * 54)
    ft.app(target=admin.main, view=None, host="0.0.0.0", port=PORT, assets_dir=str(Path(__file__).resolve().parent / "assets"))
