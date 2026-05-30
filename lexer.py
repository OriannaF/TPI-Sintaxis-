import re
from dataclasses import dataclass
import tkinter as tk
from tkinter import filedialog


@dataclass
class Token:
    tipo: str
    valor: str
    linea: int
    columna: int


TOKEN_REGEX = [
    ("COMMENT",      r"//[^\n]*"),
    ("NEWLINE",      r"\n"),
    ("SKIP",         r"[ \t\r]+"),

    ("EQ",           r"=="),
    ("NEQ",          r"!="),
    ("GE",           r">="),
    ("LE",           r"<="),

    ("GT",           r">"),
    ("LT",           r"<"),
    ("ASSIGN",       r"="),
    ("DOT",          r"\."),

    ("TEMPERATURA",  r"-?\d+(?:\.\d+)?°C"),
    ("PORCENTAJE",   r"\d+(?:\.\d+)?%"),
    ("ILUMINANCIA",  r"\d+(?:\.\d+)?lux"),
    ("TIEMPO",       r"\d+(?:\.\d+)?[smh]"),
    ("HORA",         r"(?:[01]\d|2[0-3]):[0-5]\d"),
    ("FECHA",        r"(?:(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])/(?:19\d{2}|20\d{2}))|(?:(?:19\d{2}|20\d{2})-(?:0?[1-9]|1[0-2])-(?:0?[1-9]|[12]\d|3[01]))"),
    ("EMAIL",        r"[A-Za-z0-9._+\-]+@[A-Za-z0-9._+\-]+\.[A-Za-z]{2,4}"),
    ("TEXTO",        r'"[^"\n]*"|\'[^\'\n]*\''),

    ("WHEN",         r"\bWHEN\b"),
    ("IF",           r"\bIF\b"),
    ("THEN",         r"\bTHEN\b"),
    ("ELSE",         r"\bELSE\b"),
    ("DO",           r"\bDO\b"),
    ("END",          r"\bEND\b"),
    ("EVERY",        r"\bEVERY\b"),
    ("AND",          r"\bAND\b"),
    ("OR",           r"\bOR\b"),
    ("NOT",          r"\bNOT\b"),

    ("BOOLEANO",     r"\b(?:TRUE|FALSE|ON|OFF)\b"),
    ("MODO_AIRE",    r"\b(?:FRIO|CALOR|VENT)\b"),
    ("VALOR_COLOR",  r"\b(?:blanco|rojo|azul)\b"),

    ("FOCO_ID",               r"\bfoco_[A-Za-z0-9_]+\b"),
    ("AIRE_ID",               r"\baire_[A-Za-z0-9_]+\b"),
    ("PERSIANA_ID",           r"\bpersiana_[A-Za-z0-9_]+\b"),
    ("CERRADURA_ID",          r"\bcerradura_[A-Za-z0-9_]+\b"),
    ("ALTAVOZ_ID",            r"\baltavoz_[A-Za-z0-9_]+\b"),
    ("ALARMA_ID",             r"\balarma(?:_[A-Za-z0-9_]+)?\b"),
    ("SENSOR_TEMPERATURA_ID", r"\bsensor_t(?:emperatura|emp)(?:_[A-Za-z0-9_]+)?\b"),
    ("SENSOR_HUMEDAD_ID",     r"\bsensor_humedad(?:_[A-Za-z0-9_]+)?\b"),
    ("SENSOR_LUZ_ID",         r"\bsensor_luz(?:_[A-Za-z0-9_]+)?\b"),
    ("SENSOR_MOVIMIENTO_ID",  r"\bsensor_movimiento(?:_[A-Za-z0-9_]+)?\b"),
    ("SENSOR_HUMO_ID",        r"\bsensor_humo(?:_[A-Za-z0-9_]+)?\b"),
    ("RELOJ_ID",              r"\breloj(?:_[A-Za-z0-9_]+)?\b"),

    ("ATRIBUTO",     r"\b(?:estado|brillo|color|modo|temp_obj|temp_objetivo|temp_act|posicion|volumen|mute|mensaje|email_notif|email|activada|hora|fecha)\b"),

    ("ID",           r"[A-Za-z_][A-Za-z0-9_]*"),
]

