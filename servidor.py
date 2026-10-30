"""
Servidor da calculadora via Socket TCP.

Protocolo de aplicação: uma mensagem JSON por linha (terminada em '\n').
  Requisição de operação:  {"op": "soma", "a": 10, "b": 15}
  Requisição de expressão: {"op": "expressao", "expr": "(10+15)*4"}
  Resposta de sucesso:     {"ok": true, "resultado": 100}
  Resposta de erro:        {"ok": false, "erro": "Divisão por zero"}

Cada cliente é atendido por uma thread própria, e a conexão fica aberta
durante toda a sessão do cliente.
"""

import argparse  # lê host e porta da linha de comando
import json  # converte entre texto JSON e dicionários Python
import socket  # API de sockets do sistema operacional (TCP/IP)
import threading  # permite atender vários clientes ao mesmo tempo

from expressao import ErroExpressao, avaliar, executor_local  # parser próprio (sem eval)

OPERACOES_BASICAS = ("soma", "subtracao", "multiplicacao", "divisao")  # operações aceitas no campo "op"


def processar(requisicao):  # recebe o dicionário da requisição e devolve o dicionário da resposta
    op = requisicao.get("op")  # lê qual operação o cliente pediu
    try:  # qualquer erro de cálculo vira resposta de erro, nunca derruba o servidor
        if op in OPERACOES_BASICAS:  # operação básica: precisa dos campos "a" e "b"
            a = float(requisicao["a"])  # converte o primeiro operando para número
            b = float(requisicao["b"])  # converte o segundo operando para número
            resultado = executor_local(op, a, b)  # faz a conta localmente no servidor
        elif op == "expressao":  # Modo B: o servidor calcula a expressão inteira
            resultado = avaliar(str(requisicao["expr"]), executor_local)  # parser + executor local
        else:  # nenhuma operação conhecida
            return {"ok": False, "erro": f"Operação desconhecida: {op}"}  # avisa o cliente
        return {"ok": True, "resultado": resultado}  # resposta de sucesso
    except ZeroDivisionError:  # divisão por zero em qualquer ponto do cálculo
        return {"ok": False, "erro": "Divisão por zero"}  # erro claro para o cliente
    except ErroExpressao as e:  # expressão mal formada (parênteses, token desconhecido...)
        return {"ok": False, "erro": f"Expressão inválida: {e}"}  # devolve a explicação do parser
    except (KeyError, TypeError, ValueError):  # faltou campo ou o valor não é número
        return {"ok": False, "erro": "Requisição inválida: informe números em 'a' e 'b'"}  # erro de entrada


def atender_cliente(conexao, endereco):  # função executada em uma thread para cada cliente
    print(f"[+] Cliente conectado: {endereco}")  # registra a nova conexão no console
    with conexao:  # garante que o socket do cliente será fechado ao final
        arquivo = conexao.makefile("rw", encoding="utf-8", newline="\n")  # trata o socket como arquivo de texto, linha a linha
        for linha in arquivo:  # bloqueia até chegar uma linha; o laço termina quando o cliente fecha a conexão
            linha = linha.strip()  # remove o '\n' e espaços das pontas
            if not linha:  # ignora linhas vazias
                continue  # volta a esperar a próxima linha
            try:  # a linha precisa ser um JSON válido
                requisicao = json.loads(linha)  # converte o texto JSON em dicionário
                resposta = processar(requisicao)  # calcula a resposta
            except json.JSONDecodeError:  # o cliente mandou algo que não é JSON
                resposta = {"ok": False, "erro": "Mensagem não é um JSON válido"}  # avisa sem derrubar a thread
            except AttributeError:  # JSON válido, mas não é um objeto (ex.: uma lista)
                resposta = {"ok": False, "erro": "A mensagem deve ser um objeto JSON"}  # avisa sem derrubar a thread
            print(f"    {endereco} -> {linha}  |  resposta: {resposta}")  # mostra a troca no console
            arquivo.write(json.dumps(resposta, ensure_ascii=False) + "\n")  # serializa a resposta e termina com '\n'
            arquivo.flush()  # envia de fato os bytes pelo socket
    print(f"[-] Cliente desconectado: {endereco}")  # registra o fim da conexão


def main():  # ponto de entrada do servidor
    parser = argparse.ArgumentParser(description="Servidor da calculadora via Socket TCP")  # define os argumentos
    parser.add_argument("--host", default="localhost", help="endereço onde escutar")  # host padrão: localhost
    parser.add_argument("--porta", type=int, default=5000, help="porta TCP (padrão 5000)")  # porta fixa do projeto
    args = parser.parse_args()  # lê os argumentos digitados

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # cria um socket IPv4 (AF_INET) do tipo TCP (SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # permite reusar a porta logo após reiniciar o servidor
    servidor.bind((args.host, args.porta))  # associa o socket ao endereço e à porta
    servidor.listen()  # coloca o socket em modo de escuta, aceitando conexões
    print(f"Servidor Socket ouvindo em {args.host}:{args.porta} (Ctrl+C para sair)")  # avisa que está pronto

    try:  # laço principal; Ctrl+C encerra
        while True:  # aceita clientes indefinidamente
            conexao, endereco = servidor.accept()  # bloqueia até um cliente conectar (fim do handshake TCP)
            thread = threading.Thread(target=atender_cliente, args=(conexao, endereco), daemon=True)  # uma thread por cliente
            thread.start()  # começa a atender o cliente em paralelo
    except KeyboardInterrupt:  # o usuário apertou Ctrl+C
        print("\nEncerrando servidor.")  # mensagem de saída
    finally:  # sempre executa, com ou sem erro
        servidor.close()  # libera a porta


if __name__ == "__main__":  # só executa main() quando o arquivo é rodado diretamente
    main()  # inicia o servidor
