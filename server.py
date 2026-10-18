#!/usr/bin/env python3
"""Backend sencillo para la Calculadora de Materiales. Solo usa Python estándar."""
import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse

CARPETA = Path(__file__).resolve().parent
BASE_DATOS = Path(os.environ.get("CALCULADORA_DB", CARPETA / "calculadora.sqlite3"))
HOST = "0.0.0.0"
PUERTO = int(os.environ.get("PORT", "8000"))
COOKIE = "calc_session"
DURACION_SESION = 7 * 24 * 60 * 60


def conectar():
    BASE_DATOS.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(BASE_DATOS, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def preparar_base():
    with conectar() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'usuario',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                inputs_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            DELETE FROM sessions WHERE expires_at < strftime('%s','now');
        """)


def usuario_publico(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"],
            "username": row["username"], "role": row["role"], "createdAt": row["created_at"]}


def cifrar_clave(clave):
    salt = secrets.token_bytes(16)
    hash_clave = hashlib.pbkdf2_hmac("sha256", clave.encode(), salt, 200_000)
    return salt.hex() + "$" + hash_clave.hex()


def clave_correcta(clave, guardada):
    try:
        salt, hash_guardado = guardada.split("$", 1)
        intento = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(intento, hash_guardado)
    except (ValueError, TypeError):
        return False


def numero(datos, campo):
    try:
        valor = float(datos[campo])
    except (KeyError, TypeError, ValueError):
        raise ValueError(f"Ingresa un valor válido para {campo}.")
    if not math.isfinite(valor) or not 0 < valor <= 1_000_000:
        raise ValueError(f"{campo} debe ser mayor que cero y no superar 1.000.000.")
    return valor


def calcular(tipo, datos):
    if not isinstance(datos, dict):
        raise ValueError("Las medidas no son válidas.")

    if tipo == "muro":
        try:
            espesor = float(datos.get("espesor", 20))
        except (TypeError, ValueError):
            raise ValueError("El espesor debe ser 20 o 30 cm.")
        if espesor not in (20, 30):
            raise ValueError("El espesor debe ser 20 o 30 cm.")
        largo, alto = numero(datos, "largo"), numero(datos, "alto")
        area = largo * alto
        cemento, arena, ladrillos = (10.9, .09, 90) if espesor == 20 else (15.2, .115, 120)
        resultado = {"superficie": round(area, 2), "cemento": round(area * cemento, 2),
                     "arena": round(area * arena, 3), "ladrillos": round(area * ladrillos), "espesor": int(espesor)}
        lineas = [("Superficie del muro", resultado["superficie"], "m²"),
                  ("Cemento", resultado["cemento"], "kg"), ("Arena", resultado["arena"], "m³"),
                  ("Ladrillos", resultado["ladrillos"], "unidades")]

    elif tipo == "viga":
        largo = numero(datos, "largo")
        resultado = {"largo": round(largo, 2), "cemento": round(largo * 9, 2), "arena": round(largo * .02, 3),
                     "piedra": round(largo * .02, 3), "hierro8": round(largo * 4, 2), "hierro4": round(largo * 3, 2)}
        lineas = [("Largo de la viga", resultado["largo"], "m"), ("Cemento", resultado["cemento"], "kg"),
                  ("Arena", resultado["arena"], "m³"), ("Piedra", resultado["piedra"], "m³"),
                  ("Hierro del 8", resultado["hierro8"], "m"), ("Hierro del 4", resultado["hierro4"], "m")]

    elif tipo == "columna":
        largo = numero(datos, "largo")
        resultado = {"largo": round(largo, 2), "cemento": round(largo * 7.5, 2), "arena": round(largo * .016, 3),
                     "piedra": round(largo * .016, 3), "hierro10": round(largo * 6, 2), "hierro4": round(largo * 3, 2)}
        lineas = [("Largo de la columna", resultado["largo"], "m"), ("Cemento", resultado["cemento"], "kg"),
                  ("Arena", resultado["arena"], "m³"), ("Piedra", resultado["piedra"], "m³"),
                  ("Hierro del 10", resultado["hierro10"], "m"), ("Hierro del 4", resultado["hierro4"], "m")]

    elif tipo == "contrapiso":
        espesor, ancho, largo = numero(datos, "espesor"), numero(datos, "ancho"), numero(datos, "largo")
        volumen = espesor * ancho * largo
        resultado = {"espesor": espesor, "ancho": ancho, "largo": largo, "volumen": round(volumen, 3),
                     "cemento": round(volumen * 105, 2), "arena": round(volumen * .45, 3), "piedra": round(volumen * .9, 3)}
        lineas = [("Volumen", resultado["volumen"], "m³"), ("Cemento", resultado["cemento"], "kg"),
                  ("Arena", resultado["arena"], "m³"), ("Piedra", resultado["piedra"], "m³")]

    elif tipo == "techo":
        espesor, ancho, largo = numero(datos, "espesor"), numero(datos, "ancho"), numero(datos, "largo")
        area = ancho * largo
        resultado = {"espesor": espesor, "ancho": ancho, "largo": largo, "superficie": round(area, 2),
                     "cemento": round(area * 33, 2), "arena": round(area * .072, 3), "piedra": round(area * .072, 3),
                     "hierro8": round(area * 7, 2), "hierro6": round(area * 4, 2)}
        lineas = [("Superficie", resultado["superficie"], "m²"), ("Espesor", espesor, "m"),
                  ("Cemento", resultado["cemento"], "kg"), ("Arena", resultado["arena"], "m³"),
                  ("Piedra", resultado["piedra"], "m³"), ("Hierro del 8", resultado["hierro8"], "m"),
                  ("Hierro del 6", resultado["hierro6"], "m")]

    elif tipo == "pisos":
        area = numero(datos, "ancho") * numero(datos, "largo")
        resultado = {"ancho": float(datos["ancho"]), "largo": float(datos["largo"]),
                     "superficieNeta": round(area, 2), "superficieConRecorte": round(area * 1.1, 2)}
        lineas = [("Superficie neta", resultado["superficieNeta"], "m²"),
                  ("Superficie con 10% recorte", resultado["superficieConRecorte"], "m²")]

    elif tipo == "pintura":
        area = numero(datos, "superficie")
        resultado = {"superficie": round(area, 2), "litros": round(area / 6, 2)}
        lineas = [("Superficie", resultado["superficie"], "m²"), ("Pintura necesaria", resultado["litros"], "litros")]
    else:
        raise ValueError("Tipo de cálculo no reconocido.")

    return resultado, [{"label": nombre, "value": valor, "unit": unidad} for nombre, valor, unidad in lineas]


class Aplicacion(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(CARPETA), **kwargs)

    def log_message(self, formato, *args):
        print(formato % args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def responder(self, estado, datos, cabeceras=()):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for nombre, valor in cabeceras:
            self.send_header(nombre, valor)
        self.end_headers()
        self.wfile.write(cuerpo)

    def leer_json(self):
        try:
            cantidad = int(self.headers.get("Content-Length", "0"))
            if cantidad <= 0 or cantidad > 64_000:
                raise ValueError("La solicitud está vacía o es demasiado grande.")
            datos = json.loads(self.rfile.read(cantidad))
            if not isinstance(datos, dict):
                raise ValueError("Se esperaba un objeto JSON.")
            return datos
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ValueError("JSON inválido.")

    def token_sesion(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            return cookie[COOKIE].value
        except (KeyError, ValueError):
            return None

    def usuario_actual(self):
        token = self.token_sesion()
        if not token:
            return None
        huella = hashlib.sha256(token.encode()).hexdigest()
        with conectar() as db:
            fila = db.execute("""SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id
                                WHERE s.token_hash=? AND s.expires_at>?""", (huella, int(time.time()))).fetchone()
        return usuario_publico(fila) if fila else None

    def exigir_usuario(self):
        usuario = self.usuario_actual()
        if not usuario:
            self.responder(401, {"error": "Inicia sesión para continuar."})
        return usuario

    @staticmethod
    def calculo_publico(fila):
        return {"id": fila["id"], "type": fila["type"], "inputs": json.loads(fila["inputs_json"]),
                "result": json.loads(fila["result_json"]), "createdAt": fila["created_at"], "updatedAt": fila["updated_at"]}

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/api/health":
            return self.responder(200, {"ok": True})
        if ruta == "/api/auth/me":
            return self.responder(200, {"user": self.usuario_actual()})
        if ruta == "/api/calculations":
            usuario = self.exigir_usuario()
            if not usuario:
                return
            with conectar() as db:
                filas = db.execute("SELECT * FROM calculations WHERE user_id=? ORDER BY updated_at DESC,id DESC", (usuario["id"],)).fetchall()
            return self.responder(200, {"calculations": [self.calculo_publico(f) for f in filas]})
        if ruta.startswith("/api/"):
            return self.responder(404, {"error": "Ruta API no encontrada."})
        if ruta == "/":
            self.path = "/index.html"
        elif ruta not in ("/index.html", "/styles.css", "/script.js"):
            return self.send_error(404)
        return super().do_GET()

    def do_HEAD(self):
        ruta = urlparse(self.path).path
        if ruta == "/":
            self.path = "/index.html"
        elif ruta not in ("/index.html", "/styles.css", "/script.js"):
            return self.send_error(404)
        return super().do_HEAD()

    def do_POST(self):
        ruta = urlparse(self.path).path
        try:
            datos = self.leer_json()
            if ruta == "/api/auth/register":
                nombre = str(datos.get("name", "")).strip()
                email = str(datos.get("email", "")).strip().lower()
                usuario = str(datos.get("username", "")).strip()
                clave = str(datos.get("password", ""))
                if len(nombre) < 2 or "@" not in email or len(usuario) < 3 or len(clave) < 8:
                    raise ValueError("Completa los datos; la contraseña debe tener al menos 8 caracteres.")
                with conectar() as db:
                    try:
                        db.execute("INSERT INTO users(name,email,username,password_hash) VALUES(?,?,?,?)",
                                   (nombre, email, usuario, cifrar_clave(clave)))
                    except sqlite3.IntegrityError:
                        return self.responder(409, {"error": "Ese email o usuario ya está registrado."})
                return self.responder(201, {"message": "Cuenta creada. Ya puedes iniciar sesión."})

            if ruta == "/api/auth/login":
                usuario = str(datos.get("username", "")).strip()
                clave = str(datos.get("password", ""))
                with conectar() as db:
                    fila = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (usuario,)).fetchone()
                    if not fila or not clave_correcta(clave, fila["password_hash"]):
                        return self.responder(401, {"error": "Usuario o contraseña incorrectos."})
                    token = secrets.token_urlsafe(32)
                    huella = hashlib.sha256(token.encode()).hexdigest()
                    expira = int(time.time()) + DURACION_SESION
                    db.execute("INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", (huella, fila["id"], expira))
                cookie = f"{COOKIE}={token}; HttpOnly; Path=/; SameSite=Strict; Max-Age={DURACION_SESION}"
                if self.headers.get("X-Forwarded-Proto") == "https" or os.environ.get("COOKIE_SECURE") == "1":
                    cookie += "; Secure"
                return self.responder(200, {"user": usuario_publico(fila)}, [("Set-Cookie", cookie)])

            if ruta == "/api/auth/logout":
                token = self.token_sesion()
                if token:
                    with conectar() as db:
                        db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
                return self.responder(200, {"message": "Sesión cerrada."}, [("Set-Cookie", f"{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")])

            if ruta == "/api/auth/recovery":
                return self.responder(200, {"message": "La recuperación por email requiere configurar un servicio de correo."})

            if ruta == "/api/calculations":
                usuario = self.exigir_usuario()
                if not usuario:
                    return
                tipo, entradas = str(datos.get("type", "")), datos.get("inputs", {})
                resultado, lineas = calcular(tipo, entradas)
                with conectar() as db:
                    nuevo = db.execute("INSERT INTO calculations(user_id,type,inputs_json,result_json) VALUES(?,?,?,?)",
                                       (usuario["id"], tipo, json.dumps(entradas), json.dumps({"data": resultado, "lines": lineas}))).lastrowid
                    fila = db.execute("SELECT * FROM calculations WHERE id=?", (nuevo,)).fetchone()
                return self.responder(201, {"calculation": self.calculo_publico(fila)})

            return self.responder(404, {"error": "Ruta API no encontrada."})
        except ValueError as error:
            return self.responder(400, {"error": str(error)})
        except Exception as error:
            print("Error:", error)
            return self.responder(500, {"error": "Error interno del servidor."})

    def do_PUT(self):
        partes = urlparse(self.path).path.strip("/").split("/")
        if len(partes) != 3 or partes[:2] != ["api", "calculations"]:
            return self.responder(404, {"error": "Ruta API no encontrada."})
        usuario = self.exigir_usuario()
        if not usuario:
            return
        try:
            datos = self.leer_json()
            tipo, entradas = str(datos.get("type", "")), datos.get("inputs", {})
            resultado, lineas = calcular(tipo, entradas)
            with conectar() as db:
                cursor = db.execute("""UPDATE calculations SET type=?,inputs_json=?,result_json=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND user_id=?""",
                    (tipo, json.dumps(entradas), json.dumps({"data": resultado, "lines": lineas}), partes[2], usuario["id"]))
                if not cursor.rowcount:
                    return self.responder(404, {"error": "Cálculo no encontrado."})
                fila = db.execute("SELECT * FROM calculations WHERE id=?", (partes[2],)).fetchone()
            return self.responder(200, {"calculation": self.calculo_publico(fila)})
        except ValueError as error:
            return self.responder(400, {"error": str(error)})
        except Exception as error:
            print("Error:", error)
            return self.responder(500, {"error": "Error interno del servidor."})

    def do_DELETE(self):
        partes = urlparse(self.path).path.strip("/").split("/")
        if len(partes) != 3 or partes[:2] != ["api", "calculations"]:
            return self.responder(404, {"error": "Ruta API no encontrada."})
        usuario = self.exigir_usuario()
        if not usuario:
            return
        with conectar() as db:
            cursor = db.execute("DELETE FROM calculations WHERE id=? AND user_id=?", (partes[2], usuario["id"]))
        if not cursor.rowcount:
            return self.responder(404, {"error": "Cálculo no encontrado."})
        return self.responder(200, {"message": "Cálculo eliminado."})


if __name__ == "__main__":
    preparar_base()
    print(f"Calculadora disponible en http://localhost:{PUERTO}")
    ThreadingHTTPServer((HOST, PUERTO), Aplicacion).serve_forever()
