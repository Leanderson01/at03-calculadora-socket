# AT03 – Calculadora distribuída via Socket TCP

Trabalho AT03 de Sistemas Distribuídos (SMD/UFC, 2026). Calculadora remota com as quatro operações e expressões aritméticas, usando **sockets TCP puros**: o paradigma de mais baixo nível da atividade. Não há middleware. Cliente e servidor combinam o próprio protocolo de aplicação por cima de um fluxo de bytes.

## Paradigma

- **Socket TCP** (módulo `socket` da biblioteca padrão).
- **Protocolo de aplicação próprio:** uma mensagem JSON por linha, terminada em `\n`. O `\n` é o que separa uma mensagem da outra dentro do fluxo TCP.

| Mensagem | Exemplo |
|---|---|
| Operação | `{"op": "soma", "a": 10, "b": 15}` |
| Expressão (Modo B) | `{"op": "expressao", "expr": "(10+15)*4"}` |
| Sucesso | `{"ok": true, "resultado": 100}` |
| Erro | `{"ok": false, "erro": "Divisão por zero"}` |

- O servidor atende vários clientes ao mesmo tempo, com uma thread por conexão.
- O cliente abre **uma** conexão e a mantém durante toda a sessão.
- Divisão por zero e entradas inválidas voltam como `{"ok": false, ...}` e o servidor continua no ar.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `servidor.py` | Servidor TCP multithread (todas as linhas comentadas) |
| `cliente.py` | Cliente com menu textual (todas as linhas comentadas) |
| `expressao.py` | Parser de expressões (descida recursiva, sem `eval`) |
| `test_expressao.py` | Testes do parser |

## Instalação

Python 3.10 ou mais novo. O projeto usa só a biblioteca padrão.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Como executar

Em dois terminais, nesta ordem:

```bash
python servidor.py               # escuta em localhost:5000
python cliente.py                # conecta em localhost:5000
```

Host e porta podem ser trocados com `--host` e `--porta`.

```
=== Calculadora Socket ===
1) Operação simples (ex: 10 + 15)
2) Expressão – Modo A (cliente decompõe e chama o servidor por operação)
3) Expressão – Modo B (servidor calcula a expressão inteira)
0) Sair
```

- **Modo A:** o cliente faz o parsing e manda uma requisição por operação básica:
  ```
    → servidor: soma(10, 15) = 25
    → servidor: multiplicacao(25, 4) = 100
  Resultado final: 100
  ```
- **Modo B:** o cliente manda a string e o servidor devolve o resultado final.

Testes do parser:

```bash
python -m pytest -q              # ou: python -m unittest
```

## Captura no Wireshark

1. Interface de loopback: **Adapter for loopback traffic capture** no Windows (instalado pelo Npcap), `lo` no Linux, `lo0` no macOS.
2. Filtro: `tcp.port == 5000`
3. Suba o servidor, comece a captura e só então abra o cliente.

O que observar:
- o **handshake TCP** (SYN, SYN-ACK, ACK) acontece uma única vez, quando o cliente abre;
- cada operação é um segmento com o JSON em texto puro (botão direito → *Follow → TCP Stream*);
- no Modo A aparecem várias trocas na **mesma conexão**, e no Modo B só uma;
- o FIN só aparece quando o cliente sai (opção 0).
