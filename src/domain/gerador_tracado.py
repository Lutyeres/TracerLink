import math
import matplotlib.pyplot as plt
from pathlib import Path

from src.config import settings


class GeradorTracado:

    def __init__(self, nome_arquivo):

        settings.carregar_config()

        pasta = Path(settings.get_pasta())
        ext = settings.get_ext()

        if not nome_arquivo.endswith(f".{ext}"):
            nome_arquivo = f"{nome_arquivo}.{ext}"

        self.caminho = pasta / nome_arquivo

        if not self.caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.caminho}")

    # -----------------------------------------------------

    def _extrair_blocos(self):

        r_values = []
        l_values = []

        lendo_r = False
        lendo_l = False

        with open(self.caminho, "r", encoding="utf-8") as f:

            for linha in f:

                linha = linha.strip()

                if linha.startswith("TRCFMT"):

                    if ";R;" in linha:
                        lendo_r = True
                        lendo_l = False
                        continue

                    if ";L;" in linha:
                        lendo_l = True
                        lendo_r = False
                        continue

                if linha.startswith("R="):

                    valores = linha[2:].split(";")
                    numeros = [float(v) /100 for v in valores if v]

                    if lendo_r:
                        r_values.extend(numeros)

                    elif lendo_l:
                        l_values.extend(numeros)

        if not r_values and not l_values:
            raise Exception("Nenhum dado de traçado encontrado.")

        return r_values, l_values

    # -----------------------------------------------------

    def _polar_para_cartesiano(self, valores):

        x = []
        y = []

        total = len(valores)

        for i, r in enumerate(valores):

            angulo = 2 * math.pi * i / total

            x.append(r * math.cos(angulo))
            y.append(r * math.sin(angulo))

        return x, y

    # -----------------------------------------------------

    def _extrair_parametros(self):

        hbox_r = hbox_l = None
        vbox_r = vbox_l = None
        dbl = 0

        with open(self.caminho, "r", encoding="utf-8") as f:

            for linha in f:

                linha = linha.strip()

                if linha.startswith("HBOX="):

                    valores = linha.split("=")[1].split(";")
                    hbox_r = float(valores[0])
                    hbox_l = float(valores[1])

                elif linha.startswith("VBOX="):

                    valores = linha.split("=")[1].split(";")
                    vbox_r = float(valores[0])
                    vbox_l = float(valores[1])

                elif linha.startswith("DBL="):

                    dbl = float(linha.split("=")[1])
                    print(dbl)

        if hbox_r is None or hbox_l is None:
            raise Exception("HBOX não encontrado no arquivo")

        return hbox_r, hbox_l, dbl

    def visualizar(self):
        r_values, l_values = self._extrair_blocos()
        hbox_r, hbox_l, dbl = self._extrair_parametros()

        plt.figure(figsize=(14, 7))

        # 1. Normalização: Garantir que cada lente comece centrada em seu próprio eixo local
        # (Isso corrige se os dados brutos vierem com algum deslocamento estranho)

        if r_values:
            x_r, y_r = self._polar_para_cartesiano(l_values)
            # Centraliza a lente na origem (0,0) antes de mover
            x_r = [v - (min(x_r) + max(x_r)) / 2 for v in x_r]

            # Desloca para a direita: metade da largura da lente + metade da ponte
            distancia_centro_r = (hbox_r / 2) + (dbl / 2)
            x_r = [v + distancia_centro_r for v in x_r]
            plt.plot(x_r, y_r, label=f"Direita (HBOX={hbox_r})")

        if l_values:
            x_l, y_l = self._polar_para_cartesiano(r_values)
            # Centraliza a lente na origem (0,0) antes de mover
            x_l = [v - (min(x_l) + max(x_l)) / 2 for v in x_l]

            # Desloca para a esquerda: (metade da largura da lente + metade da ponte) negativo
            distancia_centro_l = -((hbox_l / 2) + (dbl / 2))
            x_l = [v + distancia_centro_l for v in x_l]
            plt.plot(x_l, y_l, label=f"Esquerda (HBOX={hbox_l})")

        # Ajustes de exibição para ver a separação
        plt.gca().set_aspect("equal")
        plt.axvline(0, color='red', linestyle='--', label="Eixo Central (Ponte)")

        # Desenha linhas guias para a ponte (DBL)
        plt.axvline(dbl / 2, color='gray', linestyle=':', alpha=0.5)
        plt.axvline(-dbl / 2, color='gray', linestyle=':', alpha=0.5)

        plt.legend()
        plt.grid(True, which='both', linestyle='-', alpha=0.2)
        plt.title(f"Visualização Óptica - DBL: {dbl}")
        plt.show()