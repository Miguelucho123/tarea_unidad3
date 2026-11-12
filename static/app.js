'use strict';

const state = {
  tab: 'panel',
  offers: [],
  applications: [],
  students: [],
  companies: []
};

const $ = (sel) => document.querySelector(sel);

const titles = {
  panel: ['Gestión de prácticas', 'Ofertas, postulaciones y revisión institucional en un mismo lugar. Demostración académica de los requisitos RF02, RF03 y RF04.'],
  ofertas: ['Ofertas disponibles', 'Consulta las oportunidades de práctica y registra una postulación de prueba.'],
  publicar: ['Publica una oportunidad', 'Crea una oferta de práctica desde una empresa de demostración.'],
  postulaciones: ['Sigue tus postulaciones', 'Verifica la trazabilidad del estado de cada solicitud registrada.'],
  revision: ['Revisión institucional', 'Aprueba o rechaza solicitudes con control de transición de estados.']
};

async function api(url, opts) {
  const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
  const payload = await res.json();
  if (!res.ok) {
    throw new Error(typeof payload.detail === 'string' ? payload.detail : 'Operación no válida');
  }
  return payload;
}

function notify(msg, error = false) {
  const n = $('#notification');
  n.hidden = false;
  n.textContent = msg;
  n.className = error ? 'error' : '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
  setTimeout(() => { n.hidden = true; }, 5000);
}

function node(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}

function selectedStudent() {
  return Number($('#studentPick').value);
}

async function refresh() {
  [state.offers, state.applications] = await Promise.all([api('/api/ofertas'), api('/api/postulaciones')]);
  render();
}

function renderStats() {
  $('#statOffers').textContent = state.offers.length;
  $('#statApps').textContent = state.applications.length;
  $('#statPending').textContent = state.applications.filter(x => x.estado === 'Pendiente').length;
  $('#offerCount').textContent = state.offers.filter(x => x.estado === 'Abierta').length + ' ofertas abiertas';
}

function renderOffers() {
  const cards = $('#offerCards');
  cards.replaceChildren();
  state.offers.forEach(o => {
    const card = node('article', 'offer-card');
    card.append(node('small', '', o.empresa), node('h3', '', o.titulo), node('p', '', o.descripcion));
    const foot = node('div', 'offer-foot');
    const pill = node('span', 'pill', o.modalidad);
    const btn = node('button', 'outline-btn', 'Postularme');
    btn.disabled = o.estado !== 'Abierta';
    btn.onclick = () => postular(o.id);
    foot.append(pill, btn);
    card.append(foot);
    cards.append(card);
  });
}

function renderApplications() {
  const mine = $('#myApplications');
  mine.replaceChildren();
  const my = state.applications.filter(p => p.estudiante_id === selectedStudent());
  if (!my.length) {
    mine.append(node('p', 'empty', 'Aún no existen postulaciones para este estudiante de demostración.'));
  }
  my.forEach(p => mine.append(makeRow(p, false)));

  const review = $('#reviewList');
  review.replaceChildren();
  if (!state.applications.length) {
    review.append(node('p', 'empty', 'Aún no hay postulaciones. Visita Ofertas disponibles para crear una.'));
  }
  state.applications.forEach(p => review.append(makeRow(p, true)));
}

function render() {
  renderStats();
  renderOffers();
  renderApplications();
}

function makeRow(p, coordinator) {
  const row = node('div', 'app-row');
  const desc = node('div', '');
  const ctrl = node('div', 'app-controls');
  const detalle = (coordinator ? p.estudiante + ' · ' : '') + p.empresa + ' · #' + p.id;
  desc.append(node('strong', '', p.oferta), node('p', '', detalle));
  ctrl.append(node('span', 'pill ' + p.estado.toLowerCase(), p.estado));
  if (coordinator && p.estado === 'Pendiente') {
    const accept = node('button', 'outline-btn', 'Aprobar');
    const reject = node('button', 'outline-btn', 'Rechazar');
    accept.onclick = () => revisar(p.id, 'Aprobada');
    reject.onclick = () => revisar(p.id, 'Rechazada');
    ctrl.append(accept, reject);
  }
  row.append(desc, ctrl);
  return row;
}

async function postular(id) {
  try {
    await api('/api/postulaciones', {
      method: 'POST',
      body: JSON.stringify({ oferta_id: id, estudiante_id: selectedStudent() })
    });
    await refresh();
    notify('Postulación registrada correctamente. Revisa «Mis postulaciones».');
  } catch (e) {
    notify(e.message, true);
  }
}

async function revisar(id, decision) {
  try {
    await api('/api/postulaciones/' + id, { method: 'PATCH', body: JSON.stringify({ decision }) });
    await refresh();
    notify('Estado actualizado a ' + decision + '.');
  } catch (e) {
    notify(e.message, true);
  }
}

async function publicarOferta(e) {
  e.preventDefault();
  const form = e.target;
  const datos = Object.fromEntries(new FormData(form));
  datos.empresa_id = Number(datos.empresa_id);
  try {
    await api('/api/ofertas', { method: 'POST', body: JSON.stringify(datos) });
    form.reset();
    await refresh();
    switchTab('ofertas');
    notify('La nueva oferta quedó publicada en el catálogo.');
  } catch (error) {
    notify(error.message, true);
  }
}

function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.tab-section').forEach(el => { el.hidden = el.id !== 'tab-' + tab; });
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  const [name, description] = titles[tab];
  $('#sectionTitle').replaceChildren(document.createTextNode(name));
  $('#sectionDescription').textContent = description;
  $('#notification').hidden = true;
  render();
}

function fillSelect(select, items, label) {
  items.forEach(item => {
    const opt = node('option', '', item[label]);
    opt.value = item.id;
    select.append(opt);
  });
}

async function initialize() {
  try {
    [state.students, state.companies] = await Promise.all([api('/api/estudiantes'), api('/api/empresas')]);
    fillSelect($('#studentPick'), state.students, 'nombre');
    fillSelect($('#companyPick'), state.companies, 'razon_social');
    document.querySelectorAll('.nav-item').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
    document.querySelectorAll('[data-switch]').forEach(b => { b.onclick = () => switchTab(b.dataset.switch); });
    $('#studentPick').onchange = render;
    $('#offerForm').onsubmit = publicarOferta;
    await refresh();
  } catch (error) {
    notify('No se puede cargar el prototipo: ' + error.message, true);
  }
}

document.addEventListener('DOMContentLoaded', initialize);
