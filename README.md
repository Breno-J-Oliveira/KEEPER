<div align="center">
  <img src="docs/images/modo-escuro-logo.png" alt="KEEPER — Sistema Inteligente de Controle de Acesso" width="240">

  # KEEPER
  ### Sistema Inteligente de Controle de Acesso

  **Identificação. Validação. Autorização. Registro.**

  <p>
    <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.13">
    <img src="https://img.shields.io/badge/Flet-0.28.3-7C3AED?style=for-the-badge" alt="Flet">
    <img src="https://img.shields.io/badge/SQLite-database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
    <img src="https://img.shields.io/badge/OpenCV-computer%20vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV">
    <img src="https://img.shields.io/badge/Project-SENAI%202026-647332?style=for-the-badge" alt="Projeto SENAI 2026">
  </p>
  <p>
    <img src="https://img.shields.io/badge/status-projeto%20acadêmico-647332?style=flat-square" alt="Status">
    <img src="https://img.shields.io/badge/testes%20de%20lógica-8%20cenários%20aprovados-3F9A73?style=flat-square" alt="Testes de lógica">
    <img src="https://img.shields.io/badge/interface-tema%20claro%20e%20escuro-BFAB67?style=flat-square" alt="Temas">
  </p>
</div>

---

## Sobre o projeto

O **KEEPER** é um sistema de controle de acesso de pessoas e veículos desenvolvido pela equipe do curso Técnico em Desenvolvimento de Sistemas da **Escola SENAI “A. Jacob Lafer”**, em Santo André (SP), em 2026.

O projeto centraliza, em um único ecossistema, a identificação de funcionários e veículos, a validação de credenciais, a confirmação da solicitação de acesso e o registro de entradas e saídas. As três interfaces compartilham as regras de negócio e o banco de dados SQLite.

> **Importante:** nesta versão, o KEEPER registra e administra a autorização por software. Ele não aciona fisicamente um portão ou uma cancela.

## Principais funcionalidades

### Aplicativo do funcionário

- Login com usuário ou e-mail e senha.
- Credencial digital em QR Code dinâmico, renovado a cada 30 segundos.
- Recebimento de solicitações de acesso e possibilidade de confirmar ou recusar.
- Cadastro, edição e ativação/inativação dos próprios veículos.
- Consulta ao histórico de movimentações.
- Edição de perfil e senha.
- Cadastro, atualização e remoção da referência facial.

### Máquina de portaria

- Leitura da placa por câmera e OCR, com alternativa de digitação manual.
- Validação da placa e do vínculo com um veículo cadastrado e ativo.
- Leitura e validação da credencial QR assinada.
- Comparação facial com prova de vida por movimento da cabeça.
- Envio da solicitação para confirmação do funcionário.
- Registro de entrada ou saída somente após a confirmação.
- Tratamento de falhas de validação, cancelamento e expiração de solicitações.

### Painel administrativo

- Dashboard com indicadores de usuários, veículos, presença e acessos do dia.
- Cadastro, edição, inativação e exclusão de usuários e veículos conforme as regras do sistema.
- Consulta e filtragem do histórico de acessos.
- Registro manual de entrada e saída.
- Gestão de solicitações e auditoria de operações.
- Relatórios, exportação de histórico em CSV e relatório em PDF.
- Configurações de portaria, câmera, OCR e reconhecimento facial.
- Backup do banco SQLite e ferramentas administrativas.

---

## Demonstração visual

