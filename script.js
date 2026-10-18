/* Calculadora de materiales: frontend conectado al backend REST. */
'use strict';

const pantallas = [...document.querySelectorAll('.pantalla')];
const aviso = document.getElementById('aviso');
const listaHistorial = document.getElementById('historial-lista');
const API = '/api';
const TIPOS = {
    muro: {nombre: 'Muro de ladrillo', formulario: 'form-muro', resultado: 'resultado-muro', campos: ['espesor','largo','alto']},
    viga: {nombre: 'Viga de hormigón', formulario: 'form-viga', resultado: 'resultado-viga', campos: ['largo']},
    columna: {nombre: 'Columna de hormigón', formulario: 'form-columna', resultado: 'resultado-columna', campos: ['largo']},
    contrapiso: {nombre: 'Contrapiso', formulario: 'form-contrapiso', resultado: 'resultado-contrapiso', campos: ['espesor','ancho','largo']},
    techo: {nombre: 'Techo', formulario: 'form-techo', resultado: 'resultado-techo', campos: ['espesor','ancho','largo']},
    pisos: {nombre: 'Pisos', formulario: 'form-pisos', resultado: 'resultado-pisos', campos: ['ancho','largo']},
    pintura: {nombre: 'Pintura', formulario: 'form-pintura', resultado: 'resultado-pintura', campos: ['superficie']}
};
let usuarioActual = null;
let calculoEnEdicion = null;
let timerAviso;

function mostrarAviso(mensaje, tipo = 'info') {
    aviso.textContent = mensaje;
    aviso.className = `aviso aviso--${tipo}`;
    aviso.hidden = false;
    clearTimeout(timerAviso);
    timerAviso = setTimeout(() => { aviso.hidden = true; }, 5000);
}

async function peticion(ruta, opciones = {}) {
    const respuesta = await fetch(API + ruta, {
        credentials: 'same-origin',
        ...opciones,
        headers: { 'Content-Type': 'application/json', ...(opciones.headers || {}) }
    });
    let cuerpo = {};
    try { cuerpo = await respuesta.json(); } catch (_) { /* respuesta sin JSON */ }
    if (!respuesta.ok) throw new Error(cuerpo.error || 'No se pudo completar la solicitud.');
    return cuerpo;
}

