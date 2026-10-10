"""KEEPER no celular: serve o app do funcionário na rede Wi-Fi. Abra o endereço mostrado no navegador do celular."""
import socket
import flet as ft
import employee

PORT = 8550


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    url = f"http://{lan_ip()}:{PORT}"
    print("\n" + "=" * 52 + f"\n  KEEPER MOBILE — abra no celular (mesmo Wi-Fi):\n  {url}\n" + "=" * 52)
    try:
        import qrcode
        q = qrcode.QRCode(border=1); q.add_data(url); q.print_ascii(invert=True)
    except Exception:
        pass
    ft.app(target=employee.main, assets_dir=str(__import__("pathlib").Path(__file__).resolve().parent / "assets"), view=None, host="0.0.0.0", port=PORT)
