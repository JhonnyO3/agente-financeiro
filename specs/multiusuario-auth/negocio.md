# Negócio — Multiusuário, Autenticação e Reorganização do módulo agente

Pedido original (transcrito e organizado):

1. **Reorganizar o módulo do agente.** Hoje o agente de WhatsApp vive em `app/`.
   Quero movê-lo para um diretório próprio (`agent/`), melhorando a separação da
   aplicação e alinhando com `backend/` e `frontend/`.

2. **Suportar mais de um usuário.** Inicialmente o sistema previa só o meu usuário.
   Preciso poder ter vários usuários, cada um com acesso apenas ao seu próprio
   painel financeiro.

3. **Login.** Criar um modal simples de **login** (sem modal de cadastro). O
   **cadastro é feito via script**; o usuário apenas loga com as credenciais geradas
   pelo script e passa a acessar somente o controle financeiro dele. Implementar um
   módulo de autenticação usando as melhores práticas e a biblioteca mais simples e
   segura possível.

## Decisões já tomadas (ver spec.md)

- Diretório do agente: `app/` → **`agent/`**.
- WhatsApp continua com **um único número autorizado por enquanto**
  (`WHATSAPP_ALLOWED_NUMBER` permanece), mas o **modelo de dados já fica preparado
  para múltiplos usuários**.
- Autenticação por **JWT**: o backend FastAPI emite o token no login; o frontend o
  guarda e o envia nas chamadas.
- O **backend também exige o token** (não confia só na rede): cada endpoint protegido
  valida o JWT e filtra os dados pelo usuário do token.
- Login por **e-mail**; hash **bcrypt**; **access + refresh token** (padrão de mercado).
- Usuário padrão **Jhonatas** (`jhonatas2004@gmail.com`, role `ADMIN`).
- `usuarios` guarda: e-mail, senha (hash), telefone, username, nome, role, ativo.
- **RBAC** com papéis `ADMIN` e `USER`:
  - `USER` só acessa as próprias transações (isolamento por dono).
  - `ADMIN` é **master**: CRUD de usuários e CRUD de transações de qualquer usuário,
    com um **check de segurança extra** sobre a credencial/e-mail do admin.
