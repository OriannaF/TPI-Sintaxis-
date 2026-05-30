from lexer import lexer, leer_archivo, Token
import tkinter as tk
from tkinter import filedialog
from html import escape
import os


class ParserError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token], source_path: str):
        self.tokens = tokens
        self.pos = 0
        self.source_path = source_path

        # datos para traducción HTML
        self.sensores = {}   # nombre -> set de descripciones
        self.actuadores = {} # nombre -> {atributo: valor}

    # =========================
    # Utilidades básicas parser
    # =========================
    def actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def coincide(self, *tipos):
        token = self.actual()
        return token is not None and token.tipo in tipos

    def consumir(self, *tipos_esperados):
        token = self.actual()

        if token is None:
            raise ParserError(
                f"Error sintáctico: se esperaba '{tipos_esperados[0] if len(tipos_esperados) == 1 else tipos_esperados}' "
                f"pero se llegó al fin del archivo."
            )

        if token.tipo in tipos_esperados:
            self.pos += 1
            return token

        raise ParserError(
            f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
            f"se esperaba '{tipos_esperados[0] if len(tipos_esperados) == 1 else tipos_esperados}' "
            f"y se encontró '{token.valor}'"
        )

    # =========================
    # Parse principal
    # =========================
    def parse(self):
        self.programa()

        if self.actual() is not None:
            token = self.actual()
            raise ParserError(
                f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                f"token inesperado '{token.valor}' al final del archivo"
            )

    def programa(self):
        self.lista_sentencias()

    def lista_sentencias(self):
        self.sentencia()

        while self.coincide("WHEN", "EVERY", "IF", "ID",
                            "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
                            "ALTAVOZ_ID", "ALARMA_ID",
                            "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
                            "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
                            "RELOJ_ID"):
            self.sentencia()

    def sentencia(self):
        if self.coincide("WHEN"):
            self.when_stmt()
        elif self.coincide("EVERY"):
            self.every_stmt()
        elif self.coincide("IF"):
            self.if_stmt()
        elif self.coincide("ID", "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
                             "ALTAVOZ_ID", "ALARMA_ID",
                             "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
                             "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
                             "RELOJ_ID"):
            token_actual = self.actual()

            # mirar si parece realmente una asignación: ID . ID = ...
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tipo == "DOT":
                self.asignacion()
            else:
                raise ParserError(
                    f"Error sintáctico en línea {token_actual.linea}, columna {token_actual.columna}: "
                    f"sentencia no válida '{token_actual.valor}'. "
                )
        else:
            token = self.actual()
            if token is None:
                raise ParserError("Error sintáctico: fin de archivo inesperado.")
            raise ParserError(
                f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                f"sentencia no válida cerca de '{token.valor}'"
            )

    def when_stmt(self):
        self.consumir("WHEN")
        self.condicion()
        self.consumir("DO")
        self.bloque()
        self.consumir("END")

    def every_stmt(self):
        self.consumir("EVERY")
        self.tiempo()
        self.consumir("DO")
        self.bloque()
        self.consumir("END")

    def if_stmt(self):
        self.consumir("IF")
        self.condicion()
        self.consumir("THEN")
        self.bloque()

        if self.coincide("ELSE"):
            self.consumir("ELSE")
            self.bloque()

        self.consumir("END")

    def asignacion(self):
        dispositivo = self.identificador()
        self.consumir("DOT")
        atributo = self.atributo()
        self.consumir("ASSIGN")
        valor = self.valor()

        self.registrar_actuador(dispositivo.valor, atributo.valor, valor["texto"], valor["tipo"])

    def bloque(self):
        self.sentencia()

        while self.coincide("WHEN", "EVERY", "IF", "ID",
                            "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
                            "ALTAVOZ_ID", "ALARMA_ID",
                            "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
                            "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
                            "RELOJ_ID"):
            self.sentencia()

    # =========================
    # Condiciones
    # =========================
    def condicion(self):
        self.expresion_or()

    def expresion_or(self):
        self.expresion_and()
        while self.coincide("OR"):
            self.consumir("OR")
            self.expresion_and()

    def expresion_and(self):
        self.expresion_not()
        while self.coincide("AND"):
            self.consumir("AND")
            self.expresion_not()

    def expresion_not(self):
        if self.coincide("NOT"):
            self.consumir("NOT")
            self.expresion_not()
        else:
            self.primaria_condicion()

    def primaria_condicion(self):
        if self.coincide("BOOLEANO"):
            self.consumir("BOOLEANO")
        else:
            self.comparacion()

    def comparacion(self):
        ref = self.referencia()
        op = self.operador()
        val = self.valor()

        self.registrar_sensor(ref["texto"], op.valor, val["texto"], val["tipo"])

    # =========================
    # Componentes
    # =========================
    def referencia(self):
        primer_id = self.identificador()

        if self.coincide("DOT"):
            self.consumir("DOT")
            segundo_id = self.atributo()
            return {
                "texto": f"{primer_id.valor}.{segundo_id.valor}",
                "base": primer_id.valor,
                "atributo": segundo_id.valor,
            }

        return {
            "texto": primer_id.valor,
            "base": primer_id.valor,
            "atributo": None,
        }

    def operador(self):
        if self.coincide("EQ"):
            return self.consumir("EQ")
        elif self.coincide("NEQ"):
            return self.consumir("NEQ")
        elif self.coincide("GT"):
            return self.consumir("GT")
        elif self.coincide("LT"):
            return self.consumir("LT")
        elif self.coincide("GE"):
            return self.consumir("GE")
        elif self.coincide("LE"):
            return self.consumir("LE")

        token = self.actual()
        if token is None:
            raise ParserError("Error sintáctico: se esperaba un operador y se llegó al fin del archivo.")
        raise ParserError(
            f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
            f"se esperaba un operador de comparación y se encontró '{token.valor}'"
        )

    def valor(self):
        token = self.actual()

        tipos_validos = {
            "BOOLEANO",
            "PORCENTAJE",
            "TEMPERATURA",
            "TIEMPO",
            "TEXTO",
            "HORA",
            "FECHA",
            "EMAIL",
            "ILUMINANCIA",
            "ID",
            "MODO_AIRE",
            "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
            "ALTAVOZ_ID", "ALARMA_ID",
            "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
            "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
            "RELOJ_ID",
        }

        if token is None:
            raise ParserError("Error sintáctico: se esperaba un valor y se llegó al fin del archivo.")

        if token.tipo not in tipos_validos:
            raise ParserError(
                f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                f"se esperaba un valor y se encontró '{token.valor}'"
            )

        self.pos += 1
        return {
            "tipo": token.tipo,
            "texto": token.valor,
        }

    def identificador(self):
        return self.consumir("ID", "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
                             "ALTAVOZ_ID", "ALARMA_ID",
                             "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
                             "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
                             "RELOJ_ID")

    def atributo(self):
        return self.consumir("ATRIBUTO", "ID")

    def tiempo(self):
        return self.consumir("TIEMPO")

    # =========================
    # Recolección de datos HTML
    # =========================
    def es_sensor(self, referencia: str) -> bool:
        base = referencia.split(".")[0].lower()
        return base.startswith("sensor_") or base == "reloj"

    def registrar_sensor(self, referencia: str, operador: str, valor: str, tipo_valor: str):
        # Solo registramos como sensor si parece sensor/reloj
        if not self.es_sensor(referencia):
            return

        descripcion = f"{referencia} {operador} {valor}"

        if referencia not in self.sensores:
            self.sensores[referencia] = []

        if descripcion not in self.sensores[referencia]:
            self.sensores[referencia].append(descripcion)

    def registrar_actuador(self, dispositivo: str, atributo: str, valor: str, tipo_valor: str):
        if dispositivo not in self.actuadores:
            self.actuadores[dispositivo] = {}

        self.actuadores[dispositivo][atributo] = {
            "valor": valor,
            "tipo": tipo_valor
        }

    # =========================
    # Traducción a HTML
    # =========================
    def limpiar_texto(self, texto: str) -> str:
        if len(texto) >= 2:
            if (texto.startswith('"') and texto.endswith('"')) or (texto.startswith("“") and texto.endswith("”")):
                return texto[1:-1]
        return texto

    def mailto_html(self, email: str) -> str:
        username = email.split("@")[0]
        return f'<a href="mailto:{escape(email)}">Contactar a {escape(username)}</a>'

    def generar_html(self) -> str:
        partes = []

        partes.append("<!DOCTYPE html>")
        partes.append("<html lang='es'>")
        partes.append("<head>")
        partes.append("  <meta charset='UTF-8'>")
        partes.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        partes.append("  <title>Smart Home</title>")
        partes.append("  <style>")
        partes.append("    body { font-family: Arial, sans-serif; margin: 20px; background: #f7f7f7; }")
        partes.append("    .sensores { border: 1px solid green; padding: 20px; margin-bottom: 20px; background: #ffffff; }")
        partes.append("    .actuador { border: 1px solid gray; padding: 20px; margin-bottom: 20px; background: #ffffff; }")
        partes.append("    h1, h2 { margin-top: 0; }")
        partes.append("    ul { margin: 0; padding-left: 22px; }")
        partes.append("    li { margin-bottom: 6px; }")
        partes.append("  </style>")
        partes.append("</head>")
        partes.append("<body>")
        partes.append("  <h1>Smart Home</h1>")

        # Sensores
        partes.append("  <div class='sensores'>")
        partes.append("    <h1>Sensores</h1>")

        if self.sensores:
            for sensor in sorted(self.sensores.keys()):
                partes.append(f"    <h2>{escape(sensor)}</h2>")
                partes.append("    <ul>")
                for descripcion in self.sensores[sensor]:
                    partes.append(f"      <li>{escape(descripcion)}</li>")
                partes.append("    </ul>")
        else:
            partes.append("    <p>No se detectaron sensores en las condiciones.</p>")

        partes.append("  </div>")

        # Actuadores
        if self.actuadores:
            for actuador in sorted(self.actuadores.keys()):
                partes.append("  <div class='actuador'>")
                partes.append(f"    <h1>{escape(actuador)}</h1>")
                partes.append("    <ul>")

                for atributo in sorted(self.actuadores[actuador].keys()):
                    dato = self.actuadores[actuador][atributo]
                    valor = self.limpiar_texto(dato['valor'])

                    if dato["tipo"] == "EMAIL":
                        contenido = self.mailto_html(valor)
                        partes.append(f"      <li>{escape(atributo)}: {contenido}</li>")
                    else:
                        partes.append(f"      <li>{escape(atributo)}: {escape(valor)}</li>")

                partes.append("    </ul>")
                partes.append("  </div>")
        else:
            partes.append("  <div class='actuador'>")
            partes.append("    <h1>Actuadores</h1>")
            partes.append("    <p>No se detectaron asignaciones a actuadores.</p>")
            partes.append("  </div>")

        partes.append("</body>")
        partes.append("</html>")

        return "\n".join(partes)

    def guardar_html(self):
        html = self.generar_html()
        salida = os.path.splitext(self.source_path)[0] + ".html"

        with open(salida, "w", encoding="utf-8") as archivo:
            archivo.write(html)

        return salida


def seleccionar_archivo():
    root = tk.Tk()
    root.withdraw()

    archivo = filedialog.askopenfilename(
        title="Seleccionar archivo .smart",
        filetypes=[("Archivos SMART", "*.smart")]
    )
    return archivo


def main():
    try:
        ruta_archivo = seleccionar_archivo()

        if not ruta_archivo:
            print("No se seleccionó ningún archivo.")
            return

        codigo = leer_archivo(ruta_archivo)
        tokens = lexer(codigo)

        parser = Parser(tokens, ruta_archivo)
        parser.parse()
        ruta_html = parser.guardar_html()

        print("Análisis sintáctico exitoso: archivo correctamente construido.")
        print(f"Traducción HTML generada en: {ruta_html}")

    except (ValueError, FileNotFoundError, SyntaxError, ParserError) as e:
        print(e)


if __name__ == "__main__":
    main()