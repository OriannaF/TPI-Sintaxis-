from lexer import lexer, leer_archivo, Token
import tkinter as tk
from tkinter import filedialog
from html import escape
import os


class ParserError(Exception):
    pass


# ============================================================
# AST Node Classes
# ============================================================

class ASTNode:
    pass


class Program(ASTNode):
    __slots__ = ('statements',)
    def __init__(self, statements: list):
        self.statements = statements


class WhenStmt(ASTNode):
    __slots__ = ('condition', 'body')
    def __init__(self, condition, body: list):
        self.condition = condition
        self.body = body


class EveryStmt(ASTNode):
    __slots__ = ('tiempo', 'body')
    def __init__(self, tiempo, body: list):
        self.tiempo = tiempo
        self.body = body


class IfStmt(ASTNode):
    __slots__ = ('condition', 'then_body', 'else_body')
    def __init__(self, condition, then_body: list, else_body: list = None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body


class AssignStmt(ASTNode):
    __slots__ = ('device', 'attribute', 'value', 'device_tipo')
    def __init__(self, device: str, attribute: str, value, device_tipo: str):
        self.device = device
        self.attribute = attribute
        self.value = value
        self.device_tipo = device_tipo


class BinaryOp(ASTNode):
    __slots__ = ('operator', 'left', 'right')
    def __init__(self, operator: str, left, right):
        self.operator = operator
        self.left = left
        self.right = right


class UnaryOp(ASTNode):
    __slots__ = ('operator', 'operand')
    def __init__(self, operator: str, operand):
        self.operator = operator
        self.operand = operand


class Comparison(ASTNode):
    __slots__ = ('left', 'operator', 'right', 'device_tipo')
    def __init__(self, left, operator: str, right, device_tipo: str = None):
        self.left = left
        self.operator = operator
        self.right = right
        self.device_tipo = device_tipo


class Reference(ASTNode):
    __slots__ = ('base', 'attribute')
    def __init__(self, base: str, attribute: str = None):
        self.base = base
        self.attribute = attribute


class Literal(ASTNode):
    __slots__ = ('tipo', 'valor')
    def __init__(self, tipo: str, valor: str):
        self.tipo = tipo
        self.valor = valor


# ============================================================
# Tablas de validación (gramática 4.4.7 y 4.4.14)
# ============================================================

ASIGNACIONES = {
    "FOCO_ID": {
        "estado": ("BOOLEANO",),
        "brillo": ("PORCENTAJE",),
        "color": ("VALOR_COLOR",),
    },
    "AIRE_ID": {
        "estado": ("BOOLEANO",),
        "modo": ("MODO_AIRE",),
        "temp_obj": ("TEMPERATURA",),
        "temp_objetivo": ("TEMPERATURA",),
    },
    "PERSIANA_ID": {
        "posicion": ("PORCENTAJE",),
    },
    "CERRADURA_ID": {
        "estado": ("BOOLEANO",),
    },
    "ALTAVOZ_ID": {
        "volumen": ("PORCENTAJE",),
        "mute": ("BOOLEANO",),
        "mensaje": ("TEXTO",),
        "email_notif": ("EMAIL",),
        "email": ("EMAIL",),
    },
    "ALARMA_ID": {
        "estado": ("BOOLEANO",),
        "activada": ("BOOLEANO",),
    },
}

COMPARACION_SENSORES = {
    "SENSOR_TEMPERATURA_ID": ("TEMPERATURA",),
    "SENSOR_HUMEDAD_ID": ("PORCENTAJE",),
    "SENSOR_LUZ_ID": ("ILUMINANCIA",),
    "SENSOR_MOVIMIENTO_ID": ("BOOLEANO",),
    "SENSOR_HUMO_ID": ("BOOLEANO",),
}

COMPARACION_ACTUADORES = {
    "FOCO_ID": {
        "estado": ("BOOLEANO",),
        "brillo": ("PORCENTAJE",),
        "color": ("VALOR_COLOR",),
    },
    "AIRE_ID": {
        "estado": ("BOOLEANO",),
        "modo": ("MODO_AIRE",),
        "temp_obj": ("TEMPERATURA",),
        "temp_act": ("TEMPERATURA",),
    },
    "PERSIANA_ID": {
        "posicion": ("PORCENTAJE",),
    },
    "CERRADURA_ID": {
        "estado": ("BOOLEANO",),
    },
    "ALTAVOZ_ID": {
        "volumen": ("PORCENTAJE",),
        "mute": ("BOOLEANO",),
    },
    "ALARMA_ID": {
        "estado": ("BOOLEANO",),
        "activada": ("BOOLEANO",),
    },
}

COMPARACION_RELOJ = {
    "hora": ("HORA",),
    "fecha": ("FECHA",),
}

FIRST_SENTENCIA = {
    "WHEN", "EVERY", "IF",
    "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
    "ALTAVOZ_ID", "ALARMA_ID",
    "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
    "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
    "RELOJ_ID",
}

TIPOS_DISPOSITIVO = {
    "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
    "ALTAVOZ_ID", "ALARMA_ID",
    "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
    "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
    "RELOJ_ID",
}


# ============================================================
# Parser
# ============================================================

class Parser:
    def __init__(self, tokens: list[Token], source_path: str):
        self.tokens = tokens
        self.pos = 0
        self.source_path = source_path
        self.ast = None
        self.sensores = {}
        self.actuadores = {}

    # -------- helpers de tokens --------

    def actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def coincide(self, *tipos):
        t = self.actual()
        return t is not None and t.tipo in tipos

    def consumir(self, *tipos_esperados):
        t = self.actual()
        if t is None:
            raise ParserError(
                f"Error sintáctico: se esperaba "
                f"'{tipos_esperados[0] if len(tipos_esperados) == 1 else tipos_esperados}' "
                "pero se llegó al fin del archivo."
            )
        if t.tipo in tipos_esperados:
            self.pos += 1
            return t
        raise ParserError(
            f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
            f"se esperaba "
            f"'{tipos_esperados[0] if len(tipos_esperados) == 1 else tipos_esperados}' "
            f"y se encontró '{t.valor}'"
        )

    # -------- entrada principal --------

    def parse(self) -> Program:
        ast = self.programa()
        if self.actual() is not None:
            t = self.actual()
            raise ParserError(
                f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
                f"token inesperado '{t.valor}' al final del archivo"
            )
        self.ast = ast
        return ast

    # ================================================================
    # Reglas de Producción (Sección 4.4)
    # ================================================================

    # 4.4.1: programa → lista_sentencias
    def programa(self) -> Program:
        stmts = self.lista_sentencias()
        return Program(stmts)

    # 4.4.2: lista_sentencias → sentencia { sentencia }
    def lista_sentencias(self) -> list:
        stmts = []
        stmts.append(self.sentencia())
        while self.coincide(*FIRST_SENTENCIA):
            stmts.append(self.sentencia())
        return stmts

    # 4.4.3: sentencia → when | every | if | asignacion
    def sentencia(self) -> ASTNode:
        t = self.actual()
        if t is None:
            raise ParserError("Error sintáctico: fin de archivo inesperado.")

        if self.coincide("WHEN"):
            return self.when_stmt()
        elif self.coincide("EVERY"):
            return self.every_stmt()
        elif self.coincide("IF"):
            return self.if_stmt()
        elif self.coincide(*TIPOS_DISPOSITIVO):
            if self._hay_dot():
                return self.asignacion()
            raise ParserError(
                f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
                f"'{t.valor}' no es una sentencia válida. "
                "Los identificadores deben usar notación de punto para asignación "
                "(ej: dispositivo.atributo = valor)"
            )
        else:
            raise ParserError(
                f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
                f"sentencia no válida cerca de '{t.valor}'"
            )

    def _hay_dot(self) -> bool:
        return self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].tipo == "DOT"

    # 4.4.4: when → WHEN condicion DO bloque END
    def when_stmt(self) -> WhenStmt:
        self.consumir("WHEN")
        cond = self.condicion()
        self.consumir("DO")
        body = self.bloque()
        self.consumir("END")
        return WhenStmt(cond, body)

    # 4.4.5: every → EVERY tiempo DO bloque END
    def every_stmt(self) -> EveryStmt:
        self.consumir("EVERY")
        t = self.tiempo()
        self.consumir("DO")
        body = self.bloque()
        self.consumir("END")
        return EveryStmt(t, body)

    # 4.4.6: if → IF condicion THEN bloque [ ELSE bloque ] END
    def if_stmt(self) -> IfStmt:
        self.consumir("IF")
        cond = self.condicion()
        self.consumir("THEN")
        then_body = self.bloque()
        else_body = None
        if self.coincide("ELSE"):
            self.consumir("ELSE")
            else_body = self.bloque()
        self.consumir("END")
        return IfStmt(cond, then_body, else_body)

    def asignacion(self) -> AssignStmt:
        device_token = self.actual()
        device_tipo = device_token.tipo

        if device_tipo not in ASIGNACIONES:
            raise ParserError(
                f"Error sintáctico en línea {device_token.linea}, columna {device_token.columna}: "
                f"'{device_token.valor}' no es un dispositivo asignable. "
                f"Dispositivos válidos: foco, aire, persiana, cerradura, altavoz, alarma."
            )

        self.pos += 1
        self.consumir("DOT")
        attr_token = self.atributo()
        self.consumir("ASSIGN")
        val = self.valor()

        atributos_permitidos = ASIGNACIONES[device_tipo]

        if attr_token.valor not in atributos_permitidos:
            raise ParserError(
                f"Error sintáctico en línea {attr_token.linea}, columna {attr_token.columna}: "
                f"el atributo '{attr_token.valor}' no es válido para '{device_token.valor}'. "
                f"Atributos permitidos: {', '.join(atributos_permitidos)}"
            )

        tipos_permitidos = atributos_permitidos[attr_token.valor]
        if val.tipo not in tipos_permitidos:
            raise ParserError(
                f"Error sintáctico en línea {device_token.linea}, columna {device_token.columna}: "
                f"el valor '{val.valor}' es de tipo '{val.tipo}', pero "
                f"'{device_token.valor}.{attr_token.valor}' requiere "
                f"{'/'.join(tipos_permitidos)}"
            )

        return AssignStmt(device_token.valor, attr_token.valor, val, device_tipo)

    # 4.4.8: bloque → sentencia { sentencia }
    def bloque(self) -> list:
        stmts = []
        stmts.append(self.sentencia())
        while self.coincide(*FIRST_SENTENCIA):
            stmts.append(self.sentencia())
        return stmts

    # -------- Condiciones (4.4.9 a 4.4.13) --------

    # 4.4.9: condicion → expresion_or
    def condicion(self):
        return self.expresion_or()

    # 4.4.10: expresion_or → expresion_and { OR expresion_and }
    def expresion_or(self):
        left = self.expresion_and()
        while self.coincide("OR"):
            self.consumir("OR")
            right = self.expresion_and()
            left = BinaryOp("OR", left, right)
        return left

    # 4.4.11: expresion_and → expresion_not { AND expresion_not }
    def expresion_and(self):
        left = self.expresion_not()
        while self.coincide("AND"):
            self.consumir("AND")
            right = self.expresion_not()
            left = BinaryOp("AND", left, right)
        return left

    # 4.4.12: expresion_not → NOT expresion_not | primaria_condicion
    def expresion_not(self):
        if self.coincide("NOT"):
            self.consumir("NOT")
            operand = self.expresion_not()
            return UnaryOp("NOT", operand)
        return self.primaria_condicion()

    # 4.4.13: primaria_condicion → BOOLEANO | comparacion
    def primaria_condicion(self):
        if self.coincide("BOOLEANO"):
            tok = self.consumir("BOOLEANO")
            return Literal(tok.tipo, tok.valor)
        return self.comparacion()

    # -------- Comparaciones (4.4.14) --------

    # 4.4.14: comparacion → comparacion_sensor | comparacion_reloj | comparacion_actuador
    def comparacion(self) -> Comparison:
        token = self.actual()
        if token is None:
            raise ParserError("Error sintáctico: se esperaba una condición y se llegó al fin del archivo.")

        if token.tipo in COMPARACION_SENSORES:
            id_tok = self.consumir(token.tipo)
            op_tok = self.operador()
            val = self.valor()
            tipos_esperados = COMPARACION_SENSORES[token.tipo]
            if val.tipo not in tipos_esperados:
                raise ParserError(
                    f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                    f"el sensor '{id_tok.valor}' requiere un valor de tipo "
                    f"{'/'.join(tipos_esperados)}, se obtuvo '{val.valor}' ({val.tipo})"
                )
            return Comparison(Reference(id_tok.valor), op_tok.valor, val, token.tipo)

        if token.tipo == "RELOJ_ID":
            id_tok = self.consumir("RELOJ_ID")
            if not self.coincide("DOT"):
                raise ParserError(
                    f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                    f"'{id_tok.valor}' en comparación requiere atributo con punto "
                    f"(ej: {id_tok.valor}.hora > 22:00)"
                )
            self.consumir("DOT")
            attr_token = self.atributo()

            if attr_token.valor not in COMPARACION_RELOJ:
                raise ParserError(
                    f"Error sintáctico en línea {attr_token.linea}, columna {attr_token.columna}: "
                    f"el atributo '{attr_token.valor}' no es válido para '{id_tok.valor}'. "
                    f"Atributos permitidos: hora, fecha"
                )

            op_tok = self.operador()
            val = self.valor()
            tipos_esperados = COMPARACION_RELOJ[attr_token.valor]
            if val.tipo not in tipos_esperados:
                raise ParserError(
                    f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                    f"'{id_tok.valor}.{attr_token.valor}' requiere valor de tipo "
                    f"{'/'.join(tipos_esperados)}, se obtuvo '{val.valor}' ({val.tipo})"
                )
            return Comparison(Reference(id_tok.valor, attr_token.valor), op_tok.valor, val, "RELOJ_ID")

        if token.tipo in COMPARACION_ACTUADORES:
            id_tok = self.consumir(token.tipo)
            if not self.coincide("DOT"):
                raise ParserError(
                    f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                    f"'{id_tok.valor}' en comparación requiere atributo con punto "
                    f"(ej: {id_tok.valor}.estado == ON)"
                )
            self.consumir("DOT")
            attr_token = self.atributo()

            atributos_permitidos = COMPARACION_ACTUADORES[token.tipo]
            if attr_token.valor not in atributos_permitidos:
                raise ParserError(
                    f"Error sintáctico en línea {attr_token.linea}, columna {attr_token.columna}: "
                    f"el atributo '{attr_token.valor}' no es válido para '{id_tok.valor}' "
                    f"en una comparación. Atributos permitidos: {', '.join(atributos_permitidos)}"
                )

            op_tok = self.operador()
            val = self.valor()
            tipos_esperados = atributos_permitidos[attr_token.valor]
            if val.tipo not in tipos_esperados:
                raise ParserError(
                    f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
                    f"'{id_tok.valor}.{attr_token.valor}' requiere valor de tipo "
                    f"{'/'.join(tipos_esperados)}, se obtuvo '{val.valor}' ({val.tipo})"
                )
            return Comparison(Reference(id_tok.valor, attr_token.valor), op_tok.valor, val, token.tipo)

        raise ParserError(
            f"Error sintáctico en línea {token.linea}, columna {token.columna}: "
            f"no se puede usar '{token.valor}' en una comparación. "
            f"Se esperaba un sensor, actuador o reloj."
        )

    # -------- Valor (4.4.14 cont) --------

    def valor(self) -> Literal:
        tipos_validos = {
            "BOOLEANO", "PORCENTAJE", "TEMPERATURA", "TIEMPO", "TEXTO",
            "HORA", "FECHA", "EMAIL", "ILUMINANCIA", "MODO_AIRE", "ID",
            "VALOR_COLOR",
        }
        t = self.actual()
        if t is None:
            raise ParserError(
                "Error sintáctico: se esperaba un valor y se llegó al fin del archivo."
            )
        if t.tipo not in tipos_validos:
            raise ParserError(
                f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
                f"se esperaba un valor y se encontró '{t.valor}'"
            )
        self.pos += 1
        return Literal(t.tipo, t.valor)

    # -------- Referencia --------

    def referencia(self) -> Reference:
        id_tok = self.identificador()
        if self.coincide("DOT"):
            self.consumir("DOT")
            attr_tok = self.atributo()
            return Reference(id_tok.valor, attr_tok.valor)
        return Reference(id_tok.valor)

    # -------- Operador --------

    def operador(self) -> Token:
        if self.coincide("EQ", "NEQ", "GT", "LT", "GE", "LE"):
            return self.consumir("EQ", "NEQ", "GT", "LT", "GE", "LE")
        t = self.actual()
        if t is None:
            raise ParserError(
                "Error sintáctico: se esperaba un operador y se llegó al fin del archivo."
            )
        raise ParserError(
            f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
            f"se esperaba un operador de comparación y se encontró '{t.valor}'"
        )

    # -------- Identificador --------

    def identificador(self) -> Token:
        return self.consumir(
            "FOCO_ID", "AIRE_ID", "PERSIANA_ID", "CERRADURA_ID",
            "ALTAVOZ_ID", "ALARMA_ID",
            "SENSOR_TEMPERATURA_ID", "SENSOR_HUMEDAD_ID",
            "SENSOR_LUZ_ID", "SENSOR_MOVIMIENTO_ID", "SENSOR_HUMO_ID",
            "RELOJ_ID",
        )

    # -------- Atributo --------

    def atributo(self) -> Token:
        return self.consumir("ATRIBUTO", "ID")

    # -------- Tiempo (4.4.15) --------

    def tiempo(self) -> Literal:
        if self.coincide("TIEMPO"):
            tok = self.consumir("TIEMPO")
            return Literal(tok.tipo, tok.valor)
        elif self.coincide("HORA"):
            tok = self.consumir("HORA")
            return Literal(tok.tipo, tok.valor)
        t = self.actual()
        if t is None:
            raise ParserError(
                "Error sintáctico: se esperaba una duración (ej: 30m, 1h) y "
                "se llegó al fin del archivo."
            )
        raise ParserError(
            f"Error sintáctico en línea {t.linea}, columna {t.columna}: "
            f"se esperaba una duración (ej: 30m, 1h) y se encontró '{t.valor}'"
        )

    # ================================================================
    # Recorrido del AST → HTML
    # ================================================================

    @staticmethod
    def es_sensor(referencia: str) -> bool:
        base = referencia.split(".")[0].lower()
        return base.startswith("sensor_") or base == "reloj"

    def _visitar_ast(self, node):
        if isinstance(node, Program):
            for stmt in node.statements:
                self._visitar_ast(stmt)

        elif isinstance(node, WhenStmt):
            self._visitar_ast(node.condition)
            for stmt in node.body:
                self._visitar_ast(stmt)

        elif isinstance(node, EveryStmt):
            for stmt in node.body:
                self._visitar_ast(stmt)

        elif isinstance(node, IfStmt):
            self._visitar_ast(node.condition)
            for stmt in node.then_body:
                self._visitar_ast(stmt)
            if node.else_body:
                for stmt in node.else_body:
                    self._visitar_ast(stmt)

        elif isinstance(node, AssignStmt):
            self.registrar_actuador(
                node.device, node.attribute,
                node.value.valor, node.value.tipo
            )

        elif isinstance(node, BinaryOp):
            self._visitar_ast(node.left)
            self._visitar_ast(node.right)

        elif isinstance(node, UnaryOp):
            self._visitar_ast(node.operand)

        elif isinstance(node, Comparison):
            self._registrar_sensor_comparacion(node)

    def _registrar_sensor_comparacion(self, node: Comparison):
        if isinstance(node.left, Reference):
            ref_parts = [node.left.base]
            if node.left.attribute:
                ref_parts.append(node.left.attribute)
            ref_str = ".".join(ref_parts)
            if self.es_sensor(ref_str):
                desc = f"{ref_str} {node.operator} {node.right.valor}"
                if ref_str not in self.sensores:
                    self.sensores[ref_str] = []
                if desc not in self.sensores[ref_str]:
                    self.sensores[ref_str].append(desc)

    def registrar_actuador(
        self, dispositivo: str, atributo: str,
        valor: str, tipo_valor: str
    ):
        if dispositivo not in self.actuadores:
            self.actuadores[dispositivo] = {}
        self.actuadores[dispositivo][atributo] = {
            "valor": valor,
            "tipo": tipo_valor
        }

    @staticmethod
    def limpiar_texto(texto: str) -> str:
        if len(texto) >= 2:
            if (texto.startswith('"') and texto.endswith('"')) or \
               (texto.startswith("'") and texto.endswith("'")):
                return texto[1:-1]
        return texto

    @staticmethod
    def mailto_html(email: str) -> str:
        username = email.split("@")[0]
        return f'<a href="mailto:{escape(email)}">Contactar a {escape(username)}</a>'

    def generar_html(self) -> str:
        if self.ast is not None:
            self._visitar_ast(self.ast)

        partes = [
            "<!DOCTYPE html>",
            "<html lang='es'>",
            "<head>",
            "  <meta charset='UTF-8'>",
            "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "  <title>Smart Home</title>",
            "  <style>",
            "    body { font-family: Arial, sans-serif; margin: 20px; background: #f7f7f7; }",
            "    .sensores { border: 1px solid green; padding: 20px; margin-bottom: 20px; background: #ffffff; }",
            "    .actuador { border: 1px solid gray; padding: 20px; margin-bottom: 20px; background: #ffffff; }",
            "    h1, h2 { margin-top: 0; }",
            "    ul { margin: 0; padding-left: 22px; }",
            "    li { margin-bottom: 6px; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <h1>Smart Home</h1>",
            "  <div class='sensores'>",
            "    <h1>Sensores</h1>",
        ]

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
                        partes.append(
                            f"      <li>{escape(atributo)}: {contenido}</li>"
                        )
                    else:
                        partes.append(
                            f"      <li>{escape(atributo)}: {escape(valor)}</li>"
                        )
                partes.append("    </ul>")
                partes.append("  </div>")
        else:
            partes.append("  <div class='actuador'>")
            partes.append("    <h1>Actuadores</h1>")
            partes.append(
                "    <p>No se detectaron asignaciones a actuadores.</p>"
            )
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


# ============================================================
# Funciones auxiliares (modos de ejecución)
# ============================================================

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
