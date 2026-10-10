"""Teste funcional rápido do KEEPER: banco, autenticação, QR, CRUD e fluxo de presença."""
from pathlib import Path

import db
import security as sec

TEST_USERNAME = "smoketest"
TEST_EMAIL = "smoke@keeper.com"


def _limpar_usuario_teste() -> None:
    """Remove por completo o usuário de teste e seus vínculos (idempotente)."""
    with db.conn() as c:
        ids = [r[0] for r in c.execute("SELECT id_usuario FROM Usuarios WHERE username=?", (TEST_USERNAME,)).fetchall()]
        for uid in ids:
            c.execute("DELETE FROM Notificacoes WHERE id_usuario=?", (uid,))
            c.execute("DELETE FROM Solicitacoes_Gate WHERE id_usuario=?", (uid,))
            c.execute("DELETE FROM Registros_Acesso WHERE id_usuario=?", (uid,))
            c.execute("DELETE FROM Veiculos WHERE id_usuario=?", (uid,))
            c.execute("DELETE FROM Auditoria WHERE id_usuario=?", (uid,))
            c.execute("DELETE FROM Usuarios WHERE id_usuario=?", (uid,))


print("[1] Banco:", db.DB)
print("[2] Resumo inicial:", db.dashboard_resumo())

u, err = db.autenticar("breno", "Breno@123")
assert not err and u and u["tipo_acesso"] == "FUNCIONARIO", err
print("[3] Login funcionário: OK ->", u["nome_completo"])

admin, err = db.autenticar("admin", "Admin@123")
assert not err and admin and admin["tipo_acesso"] == "ADM", err
print("[4] Login ADM: OK")

token = sec.gerar_token(u["id_usuario"])
uid = sec.validar_token(token)
assert uid == u["id_usuario"]
print("[5] QR assinado/expiração: OK")

cars = db.listar_veiculos(u["id_usuario"])
assert cars, "Breno precisa de um veículo demo."
print("[6] FK usuário -> veículo: OK ->", cars[0]["placa"])

# CRUD temporário (limpeza total antes e depois: o teste é repetível).
_limpar_usuario_teste()
test_user = db.criar_usuario("Smoke Test", TEST_USERNAME, TEST_EMAIL, "Smoke@123", "FUNCIONARIO")
test_vehicle = db.criar_veiculo(test_user, "ZZZ9Z99", "Smoke Car", "Cinza")
assert db.usuario_por_id(test_user)
assert db.veiculo_por_id(test_vehicle)
print("[7] CREATE usuário + veículo: OK")

db.atualizar_usuario(test_user, "Smoke Test Atualizado", TEST_USERNAME, "smoke2@keeper.com", "FUNCIONARIO", "ATIVO")
db.atualizar_veiculo(test_vehicle, "ZZZ9Z99", "Smoke Car 2", "Preto", test_user)
print("[8] UPDATE usuário + veículo: OK")

assert db.registrar_entrada(test_user, test_vehicle, "SMOKE_TEST", "PORTARIA TESTE")
assert db.esta_dentro(test_user)
assert db.registrar_saida(test_user, test_vehicle, "SMOKE_TEST", "PORTARIA TESTE", "Saída de teste")
assert not db.esta_dentro(test_user)
print("[9] Entrada + saída: OK")

# Fluxo completo da máquina: solicitação → confirmação → finalização.
sid = db.criar_solicitacao(test_user, test_vehicle, "ZZZ9Z99", sec.gerar_token(test_user), 0.9, "ENTRADA", "PORTARIA TESTE")
assert db.responder_solicitacao(sid, True), "A confirmação deveria ser registrada."
assert db.finalizar_solicitacao(sid, test_user, test_vehicle, "ENTRADA", "PORTARIA TESTE"), "A finalização deveria registrar o acesso."
assert db.esta_dentro(test_user), "O funcionário deveria estar dentro após a finalização."
print("[10] Solicitação + confirmação + finalização (portão): OK")

# Saída pelo mesmo fluxo.
sid2 = db.criar_solicitacao(test_user, test_vehicle, "ZZZ9Z99", sec.gerar_token(test_user), 0.9, "SAIDA", "PORTARIA TESTE")
assert db.responder_solicitacao(sid2, True)
assert db.finalizar_solicitacao(sid2, test_user, test_vehicle, "SAIDA", "PORTARIA TESTE")
assert not db.esta_dentro(test_user)
print("[11] Fluxo de saída completo: OK")

# Duplicidades precisam de mensagens claras (nunca erro cru do SQLite).
try:
    db.criar_usuario("Outro", TEST_USERNAME, "outro@keeper.com", "Outro@123")
    raise SystemExit("ERRO: username duplicado foi aceito.")
except ValueError as ex:
    assert "UNIQUE" not in str(ex).upper(), ex
    print("[12] Duplicidade de usuário com mensagem clara: OK ->", ex)

print("[13] Auditoria disponível:", len(db.auditoria(20)))
print("[14] Modelos presentes:", [str(p) for p in [Path(sec.MODELS / n) for n in sec.MODEL_URLS] if p.exists()])
print("[15] OCR disponível:", sec.ocr_disponivel())
_limpar_usuario_teste()
print("[16] Limpeza do usuário de teste: OK")
print("Tudo certo. Para testar câmera/face: scripts\\RUN_DEMO.cmd")