function mostrarPantalla(nombre) {
    pantallas.forEach(p => p.classList.toggle('activa', p.id === `pantalla-${nombre}`));
    ocultarResultados();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function ocultarResultados() {
    document.querySelectorAll('.resultado').forEach(el => { el.hidden = true; });
}

function resultadoHtml(tipo, calculation, actualizado = false) {
    const destino = document.getElementById(TIPOS[tipo].resultado);
    const contenedor = destino.querySelector('.resultado__lineas');
    contenedor.replaceChildren();
    const lineas = calculation.result.lines || [];
    for (const linea of lineas) {
        const p = document.createElement('p');
        const nombre = document.createElement('span');
        nombre.className = 'resultado__etiqueta';
        nombre.textContent = `${linea.label}: `;
        const valor = document.createElement('span');
        valor.textContent = `${linea.value} ${linea.unit}`;
        p.append(nombre, valor);
        contenedor.append(p);
    }
    const acciones = destino.querySelector('.resultado__acciones');
    if (acciones) {
        acciones.replaceChildren();
        const texto = document.createElement('p');
        texto.className = 'resultado__guardado';
        texto.textContent = actualizado ? 'Cambios guardados en tu historial.' : 'Cálculo guardado en tu historial.';
        acciones.append(texto);
    }
    destino.hidden = false;
}

function obtenerEntradas(tipo) {
    const cfg = TIPOS[tipo];
    const form = document.getElementById(cfg.formulario);
    const inputs = {};
    for (const nombre of cfg.campos) {
        const campo = form.elements.namedItem(nombre);
        if (!campo || campo.value.trim() === '') {
            campo?.focus();
            throw new Error('Completa todos los campos antes de calcular.');
        }
        const valor = nombre === 'espesor' && tipo === 'muro' ? Number.parseInt(campo.value, 10) : Number(campo.value);
        if (!Number.isFinite(valor) || valor <= 0) {
            campo.focus();
            throw new Error('Ingresa valores numéricos mayores que cero.');
        }
        inputs[nombre] = valor;
    }
    return inputs;
}

async function enviarCalculo(tipo, form) {
    const boton = form.querySelector('button[type="submit"]');
    const original = boton.textContent;
    boton.disabled = true;
    boton.textContent = 'Calculando…';
    try {
        const inputs = obtenerEntradas(tipo);
        const editandoEsteTipo = calculoEnEdicion && calculoEnEdicion.type === tipo;
        if (calculoEnEdicion && !editandoEsteTipo) {
            throw new Error('Termina la edición actual antes de calcular otro tipo.');
        }
        const method = editandoEsteTipo ? 'PUT' : 'POST';
        const route = editandoEsteTipo ? `/calculations/${calculoEnEdicion.id}` : '/calculations';
        const data = await peticion(route, { method, body: JSON.stringify({ type: tipo, inputs }) });
        const calculation = data.calculation;
        form.querySelector('[data-cancelar-edicion]')?.remove();
        calculoEnEdicion = null;
        boton.textContent = 'Calcular';
        resultadoHtml(tipo, calculation, editandoEsteTipo);
        await cargarHistorial();
        mostrarAviso(editandoEsteTipo ? 'Cálculo actualizado.' : 'Cálculo guardado en tu historial.', 'exito');
    } catch (error) {
        mostrarAviso(error.message, 'error');
    } finally {
        boton.disabled = false;
        if (!calculoEnEdicion) boton.textContent = original === 'Actualizar cálculo' ? 'Calcular' : original;
    }
}

function formatoFecha(fecha) {
    const d = new Date(fecha);
    return Number.isNaN(d.getTime()) ? '' : d.toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
}

async function cargarHistorial() {
    if (!usuarioActual) return;
    listaHistorial.replaceChildren();
    try {
        const data = await peticion('/calculations');
        if (!data.calculations.length) {
            const vacio = document.createElement('p');
            vacio.className = 'historial__vacio';
            vacio.textContent = 'Aún no tienes cálculos guardados. Realiza uno para empezar.';
            listaHistorial.append(vacio);
            return;
        }
        for (const item of data.calculations) {
            const article = document.createElement('article');
            article.className = 'historial-item';
            const info = document.createElement('div');
            info.className = 'historial-item__info';
            const title = document.createElement('h4');
            title.textContent = TIPOS[item.type]?.nombre || item.type;
            const date = document.createElement('time');
            date.dateTime = item.updatedAt;
            date.textContent = formatoFecha(item.updatedAt);
            const summary = document.createElement('p');
            summary.textContent = resumen(item);
            info.append(title, date, summary);
            const actions = document.createElement('div');
            actions.className = 'historial-item__acciones';
            const edit = document.createElement('button');
            edit.type = 'button'; edit.className = 'btn-secundario'; edit.textContent = 'Editar';
            edit.dataset.editarCalculo = item.id;
            const remove = document.createElement('button');
            remove.type = 'button'; remove.className = 'btn-secundario btn-secundario--peligro'; remove.textContent = 'Eliminar';
            remove.dataset.eliminarCalculo = item.id;
            actions.append(edit, remove);
            article.append(info, actions);
            listaHistorial.append(article);
        }
    } catch (error) {
        listaHistorial.textContent = error.message;
        mostrarAviso(error.message, 'error');
    }
}

function resumen(item) {
    const rows = item.result.lines || [];
    return rows.slice(0, 2).map(x => `${x.label}: ${x.value} ${x.unit}`).join(' · ');
}

function iniciarEdicion(id) {
    peticion('/calculations').then(({ calculations }) => {
        const item = calculations.find(x => String(x.id) === String(id));
        if (!item) throw new Error('No se encontró el cálculo. Actualiza el historial.');
        calculoEnEdicion = item;
        const cfg = TIPOS[item.type];
        const form = document.getElementById(cfg.formulario);
        for (const [key, value] of Object.entries(item.inputs)) {
            if (form.elements.namedItem(key)) form.elements.namedItem(key).value = value;
        }
        const submit = form.querySelector('button[type="submit"]');
        submit.textContent = 'Actualizar cálculo';
        const actions = form.querySelector('.acciones');
        if (!actions.querySelector('[data-cancelar-edicion]')) {
            const cancel = document.createElement('button');
            cancel.type = 'button';
            cancel.className = 'btn-secundario';
            cancel.dataset.cancelarEdicion = '';
            cancel.textContent = 'Cancelar';
            actions.append(cancel);
        }
        mostrarPantalla(item.type);
        mostrarAviso('Edita las medidas y selecciona “Actualizar cálculo” para guardar los cambios.', 'info');
        document.getElementById(cfg.formulario).scrollIntoView({ behavior: 'smooth', block: 'center' });
    }).catch(err => mostrarAviso(err.message, 'error'));
}

async function eliminarCalculo(id, button) {
    if (!window.confirm('¿Eliminar este cálculo del historial? Esta acción no se puede deshacer.')) return;
    button.disabled = true;
    try {
        await peticion(`/calculations/${id}`, { method: 'DELETE' });
        await cargarHistorial();
        mostrarAviso('Cálculo eliminado del historial.', 'exito');
    } catch (error) {
        mostrarAviso(error.message, 'error');
        button.disabled = false;
    }
}

function actualizarPerfil(user) {
    usuarioActual = user || null;
    const name = document.getElementById('usuario-activo');
    name.textContent = user ? `${user.name} (@${user.username})` : '—';
}

async function iniciarAplicacion() {
    try {
        const data = await peticion('/auth/me');
        actualizarPerfil(data.user);
        if (data.user) {
            mostrarPantalla('menu');
            await cargarHistorial();
        } else {
            mostrarPantalla('login');
        }
    } catch (_) {
        mostrarPantalla('login');
    }
}

/* Navegación restringida al área autenticada. */
document.addEventListener('click', async event => {
    const cancelEdit = event.target.closest('[data-cancelar-edicion]');
    if (cancelEdit) {
        const type = Object.keys(TIPOS).find(key => document.getElementById(TIPOS[key].formulario).contains(cancelEdit));
        if (type) {
            document.getElementById(TIPOS[type].formulario).reset();
            document.getElementById(TIPOS[type].formulario).querySelector('button[type="submit"]').textContent = 'Calcular';
        }
        cancelEdit.remove();
        calculoEnEdicion = null;
        mostrarAviso('Edición cancelada.', 'info');
        return;
    }
    const clear = event.target.closest('[data-borrar-resultado]');
    if (clear) {
        const result = document.getElementById(TIPOS[clear.dataset.borrarResultado].resultado);
        result.hidden = true;
        return;
    }
    const edit = event.target.closest('[data-editar-calculo]');
    if (edit) return iniciarEdicion(edit.dataset.editarCalculo);
    const remove = event.target.closest('[data-eliminar-calculo]');
    if (remove) return eliminarCalculo(remove.dataset.eliminarCalculo, remove);
    const link = event.target.closest('[data-ir]');
    if (!link) return;
    event.preventDefault();
    const destino = link.dataset.ir;
    if (!['login','registro','recuperar'].includes(destino) && !usuarioActual) {
        mostrarAviso('Inicia sesión para acceder a las calculadoras.', 'error');
        return mostrarPantalla('login');
    }
    if (destino === 'login' && usuarioActual) return mostrarPantalla('menu');
    if (destino === 'menu' && usuarioActual) await cargarHistorial();
    mostrarPantalla(destino);
});

/* Registro e inicio de sesión reales */
document.getElementById('form-login').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
        const data = await peticion('/auth/login', { method: 'POST', body: JSON.stringify({
            username: form.elements.usuario.value.trim(), password: form.elements.password.value
        }) });
        actualizarPerfil(data.user);
        form.reset();
        calculoEnEdicion = null;
        mostrarPantalla('menu');
        await cargarHistorial();
        mostrarAviso(`Bienvenido/a, ${data.user.name}.`, 'exito');
    } catch (error) { mostrarAviso(error.message, 'error'); }
    finally { button.disabled = false; }
});

