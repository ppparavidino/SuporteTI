# Suporte TI

Sistema web para abertura e acompanhamento de chamados de suporte técnico. O projeto reúne uma API em FastAPI, uma interface web em HTML/CSS/JavaScript, persistência em Microsoft SQL Server e recursos opcionais de e-mail, anexos, laudos PDF e consultas com um agente local de IA.

> Este repositório contém o código-fonte e a estrutura do banco. Ele não inclui credenciais, dados de usuários, chamados de exemplo ou arquivos enviados por usuários.

## Funcionalidades

- Cadastro e login de usuários, com armazenamento de senha usando bcrypt.
- Abertura, consulta, atualização e arquivamento de chamados.
- Histórico de alterações dos chamados.
- Fluxo de recuperação de senha por e-mail.
- Upload, listagem, download e exclusão lógica de anexos.
- Geração e download de laudos técnicos em PDF.
- Assistente opcional que usa Ollama local e uma conta SQL de leitura para responder perguntas sobre chamados.
- Interface em português do Brasil, servida pela própria API ou por um servidor estático durante o desenvolvimento.

## Tecnologias

- Python 3.10 ou superior
- FastAPI e Uvicorn
- Microsoft SQL Server e Microsoft ODBC Driver 18 for SQL Server
- HTML, CSS e JavaScript sem framework
- bcrypt, python-dotenv, python-multipart, requests e ReportLab
- Ollama com o modelo `llama3.1:8b` (opcional)

## Pré-requisitos

1. Python 3.10+.
2. Uma instância Microsoft SQL Server acessível a partir da máquina que executa a API.
3. O Microsoft ODBC Driver 18 for SQL Server instalado.
4. Acesso de leitura e escrita à pasta configurada para anexos.
5. Ollama instalado e com o modelo configurado, caso queira usar o assistente de IA.
6. Uma conta SMTP, caso queira enviar mensagens de recuperação de senha e avisos de chamados.

O projeto usa autenticação integrada do Windows para a conexão principal do backend ao SQL Server. A conexão separada do agente de IA usa o usuário e a senha configurados em `DB_AGENTE_USER` e `DB_AGENTE_PASSWORD`.

## Instalação local

### 1. Clone o repositório e crie o ambiente Python

No PowerShell, a partir da pasta do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" python-multipart pyodbc bcrypt python-dotenv requests reportlab
```

### 2. Configure as variáveis de ambiente

Crie uma cópia local do arquivo de exemplo:

```powershell
Copy-Item .env.example .env
```

Edite `.env` e informe os dados da sua instalação. O `.env` é ignorado pelo Git; **não o adicione ao repositório**.

| Variável | Descrição |
| --- | --- |
| `DB_SERVER` | Nome ou endereço da instância SQL Server, por exemplo `localhost\SQLEXPRESS`. |
| `DB_DATABASE` | Banco utilizado pela aplicação; o script de estrutura espera `SuporteTI`. |
| `DB_DRIVER` | Driver ODBC instalado; o exemplo usa `ODBC Driver 18 for SQL Server`. |
| `DB_AGENTE_USER` | Login SQL de leitura usado pelo agente de IA. |
| `DB_AGENTE_PASSWORD` | Senha desse login SQL. Mantenha-a somente no ambiente local. |
| `OLLAMA_URL` | Endereço da API Ollama; por padrão `http://localhost:11434`. |
| `OLLAMA_MODEL` | Modelo local; por padrão `llama3.1:8b`. |
| `SMTP_HOST` | Host do servidor SMTP. |
| `SMTP_PORT` | Porta SMTP: normalmente `465` com SSL ou `587` com STARTTLS. |
| `SMTP_USER` | Conta usada para autenticar no SMTP. |
| `SMTP_PASSWORD` | Senha da conta SMTP. Não a publique nem a envie em issues. |
| `SMTP_USE_SSL` | `true` para SSL na porta 465; `false` para STARTTLS na porta 587. |
| `SMTP_SENDER` | Endereço que aparecerá como remetente. |
| `SMTP_SENDER_NAME` | Nome que aparecerá como remetente. |
| `CORS_ORIGINS` | Origens permitidas pela API, separadas por vírgula. Use apenas as origens da sua interface. |
| `ANEXOS_PATH` | Pasta local ou compartilhamento de rede para armazenar anexos. |
| `ANEXOS_MAX_MB` | Tamanho máximo permitido por arquivo. |
| `ANEXOS_RETENCAO_DIAS` | Parâmetro de retenção disponível; o código atual não executa expurgo automático com base nele. |
| `ANEXOS_EXTENSOES_PERMITIDAS` | Extensões aceitas, separadas por vírgula. |

A conexão principal do backend usa autenticação integrada (`Trusted_Connection`). Por isso, `DB_AGENTE_USER` e `DB_AGENTE_PASSWORD` **não** configuram essa conexão; são usados pelo agente de IA.

### 3. Prepare o SQL Server

1. Crie o banco `SuporteTI` na instância SQL Server.
2. Abra o arquivo [`.sql`](.sql) no SQL Server Management Studio e execute-o com uma conta que possa criar tabelas, relacionamentos e usuários no banco.
3. O script cria a estrutura das tabelas, mas não insere dados de exemplo. Cadastre setores e categorias antes de testar os fluxos que dependem deles.
4. O script associa o usuário de banco `agente_ia` a um login SQL já existente e o adiciona à função `db_datareader`. Se for usar o assistente de IA, crie esse login e configure a senha correspondente no `.env` antes de executar o script. Para não usar IA, remova ou adapte as instruções referentes a `agente_ia` no script.
5. Para a conexão principal, conceda à conta Windows que executa a API as permissões necessárias no banco.

