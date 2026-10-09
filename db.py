from __future__ import annotations

import csv
import io
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import bcrypt

BASE = Path(__file__).resolve().parent
DB = BASE / "keeper.db"


@contextmanager
def conn() -> Iterator[sqlite3.Connection]:
    """Conexão SQLite com commit/rollback automáticos e fechamento garantido.

    Todas as funções usam `with conn() as c:` — a conexão sempre é
    fechada ao final do bloco, mesmo em caso de exceção.
    """
    c = sqlite3.connect(DB, timeout=15)
    try:
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.execute("PRAGMA journal_mode = WAL")
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS Usuarios (
  id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
  nome_completo VARCHAR(100) NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  email VARCHAR(120) UNIQUE NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  tipo_acesso VARCHAR(20) NOT NULL CHECK(tipo_acesso IN ('ADM','FUNCIONARIO')),
  foto_facial_path VARCHAR(255),
  status_conta VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
  criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  atualizado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS Veiculos (
  id_veiculo INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER NOT NULL,
  placa VARCHAR(8) UNIQUE NOT NULL,
  modelo VARCHAR(80),
  cor VARCHAR(30),
  ativo INTEGER NOT NULL DEFAULT 1,
  criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  atualizado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Registros_Acesso (
  id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER NOT NULL,
  id_veiculo INTEGER NOT NULL,
  data_hora_entrada DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  data_hora_saida DATETIME NULL,
  status_presenca VARCHAR(10) NOT NULL CHECK(status_presenca IN ('DENTRO','FORA')),
  metodo_validacao VARCHAR(40) NOT NULL DEFAULT 'TRIPLA_VALIDACAO',
  portaria VARCHAR(40) NOT NULL DEFAULT 'PORTARIA 01',
  observacao VARCHAR(255),
  FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario),
  FOREIGN KEY (id_veiculo) REFERENCES Veiculos(id_veiculo)
);

CREATE TABLE IF NOT EXISTS Solicitacoes_Gate (
  id_solicitacao INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER NOT NULL,
  id_veiculo INTEGER NOT NULL,
  placa_detectada VARCHAR(8) NOT NULL,
  token_qr TEXT NOT NULL,
  score_facial REAL,
  sentido VARCHAR(10) NOT NULL CHECK(sentido IN ('ENTRADA','SAIDA')) DEFAULT 'ENTRADA',
  status VARCHAR(24) NOT NULL CHECK(status IN ('AGUARDANDO','CONFIRMADA','RECUSADA','EXPIRADA','CANCELADA','FINALIZADA')) DEFAULT 'AGUARDANDO',
  portaria VARCHAR(40) NOT NULL DEFAULT 'PORTARIA 01',
  criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  respondido_em DATETIME NULL,
  finalizado_em DATETIME NULL,
  FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario),
  FOREIGN KEY (id_veiculo) REFERENCES Veiculos(id_veiculo)
);

