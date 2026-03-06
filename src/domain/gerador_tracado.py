import math
from pathlib import Path
import matplotlib.pyplot as plt

from src.config.config import get_pasta


class GeradorTracado:

    def __init__(self, nome_arquivo):

        pasta = Path(get_pasta())

        if not pasta.exists():
            raise FileNotFoundError(f"Pasta configurada não encontrada: {pasta}")

        self.arquivo = pasta / nome_arquivo

        if not self.arquivo.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.arquivo}")

        self.valores_r = []

    # ======================================================
    # LEITURA DO ARQUIVO
    # ======================================================

    def carregar(self):

        valores = []

        with open(self.arquivo, "r", encoding="utf-8") as f:

            for line in f:

                if line.startswith("R="):

                    numeros = line[2:].split(";")

                    for n in numeros:

                        n = n.strip()

                        if n:
                            valores.append(float(n))

        if len(valores) < 800:
            raise ValueError(
                f"Arquivo inválido. Esperado 800 pontos, encontrado {len(valores)}"
            )

        self.valores_r = valores[:800]

    # ======================================================
    # POLAR → CARTESIANO
    # ======================================================

    def gerar_xy(self):

        x = []
        y = []

        total = len(self.valores_r)

        for i, r in enumerate(self.valores_r):

            angle = 2 * math.pi * i / total

            x.append(r * math.cos(angle))
            y.append(r * math.sin(angle))

        return x, y

    # ======================================================
    # PLOT
    # ======================================================

    def plotar(self):

        x, y = self.gerar_xy()

        plt.figure(f"Traçado - {self.arquivo.name}")

        plt.plot(x, y)

        plt.gca().set_aspect("equal", adjustable="box")

        plt.title("Formato da Lente")
        plt.xlabel("X")
        plt.ylabel("Y")

        plt.grid(True)

        plt.show()

    # ======================================================
    # EXECUÇÃO COMPLETA
    # ======================================================

    def visualizar(self):

        self.carregar()
        self.plotar()