document.getElementById('form-registro').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
        const data = await peticion('/auth/register', { method: 'POST', body: JSON.stringify({
            name: form.elements.nombre.value.trim(), email: form.elements.email.value.trim(),
            username: form.elements.usuario.value.trim(), password: form.elements.password.value
        }) });
        form.reset();
        mostrarPantalla('login');
        mostrarAviso(data.message, 'exito');
    } catch (error) { mostrarAviso(error.message, 'error'); }
    finally { button.disabled = false; }
});

document.getElementById('form-recuperar').addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.currentTarget;
    try {
        const data = await peticion('/auth/recovery', { method: 'POST', body: JSON.stringify({ email: form.elements.email.value.trim() }) });
        form.reset(); mostrarPantalla('login'); mostrarAviso(data.message, 'info');
    } catch (error) { mostrarAviso(error.message, 'error'); }
});

document.getElementById('cerrar-sesion').addEventListener('click', async event => {
    event.preventDefault();
    try { await peticion('/auth/logout', { method: 'POST', body: '{}' }); }
    catch (error) { mostrarAviso(error.message, 'error'); }
    actualizarPerfil(null);
    calculoEnEdicion = null;
    listaHistorial.innerHTML = '<p class="historial__vacio">Inicia sesión para ver tus cálculos guardados.</p>';
    mostrarPantalla('login');
    mostrarAviso('Sesión cerrada.', 'exito');
});

document.getElementById('actualizar-historial').addEventListener('click', cargarHistorial);

for (const [tipo, config] of Object.entries(TIPOS)) {
    document.getElementById(config.formulario).addEventListener('submit', event => {
        event.preventDefault();
        if (!usuarioActual) {
            mostrarAviso('La sesión expiró. Inicia sesión nuevamente.', 'error');
            return mostrarPantalla('login');
        }
        enviarCalculo(tipo, event.currentTarget);
    });
}

iniciarAplicacion();
