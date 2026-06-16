# language: pt
Funcionalidade: Carregador e renderizador de templates Jinja2
  Carrega templates de agent/templates/ e renderiza com contexto preparado em Python.

  Cenário: carregar o conteúdo bruto de um template
    Dado o template "menu.md" em agent/templates
    Quando chamo carregar_template("menu.md")
    Então recebo uma string não vazia com o conteúdo do arquivo

  Cenário: renderizar com interpolação simples
    Quando renderizo "listar_vazio.md" com contexto {periodo: "Jun/2026"}
    Então o texto contém "Jun/2026"

  Cenário: renderizar com iteração sobre lista
    Dado um contexto com grupos e itens
    Quando renderizo "listar_concluido.md"
    Então cada item da lista aparece uma vez no texto

  Cenário: renderizar com condicional
    Dado um contexto com pendente_positivo verdadeiro
    Quando renderizo "listar_concluido.md"
    Então a linha de pendente aparece
    E com pendente_positivo falso a linha de pendente não aparece

  Cenário: blocos Jinja não introduzem espaços ou linhas extras
    Quando renderizo qualquer template com blocos for/if
    Então não há linhas em branco nem espaços extras vindos das tags de bloco

  Cenário: template inexistente levanta erro
    Quando renderizo "nao_existe.md"
    Então um TemplateNotFound é levantado