CREATE TABLE IF NOT EXISTS Notificacoes (
  id_notificacao INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER NOT NULL,
  id_solicitacao INTEGER,
  titulo VARCHAR(120) NOT NULL,
  mensagem VARCHAR(255) NOT NULL,
  lida INTEGER NOT NULL DEFAULT 0,
  criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario) ON DELETE CASCADE,
  FOREIGN KEY (id_solicitacao) REFERENCES Solicitacoes_Gate(id_solicitacao) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Configuracoes (
  chave VARCHAR(60) PRIMARY KEY,
  valor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Auditoria (
  id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
  id_usuario INTEGER,
  acao VARCHAR(60) NOT NULL,
  entidade VARCHAR(60) NOT NULL,
  entidade_id INTEGER,
  detalhe VARCHAR(255),
  criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
  FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_veiculos_usuario ON Veiculos(id_usuario);
CREATE INDEX IF NOT EXISTS idx_veiculos_placa ON Veiculos(placa);
CREATE INDEX IF NOT EXISTS idx_registros_usuario ON Registros_Acesso(id_usuario);
CREATE INDEX IF NOT EXISTS idx_registros_status ON Registros_Acesso(status_presenca);
CREATE INDEX IF NOT EXISTS idx_solic_status ON Solicitacoes_Gate(status);
CREATE INDEX IF NOT EXISTS idx_solic_usuario ON Solicitacoes_Gate(id_usuario);
CREATE INDEX IF NOT EXISTS idx_notif_usuario_lida ON Notificacoes(id_usuario, lida);
CREATE INDEX IF NOT EXISTS idx_auditoria_criado ON Auditoria(criado_em);
"""


def _hash(s: str) -> str:
    return bcrypt.hashpw(s.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _amigavel_unico(exc: Exception, username: str = "", email: str = "", placa: str = "") -> ValueError:
    """Traduz UNIQUE constraint do SQLite em mensagem clara para o usuário."""
    msg = str(exc).lower()
    if "usuarios.username" in msg or ("username" in msg and username):
        return ValueError("Este nome de usuário já está em uso. Escolha outro.")
    if "usuarios.email" in msg or ("email" in msg and email):
        return ValueError("Este e-mail já está cadastrado. Use outro endereço.")
    if "veiculos.placa" in msg or ("placa" in msg and placa):
        return ValueError(f"Já existe um veículo com a placa {placa}.")
    if "unique" in msg:
        return ValueError("Este registro já existe no sistema.")
    return ValueError(str(exc))


def _columns(c: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in c.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate(c: sqlite3.Connection) -> None:
    additions = {
        "Usuarios": {
            "atualizado_em": "DATETIME",
        },
        "Veiculos": {
            "atualizado_em": "DATETIME",
        },
        "Registros_Acesso": {
            "observacao": "VARCHAR(255)",
        },
    }
    for table, fields in additions.items():
        cols = _columns(c, table)
        for name, sqltype in fields.items():
            if name not in cols:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}")
                if name == "atualizado_em":
                    c.execute(f"UPDATE {table} SET atualizado_em=datetime('now','localtime') WHERE atualizado_em IS NULL")

    # Migrate the old request table if its CHECK does not include CANCELADA.
    sql_row = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='Solicitacoes_Gate'").fetchone()
    table_sql = (sql_row[0] or "") if sql_row else ""
    if "CANCELADA" not in table_sql:
        c.execute("ALTER TABLE Solicitacoes_Gate RENAME TO Solicitacoes_Gate_old")
        c.executescript("""
        CREATE TABLE Solicitacoes_Gate (
          id_solicitacao INTEGER PRIMARY KEY AUTOINCREMENT,
          id_usuario INTEGER NOT NULL,
          id_veiculo INTEGER NOT NULL,
          placa_detectada VARCHAR(8) NOT NULL,
          token_qr TEXT NOT NULL,
          score_facial REAL,
          sentido VARCHAR(10) NOT NULL CHECK(sentido IN ('ENTRADA','SAIDA')) DEFAULT 'ENTRADA',
          status VARCHAR(24) NOT NULL CHECK(status IN ('AGUARDANDO','CONFIRMADA','RECUSADA','EXPIRADA','CANCELADA','FINALIZADA')) DEFAULT 'AGUARDANDO',
          portaria VARCHAR(40) NOT NULL DEFAULT 'PORTARIA 01',
          criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
          respondido_em DATETIME NULL,
          finalizado_em DATETIME NULL,
          FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario),
          FOREIGN KEY (id_veiculo) REFERENCES Veiculos(id_veiculo)
        );
        """)
        c.execute("""INSERT INTO Solicitacoes_Gate
            (id_solicitacao,id_usuario,id_veiculo,placa_detectada,token_qr,score_facial,sentido,status,portaria,criado_em,respondido_em,finalizado_em)
            SELECT id_solicitacao,id_usuario,id_veiculo,placa_detectada,token_qr,score_facial,sentido,status,portaria,criado_em,respondido_em,finalizado_em
            FROM Solicitacoes_Gate_old""")
        c.execute("DROP TABLE Solicitacoes_Gate_old")


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
        _migrate(c)
        defaults = {
            "camera_index": "0",
            "face_threshold": "0.45",
            "portaria_nome": "PORTARIA 01",
            "auto_expire_seconds": "45",
            "empresa_nome": "KEEPER",
            "ocr_timeout": "25",
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO Configuracoes(chave, valor) VALUES(?,?)", (k, v))

        if not c.execute("SELECT 1 FROM Usuarios WHERE username='admin'").fetchone():
            c.execute(
                "INSERT INTO Usuarios(nome_completo, username, email, senha_hash, tipo_acesso) VALUES (?,?,?,?,?)",
                ("Administrador KEEPER", "admin", "admin@keeper.com", _hash("Admin@123"), "ADM"),
            )
        _seed_demo(c)


def _seed_demo(c: sqlite3.Connection) -> None:
    if c.execute("SELECT COUNT(*) FROM Usuarios WHERE tipo_acesso='FUNCIONARIO'").fetchone()[0]:
        return
    rows = [
        ("Breno Oliveira", "breno", "breno@keeper.com", "Breno@123"),
        ("Felipe Santos", "felipe", "felipe@keeper.com", "Felipe@123"),
        ("Juliana Costa", "juliana", "juliana@keeper.com", "Juliana@123"),
        ("Lucas Martins", "lucas", "lucas@keeper.com", "Lucas@123"),
    ]
    ids: dict[str, int] = {}
    for nome, username, email, senha in rows:
        cur = c.execute(
            "INSERT INTO Usuarios(nome_completo,username,email,senha_hash,tipo_acesso) VALUES(?,?,?,?,?)",
            (nome, username, email, _hash(senha), "FUNCIONARIO"),
        )
        ids[username] = int(cur.lastrowid)
    cars = [
        (ids["breno"], "ABC1D23", "Honda Civic", "Prata"),
        (ids["felipe"], "DEF4G56", "Jeep Compass", "Preto"),
        (ids["juliana"], "GHI7J89", "Toyota Corolla", "Branco"),
        (ids["lucas"], "JKL0M12", "Renault Kwid", "Branco"),
    ]
    c.executemany("INSERT INTO Veiculos(id_usuario,placa,modelo,cor) VALUES(?,?,?,?)", cars)


def auditar(usuario_id: int | None, acao: str, entidade: str, entidade_id: int | None = None, detalhe: str = "") -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO Auditoria(id_usuario,acao,entidade,entidade_id,detalhe) VALUES(?,?,?,?,?)",
            (usuario_id, acao, entidade, entidade_id, detalhe[:255]),
        )


def get_config(chave: str, default: str = "") -> str:
    with conn() as c:
        r = c.execute("SELECT valor FROM Configuracoes WHERE chave=?", (chave,)).fetchone()
        return str(r[0]) if r else default


def set_config(chave: str, valor: str) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO Configuracoes(chave,valor) VALUES(?,?) ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
            (chave, str(valor)),
        )


def autenticar(login: str, senha: str):
    with conn() as c:
        row = c.execute(
            "SELECT * FROM Usuarios WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
            (login.strip(), login.strip()),
        ).fetchone()
    if not row:
        return None, "Usuário não encontrado."
    if row["status_conta"] != "ATIVO":
        return None, "Conta inativa. Procure o administrador."
    try:
        ok = bcrypt.checkpw(senha.encode("utf-8"), row["senha_hash"].encode("utf-8"))
    except Exception:
        ok = False
    if not ok:
        return None, "Senha incorreta."
    return dict(row), None


def criar_usuario(nome: str, username: str, email: str, senha: str, tipo: str = "FUNCIONARIO", foto_path: str | None = None) -> int:
    with conn() as c:
        try:
            cur = c.execute(
                "INSERT INTO Usuarios(nome_completo,username,email,senha_hash,tipo_acesso,foto_facial_path) VALUES(?,?,?,?,?,?)",
                (nome.strip(), username.strip(), email.strip().lower(), _hash(senha), tipo, foto_path),
            )
            return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise _amigavel_unico(exc, username=username, email=email) from exc


def atualizar_usuario(uid: int, nome: str, username: str, email: str, tipo: str, status: str) -> None:
    with conn() as c:
        try:
            c.execute(
                "UPDATE Usuarios SET nome_completo=?, username=?, email=?, tipo_acesso=?, status_conta=?, atualizado_em=datetime('now','localtime') WHERE id_usuario=?",
                (nome.strip(), username.strip(), email.strip().lower(), tipo, status, uid),
            )
        except sqlite3.IntegrityError as exc:
            raise _amigavel_unico(exc, username=username, email=email) from exc


def atualizar_senha(uid: int, senha: str) -> None:
    with conn() as c:
        c.execute("UPDATE Usuarios SET senha_hash=?, atualizado_em=datetime('now','localtime') WHERE id_usuario=?", (_hash(senha), uid))


def atualizar_foto_facial(uid: int, caminho: str | None) -> None:
    with conn() as c:
        c.execute("UPDATE Usuarios SET foto_facial_path=?, atualizado_em=datetime('now','localtime') WHERE id_usuario=?", (caminho, uid))


def excluir_usuario(uid: int) -> None:
    with conn() as c:
        if c.execute("SELECT 1 FROM Registros_Acesso WHERE id_usuario=? LIMIT 1", (uid,)).fetchone():
            raise ValueError("Este usuário possui histórico. Inative a conta em vez de excluir.")
        if c.execute("SELECT 1 FROM Solicitacoes_Gate WHERE id_usuario=? LIMIT 1", (uid,)).fetchone():
            raise ValueError("Este usuário possui solicitações registradas. Inative a conta em vez de excluir.")
        c.execute("DELETE FROM Usuarios WHERE id_usuario=?", (uid,))


def listar_usuarios(busca: str = "", incluir_inativos: bool = True) -> list[dict[str, Any]]:
    sql = "SELECT u.*, (SELECT COUNT(*) FROM Veiculos v WHERE v.id_usuario=u.id_usuario AND v.ativo=1) AS total_veiculos, (SELECT COUNT(*) FROM Registros_Acesso r WHERE r.id_usuario=u.id_usuario) AS total_acessos FROM Usuarios u"
    clauses: list[str] = []
    params: list[Any] = []
    if not incluir_inativos:
        clauses.append("u.status_conta='ATIVO'")
    if busca.strip():
        t = f"%{busca.strip()}%"
        clauses.append("(u.nome_completo LIKE ? OR u.username LIKE ? OR u.email LIKE ?)")
        params.extend([t, t, t])
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY CASE WHEN u.status_conta='ATIVO' THEN 0 ELSE 1 END, u.nome_completo"
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def usuario_por_id(uid: int) -> dict[str, Any] | None:
    with conn() as c:
        r = c.execute("SELECT u.*, (SELECT COUNT(*) FROM Veiculos v WHERE v.id_usuario=u.id_usuario AND v.ativo=1) AS total_veiculos FROM Usuarios u WHERE u.id_usuario=?", (uid,)).fetchone()
        return dict(r) if r else None


def criar_veiculo(uid: int, placa: str, modelo: str, cor: str) -> int:
    placa_norm = placa.strip().upper()
    with conn() as c:
        try:
            cur = c.execute("INSERT INTO Veiculos(id_usuario,placa,modelo,cor) VALUES(?,?,?,?)", (uid, placa_norm, modelo.strip(), cor.strip()))
            return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise _amigavel_unico(exc, placa=placa_norm) from exc


def atualizar_veiculo(vid: int, placa: str, modelo: str, cor: str, uid: int | None = None, ativo: int | None = None) -> None:
    with conn() as c:
        fields = ["placa=?", "modelo=?", "cor=?", "atualizado_em=datetime('now','localtime')"]
        placa_norm = placa.strip().upper()
        params: list[Any] = [placa_norm, modelo.strip(), cor.strip()]
        if uid is not None:
            fields.append("id_usuario=?")
            params.append(uid)
        if ativo is not None:
            fields.append("ativo=?")
            params.append(1 if ativo else 0)
        params.append(vid)
        try:
            c.execute(f"UPDATE Veiculos SET {', '.join(fields)} WHERE id_veiculo=?", tuple(params))
        except sqlite3.IntegrityError as exc:
            raise _amigavel_unico(exc, placa=placa_norm) from exc


def definir_veiculo_status(vid: int, ativo: bool) -> None:
    with conn() as c:
        c.execute("UPDATE Veiculos SET ativo=?, atualizado_em=datetime('now','localtime') WHERE id_veiculo=?", (1 if ativo else 0, vid))


def excluir_veiculo(vid: int) -> None:
    with conn() as c:
        if c.execute("SELECT 1 FROM Registros_Acesso WHERE id_veiculo=? LIMIT 1", (vid,)).fetchone():
            raise ValueError("Este veículo possui histórico e não pode ser excluído. Inative-o.")
        if c.execute("SELECT 1 FROM Solicitacoes_Gate WHERE id_veiculo=? LIMIT 1", (vid,)).fetchone():
            raise ValueError("Este veículo possui solicitações. Inative-o.")
        c.execute("DELETE FROM Veiculos WHERE id_veiculo=?", (vid,))


def listar_veiculos(uid: int | None = None, busca: str = "", incluir_inativos: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT v.*, u.nome_completo, u.username, u.email, u.status_conta FROM Veiculos v JOIN Usuarios u ON u.id_usuario=v.id_usuario"
    clauses: list[str] = []
    params: list[Any] = []
    if not incluir_inativos:
        clauses.append("v.ativo=1")
    if uid is not None:
        clauses.append("v.id_usuario=?")
        params.append(uid)
    if busca.strip():
        t = f"%{busca.strip()}%"
        clauses.append("(v.placa LIKE ? OR v.modelo LIKE ? OR v.cor LIKE ? OR u.nome_completo LIKE ? OR u.username LIKE ?)")
        params.extend([t, t, t, t, t])
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY v.ativo DESC, v.placa"
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def veiculo_por_id(vid: int) -> dict[str, Any] | None:
    with conn() as c:
        r = c.execute("SELECT v.*,u.nome_completo,u.username,u.email,u.foto_facial_path FROM Veiculos v JOIN Usuarios u ON u.id_usuario=v.id_usuario WHERE v.id_veiculo=?", (vid,)).fetchone()
        return dict(r) if r else None


def veiculo_por_placa(placa: str) -> dict[str, Any] | None:
    p = placa.strip().upper().replace("-", "")
    with conn() as c:
        r = c.execute("SELECT v.*,u.nome_completo,u.username,u.email,u.status_conta,u.foto_facial_path FROM Veiculos v JOIN Usuarios u ON u.id_usuario=v.id_usuario WHERE upper(replace(v.placa,'-',''))=? AND v.ativo=1", (p,)).fetchone()
        return dict(r) if r else None


def qr_usuario(uid: int) -> dict[str, Any] | None:
    return usuario_por_id(uid)


def registrar_entrada(uid: int, vid: int, metodo: str = "TRIPLA_VALIDACAO", portaria: str = "PORTARIA 01", observacao: str = "") -> bool:
    with conn() as c:
        if not c.execute("SELECT 1 FROM Usuarios WHERE id_usuario=? AND status_conta='ATIVO'", (uid,)).fetchone():
            return False
        if not c.execute("SELECT 1 FROM Veiculos WHERE id_veiculo=? AND id_usuario=? AND ativo=1", (vid, uid)).fetchone():
            return False
        if c.execute("SELECT 1 FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'", (uid,)).fetchone():
            return False
        c.execute(
            "INSERT INTO Registros_Acesso(id_usuario,id_veiculo,status_presenca,metodo_validacao,portaria,observacao) VALUES(?,?, 'DENTRO',?,?,?)",
            (uid, vid, metodo, portaria, observacao),
        )
        return True


def registrar_saida(uid: int, vid: int | None = None, metodo: str = "TRIPLA_VALIDACAO", portaria: str = "PORTARIA 01", observacao: str = "") -> bool:
    with conn() as c:
        q = "UPDATE Registros_Acesso SET data_hora_saida=datetime('now','localtime'), status_presenca='FORA', metodo_validacao=?, portaria=?, observacao=? WHERE id_registro=(SELECT id_registro FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'"
        params: list[Any] = [metodo, portaria, observacao, uid]
        if vid is not None:
            q += " AND id_veiculo=?"
            params.append(vid)
        q += " ORDER BY id_registro DESC LIMIT 1)"
        cur = c.execute(q, tuple(params))
        return cur.rowcount > 0


def esta_dentro(uid: int) -> bool:
    with conn() as c:
        return bool(c.execute("SELECT 1 FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'", (uid,)).fetchone())


def veiculo_dentro(uid: int) -> dict[str, Any] | None:
    with conn() as c:
        r = c.execute("SELECT r.*,v.placa,v.modelo,v.cor FROM Registros_Acesso r JOIN Veiculos v ON v.id_veiculo=r.id_veiculo WHERE r.id_usuario=? AND r.status_presenca='DENTRO' ORDER BY r.id_registro DESC LIMIT 1", (uid,)).fetchone()
        return dict(r) if r else None


def presentes() -> list[dict[str, Any]]:
    with conn() as c:
        return [dict(r) for r in c.execute("""
            SELECT r.*,u.nome_completo,u.username,v.placa,v.modelo,v.cor
            FROM Registros_Acesso r
            JOIN Usuarios u ON u.id_usuario=r.id_usuario
            JOIN Veiculos v ON v.id_veiculo=r.id_veiculo
            WHERE r.status_presenca='DENTRO' ORDER BY r.data_hora_entrada
        """)]


def historico(uid: int | None = None, limite: int = 200, busca: str = "", somente_status: str | None = None) -> list[dict[str, Any]]:
    sql = """SELECT r.*,u.nome_completo,u.username,v.placa,v.modelo,v.cor
             FROM Registros_Acesso r JOIN Usuarios u ON u.id_usuario=r.id_usuario
             JOIN Veiculos v ON v.id_veiculo=r.id_veiculo"""
    clauses: list[str] = []
    params: list[Any] = []
    if uid is not None:
        clauses.append("r.id_usuario=?")
        params.append(uid)
    if busca.strip():
        t = f"%{busca.strip()}%"
        clauses.append("(u.nome_completo LIKE ? OR u.username LIKE ? OR v.placa LIKE ? OR v.modelo LIKE ? OR r.portaria LIKE ?)")
        params.extend([t, t, t, t, t])
    if somente_status in {"DENTRO", "FORA"}:
        clauses.append("r.status_presenca=?")
        params.append(somente_status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY r.id_registro DESC LIMIT ?"
    params.append(limite)
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def dashboard_resumo() -> dict[str, int]:
    with conn() as c:
        return {
            "usuarios": int(c.execute("SELECT COUNT(*) FROM Usuarios WHERE status_conta='ATIVO'").fetchone()[0]),
            "funcionarios": int(c.execute("SELECT COUNT(*) FROM Usuarios WHERE status_conta='ATIVO' AND tipo_acesso='FUNCIONARIO'").fetchone()[0]),
            "admins": int(c.execute("SELECT COUNT(*) FROM Usuarios WHERE status_conta='ATIVO' AND tipo_acesso='ADM'").fetchone()[0]),
            "veiculos": int(c.execute("SELECT COUNT(*) FROM Veiculos WHERE ativo=1").fetchone()[0]),
            "dentro": int(c.execute("SELECT COUNT(*) FROM Registros_Acesso WHERE status_presenca='DENTRO'").fetchone()[0]),
            "acessos_hoje": int(c.execute("SELECT COUNT(*) FROM Registros_Acesso WHERE date(data_hora_entrada)=date('now','localtime')").fetchone()[0]),
            "pendentes": int(c.execute("SELECT COUNT(*) FROM Solicitacoes_Gate WHERE status='AGUARDANDO'").fetchone()[0]),
            "notificacoes": int(c.execute("SELECT COUNT(*) FROM Notificacoes WHERE lida=0").fetchone()[0]),
        }


def criar_solicitacao(uid: int, vid: int, placa: str, token: str, score: float, sentido: str = "ENTRADA", portaria: str = "PORTARIA 01") -> int:
    with conn() as c:
        if sentido == "ENTRADA" and c.execute("SELECT 1 FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'", (uid,)).fetchone():
            raise ValueError("Funcionário já está dentro da empresa.")
        if sentido == "SAIDA" and not c.execute("SELECT 1 FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'", (uid,)).fetchone():
            raise ValueError("Funcionário não está dentro da empresa.")
        if c.execute("SELECT 1 FROM Solicitacoes_Gate WHERE id_usuario=? AND status='AGUARDANDO'", (uid,)).fetchone():
            raise ValueError("Já existe uma solicitação aguardando confirmação.")
        cur = c.execute("""INSERT INTO Solicitacoes_Gate
          (id_usuario,id_veiculo,placa_detectada,token_qr,score_facial,sentido,portaria)
          VALUES(?,?,?,?,?,?,?)""", (uid, vid, placa, token, score, sentido, portaria))
        sid = int(cur.lastrowid)
        msg = f"{portaria} validou {placa}. Confirme sua entrada." if sentido == "ENTRADA" else f"{portaria} validou {placa}. Confirme sua saída."
        c.execute("INSERT INTO Notificacoes(id_usuario,id_solicitacao,titulo,mensagem) VALUES(?,?,?,?)", (uid, sid, "Acesso detectado", msg))
        return sid


def solicitacao_por_id(sid: int) -> dict[str, Any] | None:
    with conn() as c:
        r = c.execute("""SELECT s.*,u.nome_completo,u.username,u.email,u.foto_facial_path,v.placa,v.modelo,v.cor
                     FROM Solicitacoes_Gate s JOIN Usuarios u ON u.id_usuario=s.id_usuario
                     JOIN Veiculos v ON v.id_veiculo=s.id_veiculo WHERE s.id_solicitacao=?""", (sid,)).fetchone()
        return dict(r) if r else None


def solicitacoes_pendentes_usuario(uid: int) -> list[dict[str, Any]]:
    expirar_solicitacoes()
    with conn() as c:
        return [dict(r) for r in c.execute("""SELECT s.*,v.placa,v.modelo,v.cor FROM Solicitacoes_Gate s
            JOIN Veiculos v ON v.id_veiculo=s.id_veiculo
            WHERE s.id_usuario=? AND s.status='AGUARDANDO' ORDER BY s.id_solicitacao DESC""", (uid,))]


def responder_solicitacao(sid: int, aprovado: bool) -> bool:
    with conn() as c:
        cur = c.execute("UPDATE Solicitacoes_Gate SET status=?,respondido_em=datetime('now','localtime') WHERE id_solicitacao=? AND status='AGUARDANDO'", ("CONFIRMADA" if aprovado else "RECUSADA", sid))
        if cur.rowcount:
            r = c.execute("SELECT id_usuario FROM Solicitacoes_Gate WHERE id_solicitacao=?", (sid,)).fetchone()
            if r:
                c.execute("UPDATE Notificacoes SET lida=1 WHERE id_solicitacao=?", (sid,))
        return cur.rowcount > 0


def cancelar_solicitacao(sid: int) -> bool:
    with conn() as c:
        cur = c.execute("UPDATE Solicitacoes_Gate SET status='CANCELADA',respondido_em=datetime('now','localtime') WHERE id_solicitacao=? AND status='AGUARDANDO'", (sid,))
        return cur.rowcount > 0


def finalizar_solicitacao(sid: int, uid: int, vid: int, sentido: str, portaria: str) -> bool:
    """Finaliza a solicitação e grava o acesso na mesma transação SQLite.

    A versão anterior fazia dois commits separados (registro e depois atualização
    da solicitação). Em uma demonstração com processos diferentes isso podia
    deixar a máquina presa em "aguardando" ou marcar a solicitação como finalizada
    mesmo quando o acesso não havia sido gravado.
    """
    with conn() as c:
        req = c.execute(
            "SELECT * FROM Solicitacoes_Gate WHERE id_solicitacao=? AND status='CONFIRMADA'",
            (sid,),
        ).fetchone()
        if not req:
            return False
        if int(req["id_usuario"]) != int(uid) or int(req["id_veiculo"]) != int(vid):
            return False

        user_ok = c.execute(
            "SELECT 1 FROM Usuarios WHERE id_usuario=? AND status_conta='ATIVO'", (uid,)
        ).fetchone()
        vehicle_ok = c.execute(
            "SELECT 1 FROM Veiculos WHERE id_veiculo=? AND id_usuario=? AND ativo=1", (vid, uid)
        ).fetchone()
        if not user_ok or not vehicle_ok:
            return False

        if sentido == "ENTRADA":
            if c.execute(
                "SELECT 1 FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO'", (uid,)
            ).fetchone():
                return False
            c.execute(
                "INSERT INTO Registros_Acesso(id_usuario,id_veiculo,status_presenca,metodo_validacao,portaria,observacao) VALUES(?,?, 'DENTRO',?,?,?)",
                (uid, vid, "TRIPLA_VALIDACAO", portaria, f"Solicitação #{sid} confirmada no celular"),
            )
        else:
            current = c.execute(
                "SELECT id_registro FROM Registros_Acesso WHERE id_usuario=? AND status_presenca='DENTRO' ORDER BY id_registro DESC LIMIT 1",
                (uid,),
            ).fetchone()
            if not current:
                return False
            c.execute(
                "UPDATE Registros_Acesso SET data_hora_saida=datetime('now','localtime'),status_presenca='FORA',metodo_validacao=?,portaria=?,observacao=? WHERE id_registro=?",
                ("TRIPLA_VALIDACAO", portaria, f"Solicitação #{sid} confirmada no celular", int(current[0])),
            )

        c.execute(
            "UPDATE Solicitacoes_Gate SET status='FINALIZADA',finalizado_em=datetime('now','localtime') WHERE id_solicitacao=? AND status='CONFIRMADA'",
            (sid,),
        )
        c.execute(
            "INSERT INTO Notificacoes(id_usuario,id_solicitacao,titulo,mensagem) VALUES(?,?,?,?)",
            (uid, sid, "Acesso confirmado", f"{portaria} concluiu a operação de {sentido.lower()}."),
        )
        return True


def expirar_solicitacoes(max_seconds: int | None = None) -> None:
    secs = max_seconds if max_seconds is not None else int(get_config("auto_expire_seconds", "45"))
    with conn() as c:
        c.execute("""UPDATE Solicitacoes_Gate SET status='EXPIRADA'
                  WHERE status='AGUARDANDO' AND (julianday('now','localtime')-julianday(criado_em))*86400 > ?""", (secs,))


def pendentes_maquina() -> list[dict[str, Any]]:
    expirar_solicitacoes()
    with conn() as c:
        return [dict(r) for r in c.execute("""SELECT s.*,u.nome_completo,v.modelo FROM Solicitacoes_Gate s
            JOIN Usuarios u ON u.id_usuario=s.id_usuario JOIN Veiculos v ON v.id_veiculo=s.id_veiculo
            WHERE s.status='AGUARDANDO' ORDER BY s.id_solicitacao DESC""")]


def listar_solicitacoes(limite: int = 200, busca: str = "", status: str | None = None) -> list[dict[str, Any]]:
    expirar_solicitacoes()
    sql = """SELECT s.*,u.nome_completo,u.username,v.placa,v.modelo FROM Solicitacoes_Gate s
             JOIN Usuarios u ON u.id_usuario=s.id_usuario JOIN Veiculos v ON v.id_veiculo=s.id_veiculo"""
    clauses: list[str] = []
    params: list[Any] = []
    if busca.strip():
        t = f"%{busca.strip()}%"
        clauses.append("(u.nome_completo LIKE ? OR u.username LIKE ? OR v.placa LIKE ? OR s.portaria LIKE ?)")
        params.extend([t, t, t, t])
    if status and status != "TODOS":
        clauses.append("s.status=?")
        params.append(status)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY s.id_solicitacao DESC LIMIT ?"
    params.append(limite)
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def notificacoes(uid: int, limite: int = 50, somente_nao_lidas: bool = False) -> list[dict[str, Any]]:
    sql = "SELECT * FROM Notificacoes WHERE id_usuario=?"
    params: list[Any] = [uid]
    if somente_nao_lidas:
        sql += " AND lida=0"
    sql += " ORDER BY id_notificacao DESC LIMIT ?"
    params.append(limite)
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def contador_notificacoes(uid: int) -> int:
    with conn() as c:
        return int(c.execute("SELECT COUNT(*) FROM Notificacoes WHERE id_usuario=? AND lida=0", (uid,)).fetchone()[0])


def marcar_notificacao_lida(nid: int) -> None:
    with conn() as c:
        c.execute("UPDATE Notificacoes SET lida=1 WHERE id_notificacao=?", (nid,))


def marcar_todas_notificacoes_lidas(uid: int) -> None:
    with conn() as c:
        c.execute("UPDATE Notificacoes SET lida=1 WHERE id_usuario=?", (uid,))


def limpar_notificacoes_lidas(uid: int) -> None:
    with conn() as c:
        c.execute("DELETE FROM Notificacoes WHERE id_usuario=? AND lida=1", (uid,))


def auditoria(limite: int = 200, busca: str = "") -> list[dict[str, Any]]:
    sql = "SELECT a.*,u.nome_completo FROM Auditoria a LEFT JOIN Usuarios u ON u.id_usuario=a.id_usuario"
    params: list[Any] = []
    if busca.strip():
        t = f"%{busca.strip()}%"
        sql += " WHERE a.acao LIKE ? OR a.entidade LIKE ? OR a.detalhe LIKE ? OR COALESCE(u.nome_completo,'') LIKE ?"
        params.extend([t, t, t, t])
    sql += " ORDER BY a.id_auditoria DESC LIMIT ?"
    params.append(limite)
    with conn() as c:
        return [dict(r) for r in c.execute(sql, tuple(params))]


def estatisticas_diarias(dias: int = 7) -> list[dict[str, Any]]:
    with conn() as c:
        return [dict(r) for r in c.execute("""
            WITH RECURSIVE datas(d) AS (
              SELECT date('now','localtime',?)
              UNION ALL
              SELECT date(d,'+1 day') FROM datas WHERE d < date('now','localtime')
            )
            SELECT datas.d AS dia,
                   (SELECT COUNT(*) FROM Registros_Acesso r WHERE date(r.data_hora_entrada)=datas.d) AS acessos,
                   (SELECT COUNT(*) FROM Registros_Acesso r WHERE date(r.data_hora_entrada)=datas.d AND r.status_presenca='DENTRO') AS entradas,
                   (SELECT COUNT(*) FROM Registros_Acesso r WHERE date(r.data_hora_saida)=datas.d AND r.data_hora_saida IS NOT NULL) AS saidas
            FROM datas ORDER BY datas.d
        """, (f"-{max(0,dias-1)} days",))]


def exportar_csv() -> str:
    rows = historico(None, 100000)
    out = io.StringIO()
    w = csv.writer(out, delimiter=';')
    w.writerow(["ID", "Usuário", "Username", "Placa", "Modelo", "Entrada", "Saída", "Status", "Método", "Portaria", "Observação"])
    for r in rows:
        w.writerow([r["id_registro"], r["nome_completo"], r["username"], r["placa"], r["modelo"] or "", r["data_hora_entrada"], r["data_hora_saida"] or "", r["status_presenca"], r["metodo_validacao"], r["portaria"], r.get("observacao") or ""])
    return out.getvalue()


def exportar_auditoria_csv() -> str:
    rows = auditoria(100000)
    out = io.StringIO()
    w = csv.writer(out, delimiter=';')
    w.writerow(["ID", "Usuário", "Ação", "Entidade", "ID Entidade", "Detalhe", "Data"])
    for r in rows:
        w.writerow([r["id_auditoria"], r.get("nome_completo") or "Sistema", r["acao"], r["entidade"], r.get("entidade_id") or "", r.get("detalhe") or "", r["criado_em"]])
    return out.getvalue()


init()
