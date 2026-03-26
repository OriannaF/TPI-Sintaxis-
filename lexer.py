import re
from dataclasses import dataclass

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
    ("FECHA",        r"(?:0?[1-9]|[12]\d|3[01])/(?:0?[1-9]|1[0-2])/(?:19\d{2}|20\d{2})"),
    ("EMAIL",        r"[A-Za-z0-9._+\-]+@[A-Za-z0-9._+\-]+\.[A-Za-z]{2,4}"),
    ("TEXTO",        r'"[^"\n]*"|“[^”\n]*”'),

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

    ("ID",           r"[A-Za-z_][A-Za-z0-9_]*"),
]

MASTER_REGEX = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_REGEX),
    re.IGNORECASE
)

def lexer(codigo):
    tokens = []
    linea = 1
    inicio_linea = 0
    pos = 0

    while pos < len(codigo):
        match = MASTER_REGEX.match(codigo, pos)

        if not match:
            columna = pos - inicio_linea + 1
            raise SyntaxError(
                f"Error léxico en línea {linea}, columna {columna}: símbolo no permitido '{codigo[pos]}'"
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
            # normalizar keywords/booleanos a mayúsculas
            if tipo in {
                "WHEN", "IF", "THEN", "ELSE", "DO", "END",
                "EVERY", "AND", "OR", "NOT", "BOOLEANO"
            }:
                valor = valor.upper()

            tokens.append(Token(tipo, valor, linea, columna))

        pos = match.end()

    return tokens


if __name__ == "__main__":
    codigo = """
// comentario
WHEN sensor_luz < 250lux DO
foco_entrada.estado = ON
foco_entrada.brillo = 80%
END
"""

    try:
        resultado = lexer(codigo)
        for token in resultado:
            print(token)
    except SyntaxError as e:
        print(e)