"""KEEPER V6: bloqueio de placas, visitantes, redefinição de senha e relatório PDF."""
from __future__ import annotations
import hashlib, re, secrets
from datetime import datetime, timedelta
import db
import security as sec

FMT = "%Y-%m-%d %H:%M:%S"


def init() -> None:
    with db.conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS Placas_Bloqueadas(placa TEXT PRIMARY KEY, motivo TEXT, criado_em TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS Visitantes(id_visitante INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, documento TEXT,
            placa TEXT, codigo TEXT UNIQUE NOT NULL, validade TEXT NOT NULL, usado INTEGER DEFAULT 0, criado_em TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS Reset_Senha(id INTEGER PRIMARY KEY AUTOINCREMENT, id_usuario INTEGER NOT NULL, codigo_hash TEXT DEFAULT '',
            expira_em TEXT DEFAULT '', usado INTEGER DEFAULT 0, tentativas INTEGER DEFAULT 0, criado_em TEXT DEFAULT (datetime('now','localtime')));
        """)


# ---------- Bloqueio de placas ----------
def bloquear_placa(placa: str, motivo: str = "") -> None:
    p = sec.normalizar_placa(placa)
    if not sec.validar_placa(p):
        raise ValueError("Placa inválida: use ABC1D23 ou ABC-1234.")
    with db.conn() as c:
        c.execute("INSERT OR REPLACE INTO Placas_Bloqueadas(placa,motivo) VALUES(?,?)", (p, motivo.strip()))
    db.auditar(None, "BLOQUEIO", "PLACA", None, f"{p}: {motivo}")

def desbloquear_placa(placa: str) -> None:
    with db.conn() as c:
        c.execute("DELETE FROM Placas_Bloqueadas WHERE placa=?", (placa,))
    db.auditar(None, "DESBLOQUEIO", "PLACA", None, placa)

def placa_bloqueada(placa: str) -> str | None:
    with db.conn() as c:
        r = c.execute("SELECT motivo FROM Placas_Bloqueadas WHERE placa=?", (sec.normalizar_placa(placa),)).fetchone()
    return (r["motivo"] or "Sem motivo informado") if r else None

def listar_bloqueadas() -> list[dict]:
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM Placas_Bloqueadas ORDER BY criado_em DESC")]


# ---------- Visitantes (pré-autorização com código e validade) ----------
def criar_visitante(nome: str, documento: str, placa: str, horas: int = 4) -> str:
    if len(nome.strip()) < 3:
        raise ValueError("Informe o nome do visitante.")
    p = sec.normalizar_placa(placa) if placa.strip() else ""
    if p and not sec.validar_placa(p):
        raise ValueError("Placa inválida.")
    if p and placa_bloqueada(p):
        raise ValueError("Esta placa está bloqueada.")
    codigo = secrets.token_hex(3).upper()
    validade = (datetime.now() + timedelta(hours=max(1, min(int(horas), 72)))).strftime(FMT)
    with db.conn() as c:
        c.execute("INSERT INTO Visitantes(nome,documento,placa,codigo,validade) VALUES(?,?,?,?,?)", (nome.strip(), documento.strip(), p, codigo, validade))
    db.auditar(None, "CREATE", "VISITANTE", None, f"{nome.strip()} até {validade}")
    return codigo

def listar_visitantes() -> list[dict]:
    with db.conn() as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM Visitantes ORDER BY id_visitante DESC LIMIT 50")]
    agora = datetime.now().strftime(FMT)
    for r in rows:
        r["status"] = "USADO" if r["usado"] else ("EXPIRADO" if r["validade"] < agora else "VÁLIDO")
    return rows

def validar_visitante(codigo: str, placa: str = "") -> dict | None:
    """Valida o código na portaria e o consome (uso único)."""
    with db.conn() as c:
        r = c.execute("SELECT * FROM Visitantes WHERE codigo=? AND usado=0 AND validade>=?", ((codigo or "").strip().upper(), datetime.now().strftime(FMT))).fetchone()
        if not r or (r["placa"] and placa and r["placa"] != sec.normalizar_placa(placa)):
            return None
        c.execute("UPDATE Visitantes SET usado=1 WHERE id_visitante=?", (r["id_visitante"],))
        return dict(r)


# ---------- Esqueci minha senha (código gerado pelo ADM, 15 min, 5 tentativas) ----------
def _h(codigo: str) -> str:
    return hashlib.sha256(("keeper-reset:" + codigo).encode()).hexdigest()

def pedir_reset(login: str) -> bool:
    with db.conn() as c:
        u = c.execute("SELECT id_usuario FROM Usuarios WHERE (username=? OR email=?) AND status_conta='ATIVO'", (login.strip(), login.strip().lower())).fetchone()
        if u:
            c.execute("INSERT INTO Reset_Senha(id_usuario) VALUES(?)", (u["id_usuario"],))
    return bool(u)  # a tela responde igual nos dois casos (não revela se a conta existe)

def reset_pendentes() -> list[dict]:
    with db.conn() as c:
        return [dict(r) for r in c.execute("SELECT r.id, u.nome_completo, u.username, r.criado_em, r.codigo_hash!='' AS gerado FROM Reset_Senha r JOIN Usuarios u USING(id_usuario) WHERE r.usado=0 ORDER BY r.id DESC LIMIT 20")]

def gerar_codigo_reset(rid: int) -> str:
    codigo = f"{secrets.randbelow(10**6):06d}"
    with db.conn() as c:
        c.execute("UPDATE Reset_Senha SET codigo_hash=?, expira_em=?, tentativas=0 WHERE id=? AND usado=0", (_h(codigo), (datetime.now() + timedelta(minutes=15)).strftime(FMT), rid))
    return codigo

def redefinir_senha(login: str, codigo: str, nova: str) -> str | None:
    """Retorna None se deu certo, ou a mensagem de erro."""
    if not sec.RE_SENHA.fullmatch(nova or ""):
        return "Senha fraca: use 8+ caracteres com maiúscula, minúscula e número."
    with db.conn() as c:
        u = c.execute("SELECT id_usuario FROM Usuarios WHERE username=? OR email=?", (login.strip(), login.strip().lower())).fetchone()
        r = c.execute("SELECT * FROM Reset_Senha WHERE id_usuario=? AND usado=0 AND codigo_hash!='' ORDER BY id DESC LIMIT 1", (u["id_usuario"],)).fetchone() if u else None
        if not r or r["expira_em"] < datetime.now().strftime(FMT) or r["tentativas"] >= 5:
            return "Código inválido ou expirado. Peça um novo ao administrador."
        if r["codigo_hash"] != _h((codigo or "").strip()):
            c.execute("UPDATE Reset_Senha SET tentativas=tentativas+1 WHERE id=?", (r["id"],))
            return "Código incorreto."
        c.execute("UPDATE Reset_Senha SET usado=1 WHERE id=?", (r["id"],))
    db.atualizar_senha(u["id_usuario"], nova)
    db.auditar(u["id_usuario"], "UPDATE", "SENHA", u["id_usuario"], "Senha redefinida por código")
    return None


# ---------- Relatório PDF ----------
def relatorio_pdf(path: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    olive, khaki = colors.HexColor("#193C34"), colors.HexColor("#C8A96B")
    st = getSampleStyleSheet(); s = db.dashboard_resumo(); dias = db.estatisticas_diarias(7); hist = db.historico(None, 40)
    def tab(data, widths=None):
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), olive), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F4EF")]), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CFCDC4"))]))
        return t
    el = [Paragraph("KEEPER — Relatório de acessos", st["Title"]), Paragraph(f"Gerado em {datetime.now():%d/%m/%Y %H:%M}", st["Normal"]), Spacer(1, 10),
          tab([["Usuários", "Funcionários", "Veículos", "Dentro agora", "Acessos hoje"], [s["usuarios"], s["funcionarios"], s["veiculos"], s["dentro"], s["acessos_hoje"]]]),
          Spacer(1, 14), Paragraph("Últimos 7 dias", st["Heading2"])]
    d = Drawing(480, 150); ch = VerticalBarChart(); ch.x, ch.y, ch.width, ch.height = 30, 20, 430, 110
    ch.data = [[x["entradas"] for x in dias], [x["saidas"] for x in dias]]
    ch.categoryAxis.categoryNames = [x["dia"][5:] for x in dias]; ch.bars[0].fillColor, ch.bars[1].fillColor = olive, khaki
    ch.valueAxis.valueMin = 0; ch.valueAxis.valueMax = max(3, max(max(r) for r in ch.data) + 1); ch.valueAxis.valueStep = 1
    d.add(ch); el += [d, Paragraph("Verde = entradas · Areia = saídas", st["Normal"]), Spacer(1, 12), Paragraph("Acessos recentes", st["Heading2"]),
          tab([["Colaborador", "Placa", "Entrada", "Saída", "Status"]] + [[(h.get("nome_completo") or "")[:26], h.get("placa"), h.get("data_hora_entrada"), h.get("data_hora_saida") or "—", h.get("status_presenca")] for h in hist],
              [5 * cm, 2.4 * cm, 4 * cm, 4 * cm, 2 * cm])]
    SimpleDocTemplate(path, pagesize=A4, title="Relatório KEEPER", leftMargin=1.5 * cm, rightMargin=1.5 * cm).build(el)
    return path
