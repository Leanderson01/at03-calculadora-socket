"""
Cliente da calculadora via Socket TCP.

Abre UMA conexão TCP com o servidor e a mantém aberta durante toda a
sessão. Cada pedido é uma linha JSON; cada resposta também.

Menu:
  1) operação simples         -> uma requisição {"op": ..., "a": ..., "b": ...}
  2) expressão, Modo A        -> o cliente decompõe e faz uma requisição por operação
  3) expressão, Modo B        -> uma requisição {"op": "expressao", "expr": ...}
"""

import argparse  # lê host e porta da linha de comando
import json  # converte dicionários em texto JSON e vice-versa
import socket  # API de sockets do sistema operacional (TCP/IP)

from expressao import SIMBOLOS, ErroExpressao, analisar_operacao_simples, avaliar, formatar  # parser próprio


class ErroRemoto(Exception):  # erro devolvido pelo servidor ({"ok": false, ...})
    pass  # não precisa de nada além do nome e da mensagem


class ClienteSocket:  # encapsula a conexão persistente com o servidor
    def __init__(self, host, porta):  # abre a conexão ao criar o objeto
        self.sock = socket.create_connection((host, porta))  # cria o socket TCP e conecta (three-way handshake)
        self.arquivo = self.sock.makefile("rw", encoding="utf-8", newline="\n")  # lê/escreve o socket linha a linha

    def requisitar(self, mensagem):  # envia um pedido e espera a resposta
        self.arquivo.write(json.dumps(mensagem) + "\n")  # serializa o pedido em JSON e termina com '\n'
        self.arquivo.flush()  # envia de fato os bytes pelo socket
        linha = self.arquivo.readline()  # bloqueia até chegar a linha de resposta
        if not linha:  # string vazia: o servidor fechou a conexão
            raise ConnectionError("O servidor encerrou a conexão")  # avisa quem chamou
        resposta = json.loads(linha)  # converte a resposta JSON em dicionário
        if not resposta["ok"]:  # o servidor sinalizou erro
            raise ErroRemoto(resposta["erro"])  # transforma em exceção no cliente
        return resposta["resultado"]  # devolve só o número calculado

    def operacao(self, op, a, b):  # chamada de uma operação básica
        return self.requisitar({"op": op, "a": a, "b": b})  # monta o JSON {"op", "a", "b"} e envia

    def expressao(self, expr):  # Modo B: manda a expressão inteira
        return self.requisitar({"op": "expressao", "expr": expr})  # o servidor faz todo o cálculo

    def fechar(self):  # encerra a sessão
        self.arquivo.close()  # fecha o arquivo associado ao socket
        self.sock.close()  # fecha a conexão TCP (FIN)


def executor_remoto(cliente):  # cria o executor do Modo A, ligado a esta conexão
    def executar(op, a, b):  # chamado pelo parser para cada operação básica
        resultado = cliente.operacao(op, a, b)  # uma ida e volta ao servidor por operação
        print(f"  → servidor: {op}({formatar(a)}, {formatar(b)}) = {formatar(resultado)}")  # mostra cada chamada remota
        return resultado  # devolve o valor para o parser continuar
    return executar  # o parser recebe essa função como executor


MENU = """
=== Calculadora Socket ===
1) Operação simples (ex: 10 + 15)
2) Expressão – Modo A (cliente decompõe e chama o servidor por operação)
3) Expressão – Modo B (servidor calcula a expressão inteira)
0) Sair"""  # texto do menu


def main():  # ponto de entrada do cliente
    parser = argparse.ArgumentParser(description="Cliente da calculadora via Socket TCP")  # define os argumentos
    parser.add_argument("--host", default="localhost", help="endereço do servidor")  # host padrão
    parser.add_argument("--porta", type=int, default=5000, help="porta do servidor (padrão 5000)")  # porta padrão
    args = parser.parse_args()  # lê os argumentos digitados

    try:  # o servidor pode não estar no ar
        cliente = ClienteSocket(args.host, args.porta)  # conecta uma única vez
    except OSError as e:  # conexão recusada, host inexistente etc.
        print(f"Não foi possível conectar em {args.host}:{args.porta}: {e}")  # explica o problema
        return  # encerra sem traceback

    print(f"Conectado a {args.host}:{args.porta}")  # confirma a conexão
    try:  # garante o fechamento da conexão no final
        while True:  # repete o menu até o usuário sair
            print(MENU)  # mostra as opções
            opcao = input("Escolha: ").strip()  # lê a opção digitada
            if opcao == "0":  # sair
                break  # sai do laço
            if opcao not in ("1", "2", "3"):  # opção inexistente
                print("Opção inválida.")  # avisa e mostra o menu de novo
                continue  # volta ao início do laço
            texto = input("Digite: ").strip()  # lê a operação ou expressão
            try:  # erros de entrada ou do servidor não encerram o programa
                if opcao == "1":  # operação simples
                    op, a, b = analisar_operacao_simples(texto)  # extrai operação e operandos
                    resultado = cliente.operacao(op, a, b)  # uma única requisição
                    print(f"{formatar(a)} {SIMBOLOS[op]} {formatar(b)} = {formatar(resultado)}")  # mostra o resultado
                elif opcao == "2":  # Modo A
                    resultado = avaliar(texto, executor_remoto(cliente))  # parser local + chamadas remotas
                    print(f"Resultado final: {formatar(resultado)}")  # mostra o resultado
                else:  # Modo B
                    resultado = cliente.expressao(texto)  # uma requisição com a expressão inteira
                    print(f"Resultado (calculado no servidor): {formatar(resultado)}")  # mostra o resultado
            except ErroExpressao as e:  # o parser local recusou a entrada
                print(f"Entrada inválida: {e}")  # explica o erro
            except ErroRemoto as e:  # o servidor respondeu com erro
                print(f"Erro do servidor: {e}")  # mostra a mensagem do servidor
    except (KeyboardInterrupt, EOFError):  # Ctrl+C ou fim da entrada
        print()  # pula linha antes de sair
    except (ConnectionError, OSError) as e:  # a conexão caiu no meio da sessão
        print(f"Conexão perdida: {e}")  # avisa o usuário
    finally:  # sempre executa
        cliente.fechar()  # fecha a conexão TCP
        print("Até logo!")  # despedida


if __name__ == "__main__":  # só executa main() quando o arquivo é rodado diretamente
    main()  # inicia o cliente
