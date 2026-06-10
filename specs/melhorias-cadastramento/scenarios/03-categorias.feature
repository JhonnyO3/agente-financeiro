# language: pt
Funcionalidade: Categoria reflete a natureza real da compra
  Regras RF-04, RF-05.

  Cenário: Curso parcelado vira EDUCACAO e GASTO
    Dado que o usuário envia "Curso de inglês em 12x"
    Quando o cadastro é processado
    Então a categoria é "EDUCACAO"
    E o tipo é "GASTO"

  Cenário: Objeto parcelado vira COMPRAS
    Dado que o usuário envia "Comprei um console em 4x"
    Quando o cadastro é processado
    Então a categoria é "COMPRAS"
    E a categoria não é "PARCELAMENTOS"

  Cenário: Enum de categorias não contém valores removidos
    Quando o enum de categorias é inspecionado
    Então "PARCELAMENTOS" não está presente
    E "OUTROS" não está presente
    E "EDUCACAO" está presente