As imagens abaixo correspondem às telas documentadas do projeto. Para que sejam exibidas no GitHub, organize os arquivos na pasta `docs/images/` usando os nomes indicados na seção [Organização das imagens](#organização-das-imagens).

### Funcionário — login, cadastro e credencial QR

<p align="center">
  <img src="docs/images/figura-09-funcionario-login-qr.png" alt="Telas de login, cadastro e credencial QR do funcionário" width="850">
</p>
<p align="center"><sub>Figura 9 — Telas de login, cadastro e credencial QR do funcionário.</sub></p>

### Solicitações, veículos, conta e histórico

<p align="center">
  <img src="docs/images/figura-10-funcionario-solicitacoes-veiculos.png" alt="Confirmação de solicitação, veículos, conta e histórico do funcionário" width="850">
</p>
<p align="center"><sub>Figura 10 — Confirmação de solicitação, veículos, conta e histórico.</sub></p>

### Máquina de portaria

<p align="center">
  <img src="docs/images/figura-11-maquina-portaria.png" alt="Máquina de portaria com leitura de placa, QR Code e reconhecimento facial" width="850">
</p>
<p align="center"><sub>Figura 11 — Leitura de placa, QR Code, reconhecimento facial e confirmação.</sub></p>

### Painel administrativo

<p align="center">
  <img src="docs/images/figura-12-painel-administrativo.png" alt="Painel administrativo do KEEPER" width="850">
</p>
<p align="center"><sub>Figura 12 — Dashboard, usuários, veículos, histórico e configurações.</sub></p>

### Acesso remoto

<p align="center">
  <img src="docs/images/figura-15-cloudflare-acesso-remoto.png" alt="Quick Tunnels do Cloudflare e teste do KEEPER em outra rede" width="850">
</p>
<p align="center"><sub>Figura 15 — Quick Tunnels e teste de acesso pelo celular em outra rede.</sub></p>

### Identidade visual

<p align="center">
  <img src="docs/images/paleta.png" alt="Paleta de cores do KEEPER" width="620">
</p>
<p align="center"><sub>Paleta visual baseada em tons de verde-oliva, bege e dourado, com suporte a temas claro e escuro.</sub></p>

---

## Como funciona o fluxo de acesso

```text
┌───────────────────────────┐
│ Veículo chega à portaria  │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Leitura/validação da placa│  OCR ou entrada manual
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Validação do QR Code      │  Assinatura e validade
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Reconhecimento facial     │  Comparação e prova de vida
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ Confirmação do funcionário│  Confirmar ou recusar
└─────────────┬─────────────┘
              ▼
       ┌──────────────┐
       │ Confirmado?  │
       └───┬──────┬───┘
          Sim    Não
           ▼      ▼
┌───────────────────┐  ┌─────────────────────┐
│ Registra o acesso │  │ Não registra acesso │
└───────────────────┘  └─────────────────────┘
```

Uma falha na leitura ou validação interrompe o fluxo. Solicitações recusadas, canceladas ou expiradas não geram um registro concluído de acesso.

## Arquitetura resumida

```text
                  ┌──────────────────────┐
                  │ Aplicativo funcionário│
                  │ employee.py / mobile.py│
                  └───────────┬──────────┘
                              │
┌──────────────────────┐      │      ┌──────────────────────┐
│ Máquina de portaria  │──────┼──────│ Painel administrativo│
│ machine.py           │      │      │ admin.py / web_admin.py│
└───────────┬──────────┘      │      └───────────┬──────────┘
            └─────────────────┼──────────────────┘
                              ▼
                  ┌──────────────────────┐
                  │ Regras e persistência│
                  │ db.py / security.py  │
                  └───────────┬──────────┘
                              ▼
                  ┌──────────────────────┐
                  │ SQLite — keeper.db   │
                  └──────────────────────┘
```

As interfaces reutilizam componentes visuais de `ui.py`, operações de dados de `db.py` e funções de validação e visão computacional de `security.py`.

## Tecnologias utilizadas

| Tecnologia | Utilização |
|---|---|
| **Python 3.13** | Linguagem principal e regras de negócio. |
| **Flet 0.28.3** | Interfaces desktop e web. |
| **SQLite** | Banco relacional local (`keeper.db`). |
| **bcrypt** | Hash e verificação de senhas. |
| **qrcode / Pillow** | Geração de imagens de QR Code e processamento de imagens. |
| **OpenCV** | Câmera, leitura de QR Code e processamento facial. |
| **YuNet e SFace (ONNX)** | Detecção e comparação facial. |
| **pytesseract + Tesseract OCR** | Extração de texto da placa do veículo. |
| **Cloudflare Tunnel** | Exposição temporária dos serviços web locais para demonstração remota. |
| **Git e GitHub** | Versionamento e colaboração. |

## Estrutura principal

```text
KEEPER/
├── app.py                 # Inicialização da aplicação principal
├── employee.py            # Interface do funcionário
├── machine.py             # Máquina de portaria e câmera
├── admin.py               # Painel administrativo
├── mobile.py              # Serviço web do funcionário (porta 8550)
├── web_admin.py           # Serviço web do administrador (porta 8551)
├── db.py                  # Banco de dados e operações CRUD
├── security.py             # Autenticação, QR, OCR e reconhecimento facial
├── ui.py                  # Componentes e identidade visual
├── extras.py              # Relatórios e funcionalidades auxiliares
├── smoke_test.py          # Testes automatizados de lógica
├── download_models.py     # Apoio à obtenção dos modelos necessários
├── requirements.txt       # Dependências Python
├── keeper.db              # Banco de dados local (gerado/usado na execução)
├── models/                # Modelos de visão computacional
├── assets/                # Recursos visuais e fontes
├── data/faces/            # Referências faciais locais
├── exports/               # Arquivos exportados
├── storage/               # Preferências locais
├── INSTALL_WINDOWS.cmd    # Preparação do ambiente Windows
├── RUN_SERVIDOR.cmd       # Inicialização dos serviços e túneis
└── CHECK_KEEPER.cmd       # Verificações auxiliares
```

## Requisitos para executar

- Windows 10/11 de 64 bits.
- Python 3.13 de 64 bits.
- Dependências listadas em `requirements.txt`.
- Tesseract OCR instalado e configurado para a leitura automática de placas.
- Câmera disponível para os recursos que dependem de captura de imagem.
- Modelos YuNet/SFace necessários ao reconhecimento facial.
- `cloudflared` instalado apenas para publicar os serviços por Quick Tunnel.

## Instalação e execução no Windows

### 1. Obtenha o projeto

```bash
git clone https://github.com/Breno-J-Oliveira/KEEPER.git
cd KEEPER
```

> Se o repositório tiver outro nome ou endereço, substitua a URL acima pelo link correto do projeto.

### 2. Prepare o ambiente

Execute `INSTALL_WINDOWS.cmd`, caso ele esteja presente na versão do repositório. O script deve preparar o ambiente virtual e instalar as dependências. Se o ambiente `.venv` já existir, confirme que ele aponta para uma instalação de Python disponível no computador.

### 3. Inicie o sistema

Execute `RUN_SERVIDOR.cmd`. O inicializador deve iniciar a portaria, o serviço web do funcionário, o painel administrativo e os túneis configurados.

### 4. Endereços locais

| Serviço | Endereço local | Porta |
|---|---|---:|
| Funcionário | `http://localhost:8550` | 8550 |
| Administrador | `http://localhost:8551` | 8551 |
| Portaria | Aplicativo local com acesso à câmera | — |

Para acesso remoto, o Cloudflare Quick Tunnel gera URLs temporárias `https://...trycloudflare.com`. Os links mudam quando os túneis são reiniciados. O computador servidor deve permanecer ligado, conectado à internet e com os processos em execução.

## Testes e validação

A documentação do projeto registra a execução do `smoke_test.py` e a aprovação de oito cenários de lógica de negócio, cobrindo operações como autenticação, validação de QR Code, solicitações, entrada/saída, duplicidades e expiração.

Os testes integrados que dependem de câmera, interface gráfica e acesso por rede externa ainda precisam ser registrados pela equipe. Portanto, os resultados de lógica não devem ser interpretados como garantia de que todos os cenários físicos e remotos foram validados.

## Limitações conhecidas

- O sistema depende do computador que mantém os serviços e o arquivo SQLite.
- Os Quick Tunnels são temporários e não substituem uma hospedagem permanente.
- OCR e reconhecimento facial variam conforme câmera, iluminação e qualidade da imagem.
- O Tesseract é um componente externo e precisa estar instalado para a leitura automática de placas.
- O fluxo de visitantes ainda não está integrado à validação da portaria.
- A versão documentada não aciona fisicamente portão ou cancela.
- A chave usada para assinar o QR Code é fixa no código nesta versão e deve ser externalizada antes de qualquer uso real.
- Imagens faciais são dados pessoais sensíveis; o uso exige cuidado, consentimento e controle de acesso aos arquivos.

## Equipe

Projeto acadêmico desenvolvido no curso Técnico em Desenvolvimento de Sistemas da Escola SENAI “A. Jacob Lafer”, Santo André — SP, 2026.

| Integrante | Participação |
|---|---|
| Breno Oliveira | Desenvolvimento e integração do sistema |
| Vinícius Vila Nova | Equipe de desenvolvimento |
| Gustavo Barreto | Equipe de desenvolvimento |
| Mariana Felipe | Equipe de desenvolvimento |
| Felipe Bertaco | Equipe de desenvolvimento |
| Nicolas Tukaze | Equipe de desenvolvimento |

**Orientadores:** Prof. Raul Lopes e Prof. Paulo Camargo.

## Organização das imagens

Crie a pasta `docs/images/` no repositório e copie/renomeie as imagens fornecidas para estes nomes, exatamente:

| Imagem da documentação | Nome esperado no repositório |
|---|---|
| Logo para tema escuro | `docs/images/modo-escuro-logo.png` |
| Figura 9 — Login, cadastro e QR | `docs/images/figura-09-funcionario-login-qr.png` |
| Figura 10 — Solicitações, veículos e histórico | `docs/images/figura-10-funcionario-solicitacoes-veiculos.png` |
| Figura 11 — Máquina de portaria | `docs/images/figura-11-maquina-portaria.png` |
| Figura 12 — Painel administrativo | `docs/images/figura-12-painel-administrativo.png` |
| Figura 15 — Quick Tunnels e celular | `docs/images/figura-15-cloudflare-acesso-remoto.png` |
| Paleta de cores | `docs/images/paleta.png` |

O GitHub não consegue exibir imagens que estejam apenas no computador ou em uma captura de tela da pasta: os arquivos de imagem precisam ser enviados ao repositório. Caminhos e nomes de arquivos diferenciam maiúsculas e minúsculas.

## Próximas melhorias

- Externalizar segredos e parâmetros sensíveis para variáveis de ambiente.
- Registrar testes completos da interface, câmera e acesso remoto.
- Integrar a validação de visitantes ao fluxo da portaria.
- Avaliar hospedagem persistente e armazenamento de dados adequado a um ambiente real.
- Estudar integração com hardware de portão/cancela, com mecanismos de segurança física.

---

<div align="center">
  <sub>KEEPER — Projeto acadêmico • Técnico em Desenvolvimento de Sistemas • SENAI A. Jacob Lafer • 2026</sub>
</div>