O script inclui tabelas para usuários, setores, categorias, chamados, histórico, recuperação de senha e anexos.

### 4. Configure anexos, e-mail e IA (opcionais)

- **Anexos:** configure `ANEXOS_PATH` para uma pasta existente na qual o processo da API possa ler e gravar. As extensões permitidas e o limite de tamanho vêm do `.env.example`.
- **E-mail:** configure as variáveis `SMTP_*`. O sistema não consegue enviar avisos ou códigos de recuperação enquanto a configuração SMTP estiver vazia.
- **IA:** instale e inicie o Ollama, baixe o modelo configurado com `ollama pull llama3.1:8b` e confirme que `OLLAMA_URL` aponta para a instância local. O agente usa a conta SQL de leitura configurada separadamente.

### 5. Inicie a API

Na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Endereços locais:

- API: <http://127.0.0.1:8000/>
- Documentação interativa: <http://127.0.0.1:8000/docs>
- Login: <http://127.0.0.1:8000/login.html>
- Cadastro: <http://127.0.0.1:8000/cadastro.html>
- Interface de abertura de chamado: <http://127.0.0.1:8000/frontend/index.html>

### 6. Abra a interface

As páginas principais são servidas pela API em `/login.html`, `/cadastro.html` e `/frontend/`. A interface também pode ser servida por um servidor estático durante o desenvolvimento. Nesse caso, inclua a origem usada (por exemplo, `http://127.0.0.1:5500`) em `CORS_ORIGINS`.

Por padrão, os scripts da interface usam a porta `8000` no mesmo host da página. Para uma implantação em que a API esteja em outro endereço, defina `window.SUPORTE_API_BASE_URL` antes dos scripts da interface e permita a origem da página em `CORS_ORIGINS`.

## Endpoints principais

| Método | Caminho | Uso |
| --- | --- | --- |
| `GET` | `/` | Verifica se a API está respondendo. |
| `GET` | `/setores` | Lista setores disponíveis para cadastro. |
| `POST` | `/cadastro` | Cadastra um usuário. |
| `POST` | `/login` | Autentica um usuário. |
| `POST` | `/recuperar-senha` | Solicita código de recuperação por e-mail. |
| `POST` | `/redefinir-senha` | Redefine uma senha com o código de recuperação. |
| `POST` | `/chamados` | Abre um chamado. |
| `GET` | `/chamados` | Lista chamados. |
| `GET` | `/chamados/arquivo` | Lista chamados arquivados/resolvidos. |
| `GET` | `/chamados/{id}` | Consulta um chamado. |
| `PUT` | `/chamados/{id}` | Atualiza um chamado. |
| `GET` | `/chamados/{id}/historico` | Consulta o histórico de um chamado. |
| `GET` | `/usuarios/ti` | Lista usuários da equipe de TI. |
| `GET` | `/agente/status` | Consulta a disponibilidade do agente de IA. |
| `POST` | `/agente` | Envia uma pergunta ao agente de IA. |
| `POST` | `/chamados/{id}/anexos` | Envia um anexo para um chamado. |
| `GET` | `/chamados/{id}/anexos` | Lista os anexos de um chamado. |
| `GET` | `/anexos/{id}/download` | Baixa um anexo. |
| `DELETE` | `/anexos/{id}` | Solicita a exclusão lógica de um anexo. |
| `GET` | `/chamados/{id}/laudo` | Consulta o laudo de um chamado. |
| `POST` | `/chamados/{id}/laudo` | Gera ou atualiza o laudo. |
| `GET` | `/chamados/{id}/laudo/download` | Baixa o laudo em PDF. |

Os esquemas completos de entrada e saída estão disponíveis em `/docs` enquanto a API está em execução.

## Estrutura do repositório

```text
backend/              API FastAPI e serviços de banco, autenticação, e-mail,
                      anexos, laudos e agente de IA
frontend/             Interface web principal
database/backend/     Implementação anterior/alternativa do backend
database/frontend/    Interface anterior/alternativa
.env.example          Modelo de configuração sem credenciais reais
.gitignore            Arquivos locais e segredos excluídos do Git
.sql                  Estrutura do banco Microsoft SQL Server
README.md             Este guia
```

A aplicação principal é iniciada por `backend.main:app`. As pastas `database/backend` e `database/frontend` mantêm uma implementação anterior/alternativa; não são o ponto de entrada usado pelo comando de inicialização acima.

## Segurança e publicação

- Nunca publique `.env`, senhas, tokens, arquivos de banco com dados reais, anexos ou arquivos de configuração locais.
- Use `.env.example` como modelo e credenciais próprias no seu ambiente.
- Restrinja `CORS_ORIGINS` aos endereços efetivamente usados pela interface.
- Em produção, use HTTPS, armazenamento protegido para segredos, contas de banco com privilégio mínimo e uma política de backup e retenção adequada.
- A conexão ODBC atual usa `TrustServerCertificate=yes`; revise a validação do certificado antes de uma implantação de produção.
- Revise autenticação e autorização de cada endpoint, limites de requisição, tratamento de anexos e proteção dos dados pessoais antes de disponibilizar o sistema a usuários.
- O agente de IA consulta dados do banco: mantenha seu login SQL somente leitura e não use dados reais em ambientes de demonstração.

## Licença

Este repositório ainda não declara uma licença. Até que uma licença seja adicionada, não presuma que o código pode ser redistribuído ou reutilizado por terceiros.
