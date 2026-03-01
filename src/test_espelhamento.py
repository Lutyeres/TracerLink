from pathlib import Path
from src.domain.job import Job


def main():

    # Caminho do arquivo que você quer testar
    arquivo_entrada = Path("teste_original.txt")

    if not arquivo_entrada.exists():
        print("Arquivo não encontrado:", arquivo_entrada)
        return

    print("Lendo arquivo:", arquivo_entrada)

    content = arquivo_entrada.read_text(encoding="utf-8")

    job = Job()

    print("Executando regra de espelhamento...\n")

    novo_conteudo = job._ensure_complete_file(content)

    arquivo_saida = Path("teste_espelhado.txt")
    arquivo_saida.write_text(novo_conteudo, encoding="utf-8")

    print("Arquivo espelhado salvo em:", arquivo_saida)
    print("Teste concluído.")


if __name__ == "__main__":
    main()