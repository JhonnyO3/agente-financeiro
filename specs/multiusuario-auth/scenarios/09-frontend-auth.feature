# language: pt
Funcionalidade: Autenticação no frontend Flask — modal, sessão, Bearer, refresh e logout

  Como usuário do dashboard web
  Quero fazer login com email e senha
  Para acessar apenas meu painel e que minhas chamadas ao backend sejam autenticadas

  Contexto:
    Dado que a tarefa 04 (auth backend) está concluída com o contrato congelado
    E SECRET_KEY está configurado no ambiente Flask
    E existe o usuário Alice com email "alice@example.com" e senha "senha-alice" cadastrado via script

  # ---------------------------------------------------------------------------
  # Proteção de rotas — before_request
  # ---------------------------------------------------------------------------

  Cenário: Acessar o dashboard sem login redireciona para o modal de login
    Dado que nenhum usuário está logado (sessão vazia)
    Quando faço GET /
    Então a resposta redireciona para /login
    E a página de login exibe o modal de autenticação

  Cenário: Acessar rota /api/* do proxy sem login retorna 401 JSON
    Dado que nenhum usuário está logado
    Quando faço GET /api/transacoes via proxy do frontend
    Então a resposta tem status 401
    E o body é JSON (não HTML de login)

  Cenário: Rota /login GET é pública e não redireciona
    Dado que nenhum usuário está logado
    Quando faço GET /login
    Então a resposta tem status 200
    E a página renderiza o modal/formulário de login

  Cenário: Rota /logout é pública (isenta do before_request)
    Dado que nenhum usuário está logado
    Quando faço POST /logout
    Então a resposta não redireciona para /login em loop

  Cenário: Estáticos (CSS, JS) são isentos do before_request
    Dado que nenhum usuário está logado
    Quando faço GET /static/app.css
    Então a resposta tem status 200 ou 404 (não 302 para login)

  # ---------------------------------------------------------------------------
  # Login bem-sucedido
  # ---------------------------------------------------------------------------

  Cenário: Login com credenciais corretas grava tokens na sessão e redireciona ao dashboard
    Quando envio POST /login com body {"email":"alice@example.com","senha":"senha-alice"}
    Então o frontend chama POST /auth/login no backend
    E a resposta do frontend redireciona para /
    E a sessão Flask contém "access_token", "refresh_token", "role" e "email"
    E o cookie de sessão é HttpOnly e SameSite=Lax

  Cenário: Login com credenciais erradas re-renderiza o modal com mensagem de erro
    Quando envio POST /login com body {"email":"alice@example.com","senha":"errada"}
    Então a resposta tem status 200 ou 401
    E a página exibe mensagem de erro de autenticação
    E a sessão Flask não contém "access_token"

  Cenário: Não existe modal ou rota de cadastro no frontend
    Quando faço GET /cadastro ou GET /register
    Então a resposta é 404
    E a página de login não exibe formulário de criação de conta

  # ---------------------------------------------------------------------------
  # Chamadas ao backend levam Bearer
  # ---------------------------------------------------------------------------

  Cenário: BackendClient injeta Authorization Bearer em toda chamada após login
    Dado que Alice está logada com access_token "token-valido" na sessão
    Quando o frontend faz qualquer chamada ao backend via BackendClient
    Então a requisição ao backend contém o header "Authorization: Bearer token-valido"

  Cenário: Dashboard de Alice exibe apenas os dados de Alice
    Dado que Alice está logada
    Quando Alice acessa o dashboard principal
    Então o frontend chama /api/resumo e /api/transacoes com o Bearer de Alice
    E os dados exibidos pertencem somente a Alice

  # ---------------------------------------------------------------------------
  # Renovação automática de token (refresh transparente)
  # ---------------------------------------------------------------------------

  Cenário: Chamada com access_token expirado mas refresh válido renova transparente
    Dado que Alice está logada com access_token expirado e refresh_token válido na sessão
    Quando o frontend faz GET /api/transacoes e o backend retorna 401
    Então o frontend automaticamente chama POST /auth/refresh com o refresh_token da sessão
    E o backend retorna novo access_token e novo refresh_token
    E o frontend atualiza a sessão com os novos tokens
    E refaz a chamada original para GET /api/transacoes
    E a resposta final ao browser contém os dados sem erro visível

  Cenário: Renovação automática regrava access_token E refresh_token na sessão
    Dado que Alice obteve novo access_token via refresh
    Quando verifico a sessão Flask
    Então "access_token" contém o novo token
    E "refresh_token" contém o novo token rotacionado

  Cenário: Refresh inválido no segundo acesso 401 limpa sessão e redireciona ao login
    Dado que Alice está logada com access_token expirado e refresh_token inválido (revogado)
    Quando o frontend faz GET /api/transacoes e o backend retorna 401
    E o frontend tenta POST /auth/refresh e o backend retorna 401
    Então a sessão Flask é limpa (session.clear())
    E o browser é redirecionado para /login
    E não há novo retry (apenas 1 tentativa de refresh)

  Cenário: Após renovação bem-sucedida não há loop infinito (apenas 1 retry)
    Dado que o backend retorna 401 tanto na chamada original quanto na refeita
    Quando o frontend processa o segundo 401 após o retry
    Então o frontend para de tentar (sem loop)
    E limpa a sessão e redireciona para /login

  # ---------------------------------------------------------------------------
  # Logout
  # ---------------------------------------------------------------------------

  Cenário: Logout chama /auth/logout no backend e limpa a sessão
    Dado que Alice está logada com refresh_token na sessão
    Quando Alice faz POST /logout
    Então o frontend chama POST /auth/logout no backend com o refresh_token (best-effort)
    E session.clear() é executado
    E a resposta redireciona para /login

  Cenário: Logout encerra acesso ao dashboard
    Dado que Alice acaba de fazer logout
    Quando tenta acessar GET /
    Então a resposta redireciona para /login

  Cenário: Logout funciona mesmo se a chamada ao backend falhar (best-effort)
    Dado que o backend está indisponível no momento do logout
    Quando Alice faz POST /logout
    Então o frontend ainda executa session.clear()
    E redireciona para /login sem exibir erro ao usuário

  # ---------------------------------------------------------------------------
  # Config / boot
  # ---------------------------------------------------------------------------

  Cenário: Frontend não sobe quando SECRET_KEY está ausente
    Dado que SECRET_KEY não está definido no ambiente
    Quando tento iniciar a aplicação Flask
    Então a inicialização falha com erro explícito de configuração
    E a aplicação não fica em estado de escuta
