# Calculadora de materiales

Frontend HTML/CSS/JavaScript conectado a un backend pequeño en Python y SQLite. No requiere instalar paquetes adicionales.

## Ejecutar

1. Instala Python 3.
2. Abre una terminal en esta carpeta.
3. Ejecuta `python3 server.py`.
4. Visita <http://localhost:8000> y crea una cuenta.

La base `calculadora.sqlite3` se crea automáticamente. Para usar otro puerto o ruta de base de datos:

```bash
PORT=8080 CALCULADORA_DB=/ruta/privada/calculadora.sqlite3 python3 server.py
```

## Qué hace

- Registro, inicio y cierre de sesión.
- Cálculo de muro, viga, columna, contrapiso, techo, pisos y pintura.
- Historial guardado por usuario, con operaciones crear, listar, editar y eliminar.
- SQLite guarda cuentas, sesiones y cálculos; cada cuenta solo puede acceder a su historial.
- Las contraseñas se guardan como hashes; el backend usa exclusivamente la biblioteca estándar de Python.

Las fórmulas y coeficientes siguen el PDF del proyecto. La recuperación de contraseña está preparada como aviso, pero para enviar correos hace falta conectar un servicio de correo.

## API utilizada por el frontend

- `POST /api/auth/register` — registrar (`name`, `email`, `username`, `password`).
- `POST /api/auth/login` — iniciar sesión (`username`, `password`).
- `GET /api/auth/me` — consultar sesión actual.
- `POST /api/auth/logout` — cerrar sesión.
- `GET /api/calculations` — ver historial propio.
- `POST /api/calculations` — guardar cálculo (`type`, `inputs`).
- `PUT /api/calculations/{id}` — recalcular/editar uno propio.
- `DELETE /api/calculations/{id}` — eliminar uno propio.

## Pruebas

```bash
python3 -m unittest -v test_server.py
```
