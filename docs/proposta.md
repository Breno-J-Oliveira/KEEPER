KEEPER (Guardião da entrada) Python:
O ecossistema será composto por três visões integradas na mesma aplicação Python (ou divididas por nível de acesso):Visão do Funcionário (App Mobile): Gera a credencial em QR Code, recebe alerta de portão abrindo e confirma a entrada.Visão do Totem / Portaria (App de Leitura): Executa a sequência de tripla validação (Placa $\rightarrow$ QR Code $\rightarrow$ Reconhecimento Facial).Visão do Administrador (Gestão & Dashboard): Controla usuários, veículos e monitora em tempo real quem está dentro da empresa.Fluxo Detalhado de Funcionamento[ Carro Chega ] ➔ 1. Leitura de Placa (OCR)
                     ↓
                 2. Scan do QR Code do Funcionário
                     ↓
                 3. Reconhecimento Facial na Portaria
                     ↓
                 [ Notificação Push no App do Funcionário ]
                     ↓
                 [ Pop-up: "Portão Abrindo - Confirmar Entrada?" ] ➔ (Confirma) ➔ Portão Abre & Registra Entrada no Banco
1. App do FuncionárioAutenticação: Login por E-mail ou Username e Senha.Credencial Digital: Tela principal exibe um QR Code dinâmico/criptografado contendo o ID do colaborador.Notificação em Tempo Real & Modal de Abertura:Quando a portaria valida os dados, o servidor dispara um sinal (via WebSockets/Flet pubsub) para o celular do funcionário.O aplicativo exibe uma notificação de alerta: "Portão de Acesso 1 sendo acionado".Abre uma tela de confirmação: Um botão "Confirmar Entrada" para que o usuário libere a passagem do veículo e confirme a presença física.Status Individual: Exibe o histórico de acessos (data e hora de entrada/saída) e veículos vinculados à sua conta.2. Painel de Gestão do Administrador (ADM)Controle de Presença em Tempo Real ("Quem está lá dentro"): Dashboard com cards dos colaboradores que registraram entrada e ainda não registraram saída.Logs de Entrada e Saída: Tabela com histórico completo (Quem entrou, qual carro usou, horário exato e método de validação).CRUD de Usuários e Veículos:Cadastrar, editar e inativar funcionários do sistema.Vincular novas placas de carro aos perfis.Definir permissões (ADM vs FUNCIONARIO).Estrutura de Banco de Dados (SQLite com Python)Estrutura relacional para atender aos requisitos obrigatórios do SENAI:1. Tabela Usuarios (Entidade Forte)SQLCREATE TABLE Usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    tipo_acesso VARCHAR(10) NOT NULL CHECK(tipo_acesso IN ('ADM', 'FUNCIONARIO')),
    foto_facial_path VARCHAR(255),
    status_conta VARCHAR(20) DEFAULT 'ATIVO'
);
2. Tabela Veiculos (Relacionamento 1 : N)SQLCREATE TABLE Veiculos (
    id_veiculo INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    placa VARCHAR(8) UNIQUE NOT NULL,
    modelo VARCHAR(50),
    cor VARCHAR(20),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario) ON DELETE CASCADE
);
3. Tabela Registros_Acesso (Histórico e Presença)SQLCREATE TABLE Registros_Acesso (
    id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_veiculo INTEGER NOT NULL,
    data_hora_entrada DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_hora_saida DATETIME NULL,
    status_presenca VARCHAR(10) CHECK(status_presenca IN ('DENTRO', 'FORA')),
    FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario),
    FOREIGN KEY (id_veiculo) REFERENCES Veiculos(id_veiculo)
);
Mapeamento dos Requisitos do SENAIRequisito do SENAIComo é implementado no SecureGate PythonLogin e AutenticaçãoLogin flexível no Flet aceitando Username ou E-mail + Senha criptografada (bcrypt ou hashlib).REGEX1. Validation de e-mail (^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$).2. Validação de placa Mercosul / Antiga (^([A-Z]{3}-\d{4})|([A-Z]{3}\d[A-Z]\d{2})$).UX/UIInterface limpa em Flet, alternando entre tema escuro/claro, modais de confirmação dinâmicos e cards para o ADM.Banco de DadosSQLite nativo do Python com Chaves Primárias (PK) e Chaves Estrangeiras (FK).CRUDC: Cadastro de novos usuários/carros. R: Dashboard de quem está na empresa. U: Editar cadastro/liberar portão. D: Excluir veículos ou inativar contas.Diferencial BiometriaMódulo de reconhecimento facial usando a biblioteca face_recognition / OpenCV em Python ou simulação de biometria nativa.Bibliotecas Python RecomendadasPara instalar no ambiente Python (sem depender de Node/Expo):Bashpip install flet opencv-python pyzbar face-recognition bcrypt
flet: Toda a interface gráfica mobile/desktop em Python.opencv-python & pyzbar: Captura de vídeo da webcam/câmera do celular e leitura do QR Code.face-recognition: Comparação da foto tirada no momento da entrada com a foto cadastrada no banco de dados.bcrypt: Criptografia segura das senhas dos funcionários.