MASTER_REGEX = re.compile(
    "|".join(f"(?P<{nombre}>{patron})" for nombre, patron in TOKEN_REGEX),
    re.IGNORECASE
)


def leer_archivo(ruta_archivo: str) -> str:
    if not ruta_archivo.endswith(".smart"):
        raise ValueError("Error de ejecución: el archivo debe tener extensión .smart")

    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            return archivo.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Error de ejecución: no existe el archivo '{ruta_archivo}'")


def lexer(codigo: str) -> list[Token]:
    tokens = []
    linea = 1
    inicio_linea = 0
    pos = 0

    while pos < len(codigo):
        match = MASTER_REGEX.match(codigo, pos)

        if not match:
            columna = pos - inicio_linea + 1

            fin = pos
            while fin < len(codigo) and codigo[fin] not in " \t\r\n":
                fin += 1

            cadena_error = codigo[pos:fin]

            raise SyntaxError(
                f"Error léxico en línea {linea}, columna {columna}: cadena no válida '{cadena_error}'"
            )

        tipo = match.lastgroup
        valor = match.group(tipo)
        columna = pos - inicio_linea + 1

        if tipo == "NEWLINE":
            linea += 1
            inicio_linea = match.end()

        elif tipo in ("SKIP", "COMMENT"):
            pass

        else:
            if tipo in {
                "WHEN", "IF", "THEN", "ELSE", "DO", "END",
                "EVERY", "AND", "OR", "NOT", "BOOLEANO",
                "MODO_AIRE", "VALOR_COLOR",
            }:
                valor = valor.upper()
            elif tipo == "ATRIBUTO":
                valor = valor.lower()

            tokens.append(Token(tipo, valor, linea, columna))

        pos = match.end()

    return tokens


def imprimir_tokens(tokens: list[Token]) -> None:
    print(f"{'TIPO':<15} {'VALOR':<30} {'LINEA':<8} {'COLUMNA':<8}")
    print("-" * 65)
    for token in tokens:
        print(f"{token.tipo:<15} {token.valor:<30} {token.linea:<8} {token.columna:<8}")


def seleccionar_archivo():
    root = tk.Tk()
    root.withdraw()

    archivo = filedialog.askopenfilename(
        title="Seleccionar archivo .smart",
        filetypes=[("Archivos SMART", "*.smart")]
    )
    return archivo


def modo_archivo():
    try:
        ruta_archivo = seleccionar_archivo()

        if not ruta_archivo:
            print("No se seleccionó ningún archivo.")
            return

        codigo = leer_archivo(ruta_archivo)
        tokens = lexer(codigo)

        imprimir_tokens(tokens)
        print("\nAnálisis léxico exitoso.")

    except (ValueError, FileNotFoundError, SyntaxError) as e:
        print(e)


def modo_interactivo():
    print("Modo interactivo del lexer.")
    print("Escribí una línea para analizarla.")
    print("Escribí 'salir' para terminar.\n")

    while True:
        entrada = input("smart> ")

        if entrada.strip().lower() == "salir":
            print("Saliendo del modo interactivo.")
            break

        try:
            tokens = lexer(entrada)
            imprimir_tokens(tokens)
            print()
        except SyntaxError as e:
            print(e)
            print()


def main():
    print("Seleccione modo de ejecución:")
    print("1. Analizar archivo .smart")
    print("2. Modo interactivo")

    opcion = input("Opción: ").strip()

    if opcion == "1":
        modo_archivo()
    elif opcion == "2":
        modo_interactivo()
    else:
        print("Opción no válida.")


if __name__ == "__main__":
    main()