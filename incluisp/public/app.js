const $ = id => document.getElementById(id);
const views = ['routes', 'places', 'suggest', 'benefits', 'transport', 'assistant', 'profile', 'reports', 'moderation'];
const endpointIds = ['origin', 'destination'];
const endpoints = {};
const clean = value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' }).format();
const readableDate = date => date.split('-').reverse().join('/');
const inCity = ([lat, lng]) => lat >= -24 && lat <= -23.32 && lng >= -46.84 && lng <= -46.35;
const center = [-23.5613, -46.6388];
const osmCredit = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
let content = { places: [], resources: {}, benefits: [], transport: [], reportTypes: [] };
let activeView;
let pointPicker;
let reportPosition;
let suggestedPosition;
let moderatorKey;
let routeVersion = 0;
let map;
let basemap;
let mapFailed = false;
let tilesFailed = false;
let reportMarkers;
let placeMarkers;
let endpointMarkers;
let routeLayers;
let results;
let hospitalReference;
let transitPage = 0;
let transitRequest = 0;
let savedProfile = {};
try { savedProfile = JSON.parse(localStorage.getItem('incluisp.profile')) || {}; } catch {}

function el(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function icon(name) {
  const image = el('img');
  image.src = '/icons/' + name + '.svg';
  image.alt = '';
  return image;
}

function link(label, url, className) {
  const node = el('a', className, label);
  node.href = url;
  if (url.startsWith('https:')) {
    node.target = '_blank';
    node.rel = 'noopener noreferrer';
  }
  return node;
}

function button(label, callback, className = 'button secondary') {
  const node = el('button', className, label);
  node.type = 'button';
  node.addEventListener('click', callback);
  return node;
}

function feedback(id, message = '', isError = false) {
  $(id).textContent = message;
  $(id).classList.toggle('error', isError);
}

async function api(path, { method = 'GET', body, key } = {}) {
  const headers = {};
  if (key) headers.Authorization = 'Bearer ' + key;
  if (body) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/' + path, { method, headers, body: body && JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Falha ao consultar o IncluiSP.');
  return data;
}

function busy(form, task) {
  const submit = form.querySelector('[type=submit]');
  if (submit.disabled) return;
  submit.disabled = true;
  return Promise.resolve().then(task).finally(() => { submit.disabled = false; });
}

function renderView() {
  const hash = location.hash.slice(1);
  if (hash === 'main') return;
  const next = views.includes(hash) ? hash : 'routes';
  if (next === activeView) return;
  const isInitial = !activeView;
  activeView = next;
  views.forEach(view => { $('view-' + view).hidden = view !== next; });
  document.querySelectorAll('[data-view]').forEach(item => {
    if (item.dataset.view === next) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });
  if (!isInitial) {
    const heading = $('view-' + next).querySelector('h1');
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }
  if (next === 'routes') {
    if (!map && !mapFailed) setupMap();
    requestAnimationFrame(() => map?.invalidateSize());
  } else if (pointPicker) {
    pointPicker = undefined;
    mapNotice();
  }
  if (next === 'reports') loadMine();
  if (next === 'places') renderPlaces();
  if (next === 'suggest') loadSuggestions();
  if (next === 'transport' && !$('transit-status').textContent) loadTransit();
}

function go(view) {
  if (location.hash !== '#' + view) location.hash = view;
  renderView();
}

function mapNotice() {
  const instruction = pointPicker?.description || (mapFailed ? 'O mapa está indisponível. Use a busca de endereços.' :
    tilesFailed ? 'Falha ao carregar parte do mapa. Você pode usar a descrição textual das rotas.' : '');
  const notice = $('map-message');
  notice.textContent = instruction;
  notice.hidden = !instruction;
  $('map-pick-actions').hidden = !pointPicker;
  $('map-retry').hidden = !tilesFailed;
}

function mapPin(name, type) {
  return L.divIcon({ className: 'pin ' + type, html: icon(name), iconSize: [30, 30], iconAnchor: [15, 15], popupAnchor: [0, -15] });
}

function setupMap() {
  if (!window.L) {
    mapFailed = true;
    mapNotice();
    return;
  }
  map = L.map('map', { zoomControl: false, minZoom: 10, maxZoom: 19, scrollWheelZoom: false }).setView(center, 13);
  loadStreetMap();
  const zoom = L.control.zoom({ position: 'bottomright', zoomInTitle: 'Aproximar mapa', zoomOutTitle: 'Afastar mapa' }).addTo(map);
  const controls = zoom.getContainer().querySelectorAll('a');
  controls[0].setAttribute('aria-label', 'Aproximar mapa');
  controls[1].setAttribute('aria-label', 'Afastar mapa');
  placeMarkers = L.layerGroup().addTo(map);
  reportMarkers = L.layerGroup().addTo(map);
  endpointMarkers = L.layerGroup().addTo(map);
  routeLayers = L.layerGroup().addTo(map);
  map.on('click', event => chooseMapPoint([event.latlng.lat, event.latlng.lng]));
  refreshMapPlaces();
  loadPublicReports();
}

function loadStreetMap() {
  if (!map) return;
  if (basemap) map.removeLayer(basemap);
  const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: osmCredit });
  layer.on('loading', () => {
    tilesFailed = false;
    mapNotice();
  });
  layer.on('tileerror', () => {
    tilesFailed = true;
    mapNotice();
  });
  basemap = layer;
  layer.addTo(map);
}

$('map-retry').addEventListener('click', loadStreetMap);
$('map-overview').addEventListener('click', () => {
  if (map && content.places.length) {
    map.closePopup();
    map.fitBounds(content.places.map(place => place.position), { padding: [36, 36], maxZoom: 15 });
  }
});

function refreshMapPlaces() {
  if (!placeMarkers) return;
  placeMarkers.clearLayers();
  for (const place of content.places) {
    const popup = el('div');
    popup.append(el('strong', '', place.name), el('div', '', place.address),
      el('div', '', place.resources.map(resource => content.resources[resource]).join(' · ')),
      button('Usar como destino', () => planTo(place)));
    if (place.visit) popup.insertBefore(el('div', 'popup-benefit', place.visit.title), popup.lastElementChild);
    const marker = { Transporte: 'train-front', Hospital: 'hospital', Restaurante: 'utensils' }[place.category] || 'map-pin';
    L.marker(place.position, { icon: mapPin(marker, 'place'), alt: place.name, title: place.name })
      .addTo(placeMarkers).bindPopup(popup);
  }
}

async function loadPublicReports() {
  if (!reportMarkers) return;
  try {
    const reports = await api('reports');
    reportMarkers.clearLayers();
    for (const report of reports) {
      const popup = el('div');
      popup.append(el('strong', '', report.type), el('div', '', report.location), el('div', '', report.description),
        el('div', '', 'Relato público revisado · ' + readableDate(report.date)));
      L.marker(report.position, { icon: mapPin('triangle-alert', 'report'), alt: report.type, title: report.type })
        .addTo(reportMarkers).bindPopup(popup);
    }
  } catch { /* The map still provides the basemap and catalog. */ }
}

function coordinates(point) {
  return point.map(number => number.toFixed(5)).join(', ');
}

function chooseMapPoint(point) {
  if (!pointPicker) return;
  if (!inCity(point)) {
    const hint = $('map-message');
    hint.textContent = 'Selecione um ponto na área de São Paulo.';
    hint.hidden = false;
    return;
  }
  const selection = pointPicker;
  pointPicker = undefined;
  mapNotice();
  selection.onChoose(point);
}

function requestMapPoint(description, onChoose, onCancel) {
  go('routes');
  if (mapFailed) return false;
  pointPicker = { description, onChoose, onCancel };
  mapNotice();
  $('map').focus();
  $('map').scrollIntoView({ block: 'nearest' });
  return true;
}

function locate(onPoint, onError) {
  if (!navigator.geolocation) return onError('A localização não está disponível neste navegador.');
  navigator.geolocation.getCurrentPosition(position => {
    const point = [position.coords.latitude, position.coords.longitude];
    if (!inCity(point)) return onError('A sua localização está fora da área de São Paulo atendida pelo mapa.');
    onPoint(point);
  }, () => onError('O navegador não forneceu a localização. Confira a permissão ou marque um ponto no mapa.'), { timeout: 7000 });
}

function planTo(place) {
  go('routes');
  setEndpoint('destination', place);
  $('origin').focus();
}

function showPlace(place) {
  go('routes');
  if (!map) return feedback('route-status', 'O mapa não está disponível.', true);
  map.setView(place.position, 16);
  placeMarkers.eachLayer(marker => {
    if (marker.options.title === place.name) marker.openPopup();
  });
  $('map').scrollIntoView({ block: 'nearest' });
}

function clearRoute() {
  routeVersion++;
  results = undefined;
  routeLayers?.clearLayers();
  $('route-results').replaceChildren();
  feedback('route-status');
}

function drawEndpoints() {
  endpointMarkers?.clearLayers();
  for (const id of endpointIds) {
    if (endpoints[id] && endpointMarkers) {
      L.marker(endpoints[id].position, { icon: mapPin(id === 'origin' ? 'circle-dot' : 'flag', 'endpoint'), interactive: false, zIndexOffset: 500 })
        .addTo(endpointMarkers);
    }
  }
}

function setEndpoint(id, place) {
  endpoints[id] = place;
  $(id).value = place.name;
  $(id + '-options').hidden = true;
  clearRoute();
  drawEndpoints();
}

function localSuggestions(query) {
  return content.places.filter(place => clean([place.name, place.address, ...(place.aliases || [])].join(' ')).includes(clean(query)));
}

function suggestions(container, places, select) {
  container.replaceChildren();
  container.hidden = !places.length;
  for (const place of places) {
    const option = button('', () => select(place), '');
    option.append(el('strong', '', place.name), el('small', '', place.address));
    container.append(option);
  }
}

for (const id of endpointIds) {
  const input = $(id);
  const container = $(id + '-options');
  const show = () => {
    if (!endpoints[id]) suggestions(container, localSuggestions(input.value), place => {
      setEndpoint(id, place);
      input.focus();
    });
  };
  input.addEventListener('focus', show);
  input.addEventListener('input', () => {
    delete endpoints[id];
    drawEndpoints();
    clearRoute();
    show();
  });
  input.closest('.field').addEventListener('focusout', event => {
    if (!input.closest('.field').contains(event.relatedTarget)) container.hidden = true;
  });
  input.closest('.field').addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      input.focus();
      container.hidden = true;
    }
    if (event.key === 'ArrowDown' && !container.hidden && event.target === input) {
      event.preventDefault();
      container.querySelector('button')?.focus();
    }
  });
}

$('swap').addEventListener('click', () => {
  [endpoints.origin, endpoints.destination] = [endpoints.destination, endpoints.origin];
  [$('origin').value, $('destination').value] = [$('destination').value, $('origin').value];
  endpointIds.forEach(id => { $(id + '-options').hidden = true; });
  clearRoute();
  drawEndpoints();
});
$('location').addEventListener('click', () => {
  feedback('route-status', 'Solicitando localização…');
  locate(point => {
    setEndpoint('origin', { name: 'Minha localização', position: point });
    map?.setView(point, 16);
    feedback('route-status', 'Localização definida como origem.');
  }, message => feedback('route-status', message, true));
});
$('pick-route').addEventListener('click', () => {
  const offer = id => requestMapPoint(id === 'origin' ? 'Selecione a origem no mapa.' : 'Selecione o destino no mapa.', point => {
    setEndpoint(id, { name: 'Ponto no mapa · ' + coordinates(point), position: point });
    if (id === 'origin' && !endpoints.destination) offer('destination');
    else $('route-form').querySelector('[type=submit]').focus();
  });
  if (!offer(!endpoints.origin || endpoints.destination ? 'origin' : 'destination')) {
    feedback('route-status', 'O mapa está indisponível. Use a busca de endereços.', true);
  }
});
$('pick-center').addEventListener('click', () => {
  const point = map.getCenter();
  chooseMapPoint([point.lat, point.lng]);
});
$('cancel-pick').addEventListener('click', () => {
  const onCancel = pointPicker?.onCancel;
  pointPicker = undefined;
  mapNotice();
  if (onCancel) onCancel();
  else $('pick-route').focus();
});

function renderRoutes(active = 0) {
  const { routes, source, url } = results;
  routeLayers?.clearLayers();
  if (map) {
    const shapes = routes.map((route, index) => L.polyline(route.geometry, {
      color: index === active ? '#19734b' : '#486457', weight: index === active ? 6 : 4,
      dashArray: index === active ? undefined : '7 7', opacity: index === active ? 0.93 : 0.6
    }).addTo(routeLayers));
    shapes[active].bringToFront();
    map.fitBounds(shapes[active].getBounds(), { padding: [36, 36], maxZoom: 17 });
  }
  $('route-results').replaceChildren(...routes.map((route, index) => {
    const card = el('article', 'route-choice' + (index === active ? ' active' : ''));
    const title = el('h3', '', routes.length === 1 ? 'Percurso encontrado' : 'Alternativa ' + (index + 1));
    const distance = route.meters >= 1000 ? (route.meters / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + ' km' : route.meters + ' m';
    card.append(title, el('p', 'meta', endpoints.origin.name + ' → ' + endpoints.destination.name),
      el('p', 'meta', distance + ' · ' + route.minutes + ' min estimados'),
      el('div', 'tag warning', route.status),
      el('p', 'meta', 'Cobertura incompleta para confirmar calçadas, rampas, inclinação e rebaixamentos.'));
    if (route.barriers.length) {
      const list = el('ul');
      for (const report of route.barriers) list.append(el('li', '', report.type + ' perto do percurso · ' + report.location + ' · Relato revisado em ' + readableDate(report.updated.slice(0, 10))));
      card.append(list);
    }
    if (route.exceedsDistance) card.append(el('p', 'meta', 'Este percurso excede a distância confortável do seu perfil.'));
    if (savedProfile.needsHelp) card.append(link('Consultar orientações de apoio', '#transport'));
    const directions = el('details');
    directions.append(el('summary', '', 'Descrição do percurso'));
    const steps = el('ol');
    route.steps.forEach(step => steps.append(el('li', '', step)));
    directions.append(route.steps.length ? steps : el('p', '', 'O serviço não retornou instruções por escrito para este percurso.'));
    card.append(directions, link(source, url, 'meta'));
    if (routes.length > 1 && active !== index) card.append(el('br'), button('Mostrar no mapa', () => {
      renderRoutes(index);
      const heading = $('route-results').querySelector('.active h3');
      heading.tabIndex = -1;
      heading.focus();
    }, 'text-button'));
    return card;
  }));
}

$('route-form').addEventListener('submit', event => {
  event.preventDefault();
  busy(event.currentTarget, async () => {
    clearRoute();
    try {
      for (const id of endpointIds) {
        if (endpoints[id]) continue;
        const query = $(id).value.trim();
        if (query.length < 3) {
          $(id).focus();
          throw new Error('Informe a origem e o destino ou marque os pontos no mapa.');
        }
        feedback('route-status', 'Buscando endereço…');
        const candidates = await api('search?q=' + encodeURIComponent(query));
        if ($(id).value.trim() !== query) return;
        if (!candidates.length) throw new Error('Nenhum lugar encontrado para “' + query + '”.');
        $(id).focus();
        suggestions($(id + '-options'), candidates, place => {
          setEndpoint(id, place);
          if (id === 'origin' && !endpoints.destination) $('destination').focus();
          else $('route-form').querySelector('[type=submit]').focus();
        });
        $(id + '-options').querySelector('button').focus();
        feedback('route-status', 'Selecione uma opção em ' + (id === 'origin' ? 'Origem.' : 'Destino.'));
        return;
      }
      const version = routeVersion;
      feedback('route-status', 'Consultando percursos disponíveis…');
      const { mobility, preference, avoidStairs, maxDistance } = savedProfile;
      const data = await api('routes', { method: 'POST', body: { origin: endpoints.origin.position, destination: endpoints.destination.position,
        profile: { mobility, preference, avoidStairs, maxDistance } } });
      if (version !== routeVersion) return;
      results = data;
      renderRoutes();
      feedback('route-status', data.routes.length === 1 ? '1 percurso retornado.' : data.routes.length + ' percursos para comparar.');
    } catch (error) {
      feedback('route-status', error.message, true);
    }
  });
});

function photoFigure(id, photo) {
  const figure = el('figure', 'place-photo');
  const image = el('img');
  if (photo.fit === 'contain') image.className = 'photo-contain';
  image.alt = photo.alt;
  image.loading = 'lazy';
  image.decoding = 'async';
  const caption = el('figcaption');
  if (photo.illustrative) caption.append(document.createTextNode('Imagem ilustrativa · '));
  caption.append(photo.sourceUrl ? link(photo.credit, photo.sourceUrl) : document.createTextNode(photo.credit));
  if (photo.licenseUrl) caption.append(document.createTextNode(' · '), link(photo.license, photo.licenseUrl));
  image.addEventListener('error', () => {
    image.hidden = true;
    const fallback = photo.sourceUrl ? link('Ver a foto na fonte', photo.sourceUrl, 'photo-fallback') : communityImage();
    figure.prepend(fallback);
  }, { once: true });
  image.src = photo.url || '/photos/' + (photo.fileId || id) + (photo.format === 'png' ? '.png' : '.jpg');
  figure.append(image, caption);
  return figure;
}

function communityImage() {
  const visual = el('div', 'community-image');
  visual.append(icon('image-plus'), el('span', '', 'Sugestão da comunidade'));
  return visual;
}

function communityFigure(place) {
  if (place.hasPhoto) return photoFigure(place.id, {
    url: '/api/suggestions/' + place.id + '/photo',
    alt: 'Foto enviada da sugestão ' + place.name,
    credit: 'Foto da comunidade'
  });
  const figure = el('figure', 'place-photo');
  figure.append(communityImage());
  return figure;
}

function placeCard(place, { compact = false, distance } = {}) {
  const card = el('article', 'panel info-card');
  if (!compact && place.community) card.append(communityFigure(place));
  else if (place.photo && !compact) card.append(photoFigure(place.id, place.photo));
  const provenance = place.community ? 'Sugestão da comunidade' : place.sourceLabel || 'Fonte oficial';
  card.append(el('span', 'tag', place.category), el('span', place.community ? 'tag' : 'tag verified', provenance),
    el('h3', '', place.name), el('p', 'meta', place.address), el('p', '', place.description));
  if (Number.isFinite(distance)) {
    const label = distance < 1000 ? Math.round(distance) + ' m' :
      (distance / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' km';
    card.append(el('div', 'place-distance', label + ' em linha reta'));
  }
  if (!compact) {
    const features = el('div');
    place.resources.forEach(resource => features.append(el('span', 'tag', content.resources[resource])));
    card.append(features);
    if (place.category === 'Hospital' && !place.resources.some(resource => resource !== 'transit')) {
      card.append(el('p', 'meta', 'Recursos de acessibilidade da unidade ainda sem confirmação no catálogo.'));
    }
  }
  const source = el('div', 'meta');
  if (place.community) source.textContent = 'Recursos informados pela comunidade. Confirme com o local antes da visita.';
  else source.append(link(place.source, place.url), document.createTextNode(' · Consulta em ' + readableDate(place.checked)));
  card.append(source);
  if (place.reference) {
    const reference = el('div', 'meta');
    reference.append(link(place.reference.title, place.reference.url));
    card.append(reference);
  }
  if (place.covered) card.append(el('p', 'meta', 'Local coberto. Confira o horário e o acesso antes de se deslocar.'));
  if (place.contact) card.append(link(place.contact, 'mailto:' + place.contact, 'meta'));
  if (place.visit) {
    const visit = el('aside', 'place-benefit');
    visit.append(el('strong', '', place.visit.title), el('p', '', place.visit.description),
      link('Condições de visita', place.visit.url));
    card.append(visit);
  }
  const actions = el('div', 'actions');
  actions.append(button('Ver no mapa', () => showPlace(place)), button('Planejar rota', () => planTo(place)));
  card.append(actions);
  return card;
}

function distanceInMeters(a, b) {
  const radians = degrees => degrees * Math.PI / 180;
  const latitude = radians(b[0] - a[0]);
  const longitude = radians(b[1] - a[1]);
  const arc = Math.sin(latitude / 2) ** 2 +
    Math.cos(radians(a[0])) * Math.cos(radians(b[0])) * Math.sin(longitude / 2) ** 2;
  return 12742000 * Math.asin(Math.sqrt(Math.min(1, arc)));
}

function renderPlaces() {
  const query = clean($('place-query').value);
  const category = $('place-category').value;
  const selected = [...$('place-filters').querySelectorAll('input:checked')].map(input => input.value);
  $('clear-place-filters').hidden = !(query || category || selected.length);
  const places = content.places.filter(place =>
    (!category || category === place.category) &&
    clean([place.name, place.address, ...(place.aliases || [])].join(' ')).includes(query) &&
    selected.every(resource => {
      if (resource === 'verified') return Boolean(place.checked);
      if (resource === 'benefit') return Boolean(place.visit);
      if (resource === 'covered') return Boolean(place.covered);
      return place.resources.includes(resource);
    }));
  const hospitals = category === 'Hospital';
  const nearby = hospitals || selected.includes('covered');
  $('hospital-reference').hidden = !nearby;
  $('hospital-use-origin').hidden = !endpoints.origin;
  if (nearby) {
    const reference = hospitalReference || endpoints.origin || content.places.find(place => place.id === 'masp');
    if (reference) {
      const group = hospitals ? 'Hospitais do catálogo' : 'Locais cobertos cadastrados';
      $('hospital-distance-reference').textContent = group + ' por distância em linha reta. Referência: ' + reference.name + '.';
      const ranked = places.map(place => ({ place, distance: distanceInMeters(reference.position, place.position) }));
      ranked.sort((a, b) => a.distance - b.distance);
      $('places-list').replaceChildren(...ranked.map(({ place, distance }) => placeCard(place, { distance })));
    }
  } else {
    $('places-list').replaceChildren(...places.map(place => placeCard(place)));
  }
  feedback('place-status', places.length === 1 ? '1 local encontrado.' : places.length ? places.length + ' locais encontrados.' : 'Nenhum local corresponde aos filtros.');
}
$('place-query').addEventListener('input', renderPlaces);
$('place-category').addEventListener('change', renderPlaces);
$('place-filters').addEventListener('change', renderPlaces);

function setPlaceFilter(category, resource) {
  $('place-query').value = '';
  $('place-category').value = category;
  $('place-filters').querySelectorAll('input').forEach(input => { input.checked = input.value === resource; });
  renderPlaces();
}

$('nearby-hospitals').addEventListener('click', () => setPlaceFilter('Hospital'));
$('hospital-filter').addEventListener('click', () => setPlaceFilter('Hospital'));
$('shelter-filter').addEventListener('click', () => setPlaceFilter('', 'covered'));
$('ramp-restaurants').addEventListener('click', () => setPlaceFilter('Restaurante', 'ramp'));
$('clear-place-filters').addEventListener('click', () => {
  setPlaceFilter('');
  $('place-query').focus();
});
$('hospital-locate').addEventListener('click', () => {
  feedback('hospital-location-status', 'Solicitando localização…');
  locate(point => {
    hospitalReference = { name: 'sua localização', position: point };
    renderPlaces();
    feedback('hospital-location-status', 'Resultados ordenados a partir da sua localização.');
  }, message => feedback('hospital-location-status', message, true));
});
$('hospital-use-origin').addEventListener('click', () => {
  hospitalReference = undefined;
  renderPlaces();
  feedback('hospital-location-status', 'Resultados ordenados a partir da origem do trajeto.');
});

function renderBenefits() {
  $('benefits-list').replaceChildren();
  $('offers-list').replaceChildren();
  for (const benefit of content.benefits) {
    const card = el('article', 'panel info-card');
    if (benefit.photo) card.append(photoFigure(benefit.id, benefit.photo));
    card.append(el('span', 'tag', benefit.category), el('span', 'tag ' + (benefit.status === 'Demonstração' ? 'warning' : 'verified'), benefit.status),
      el('h3', '', benefit.name), el('p', 'meta', benefit.organization), el('p', '', benefit.description),
      el('p', '', benefit.eligibility), el('p', 'meta', benefit.validity));
    if (benefit.url) card.append(link('Consultar ' + benefit.source, benefit.url, 'button secondary'));
    $(benefit.category === 'Oferta comercial' ? 'offers-list' : 'benefits-list').append(card);
  }
  $('offers-section').hidden = !$('offers-list').childElementCount;
  $('culture-benefits').replaceChildren(...content.places.filter(place => place.visit).map(place => {
    const card = el('article', 'panel info-card');
    if (place.photo) card.append(photoFigure(place.id, place.photo));
    card.append(el('span', 'tag verified', place.visit.title), el('h3', '', place.name),
      el('p', 'meta', place.address), el('p', '', place.visit.description));
    const actions = el('div', 'actions');
    actions.append(link('Condições de visita', place.visit.url, 'button secondary'), button('Ver no mapa', () => showPlace(place)));
    card.append(actions);
    return card;
  }));
}

function renderTransport() {
  const cards = content.transport.map(transport => {
    const card = el('article', 'panel info-card');
    card.append(el('span', 'tag', transport.type), el('h3', '', transport.name),
      el('p', '', transport.description), link(transport.source, transport.url, 'button secondary'));
    return card;
  });
  $('transport-list').replaceChildren(...cards, ...content.places.filter(place => place.category === 'Transporte').map(place => placeCard(place, { compact: true })));
  $('transport-guides').replaceChildren(...(content.guides || []).map(guide => {
    const article = el('article', 'panel info-card');
    article.append(el('h3', '', guide.guide), el('p', '', guide.answer));
    const actions = el('div', 'actions');
    guide.sources.forEach(source => actions.append(link(source.title, source.url, 'text-button')));
    article.append(actions);
    return article;
  }));
}

async function loadTransit(page = 0) {
  const id = ++transitRequest;
  const query = new URLSearchParams({ mode: $('transit-mode').value, q: $('transit-query').value.trim(), page });
  feedback('transit-status', 'Buscando locais de transporte…');
  $('transit-prev').hidden = true;
  $('transit-next').hidden = true;
  try {
    const data = await api('transit?' + query);
    if (id !== transitRequest) return;
    transitPage = page;
    feedback('transit-status', data.total ?
      data.start.toLocaleString('pt-BR') + ' a ' + (data.start + data.items.length - 1).toLocaleString('pt-BR') +
      ' de ' + data.total.toLocaleString('pt-BR') + ' resultados.' : 'Nenhum local encontrado.');
    $('transit-results').replaceChildren(...data.items.map(point => {
      const item = el('article', 'transit-result');
      item.append(el('h3', '', point.name), el('p', 'meta', point.address || point.detail));
      if (point.address && point.detail) item.append(el('p', 'meta', point.detail));
      const actions = el('div', 'actions');
      actions.append(button('Ver no mapa', () => showTransitPoint(point), 'text-button'));
      actions.append(button('Usar como destino', () => planTo(point), 'text-button'));
      item.append(actions);
      return item;
    }));
    $('transit-prev').hidden = page === 0;
    $('transit-next').hidden = !data.hasNext;
  } catch (error) {
    if (id !== transitRequest) return;
    $('transit-results').replaceChildren();
    feedback('transit-status', error.message, true);
  }
}

function showTransitPoint(point) {
  go('routes');
  if (!map) return feedback('route-status', 'O mapa não está disponível.', true);
  const popup = el('div');
  popup.append(el('strong', '', point.name), el('p', '', point.address || point.detail),
    button('Usar como destino', () => planTo(point)));
  map.setView(point.position, 17);
  L.popup().setLatLng(point.position).setContent(popup).openOn(map);
  $('map').scrollIntoView({ block: 'nearest' });
}

$('transit-form').addEventListener('submit', event => { event.preventDefault(); loadTransit(); });
$('transit-mode').addEventListener('change', () => loadTransit());
$('transit-prev').addEventListener('click', () => loadTransit(Math.max(0, transitPage - 1)));
$('transit-next').addEventListener('click', () => loadTransit(transitPage + 1));

function loadProfile() {
  $('nickname').value = savedProfile.nickname || '';
  $('mobility').value = savedProfile.mobility || '';
  $('preference').value = savedProfile.preference || '';
  $('max-distance').value = savedProfile.maxDistance || '';
  $('avoid-stairs').checked = savedProfile.avoidStairs || false;
  $('needs-help').checked = savedProfile.needsHelp || false;
  $('profile-hint').textContent = Object.values(savedProfile).some(Boolean) ? 'Preferências aplicadas à próxima busca.' : 'Personalize as preferências do seu trajeto.';
}
$('profile-form').addEventListener('submit', event => {
  event.preventDefault();
  const profile = { nickname: $('nickname').value.trim(), mobility: $('mobility').value, preference: $('preference').value,
    maxDistance: Number($('max-distance').value) || null, avoidStairs: $('avoid-stairs').checked, needsHelp: $('needs-help').checked };
  try {
    localStorage.setItem('incluisp.profile', JSON.stringify(profile));
    savedProfile = profile;
    loadProfile();
    clearRoute();
    feedback('profile-status', 'Preferências salvas neste navegador.');
  } catch { feedback('profile-status', 'O navegador bloqueou o armazenamento do perfil.', true); }
});
$('clear-profile').addEventListener('click', () => {
  try {
    localStorage.removeItem('incluisp.profile');
    savedProfile = {};
    loadProfile();
    clearRoute();
    feedback('profile-status', 'Perfil limpo.');
  } catch { feedback('profile-status', 'Não foi possível apagar o perfil neste navegador.', true); }
});

function showMessage(name, text, sources = [], action) {
  const message = el('div', name === 'Você' ? 'message user' : 'message');
  message.append(el('strong', '', name), el('p', '', text));
  sources.forEach(source => message.append(link(source.title, source.url)));
  const links = { routes: 'Abrir planejador', transport: 'Consultar Transporte e ajuda', profile: 'Abrir meu perfil', places: 'Ver lugares cobertos' };
  if (links[action]) {
    const actionLink = link(links[action], '#' + action);
    if (action === 'places') actionLink.addEventListener('click', () => setPlaceFilter('', 'covered'));
    message.append(actionLink);
  }
  const messages = $('messages');
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}
$('assistant-form').addEventListener('submit', event => {
  event.preventDefault();
  const question = $('question').value.trim();
  if (!question) return;
  busy(event.currentTarget, async () => {
    $('question').value = '';
    showMessage('Você', question);
    const loading = showMessage('Inclui IA', 'Consultando a base…');
    try {
      const result = await api('assistant', { method: 'POST', body: { question } });
      loading.remove();
      showMessage('Inclui IA', result.answer, result.sources, result.action);
    } catch (error) {
      loading.remove();
      showMessage('Inclui IA', error.message);
    }
  });
});
$('assistant-prompts').addEventListener('click', event => {
  if (event.target instanceof HTMLButtonElement) {
    $('question').value = event.target.textContent;
    $('assistant-form').requestSubmit();
  }
});

function setReportPosition(position, label) {
  reportPosition = position;
  if (label) $('report-location').value = label;
  $('report-options').hidden = true;
  feedback('report-point', 'Ponto selecionado · ' + coordinates(position));
}

$('report-location').addEventListener('input', () => {
  reportPosition = undefined;
  $('report-options').hidden = true;
  feedback('report-point');
});
$('search-report').addEventListener('click', async () => {
  const query = $('report-location').value.trim();
  feedback('report-point', 'Buscando endereço…');
  try {
    const places = await api('search?q=' + encodeURIComponent(query));
    if ($('report-location').value.trim() !== query) return;
    suggestions($('report-options'), places, place => {
      setReportPosition(place.position, (place.name + (place.address ? ' · ' + place.address : '')).slice(0, 150));
      $('report-date').focus();
    });
    $('report-options').querySelector('button')?.focus();
    feedback('report-point', places.length ? 'Selecione um endereço.' : 'Nenhum endereço encontrado.');
  } catch (error) { feedback('report-point', error.message, true); }
});
$('pick-report').addEventListener('click', () => {
  const returnToReport = () => {
    go('reports');
    $('pick-report').focus();
  };
  if (!requestMapPoint('Selecione o local da ocorrência no mapa.', point => {
    go('reports');
    setReportPosition(point, $('report-location').value || 'Ponto no mapa');
    $('report-location').focus();
  }, returnToReport)) {
    returnToReport();
    feedback('report-point', 'O mapa está indisponível. Use a busca de endereços.', true);
  }
});
$('locate-report').addEventListener('click', () => {
  feedback('report-point', 'Solicitando localização…');
  locate(point => setReportPosition(point, $('report-location').value || 'Minha localização'), message => feedback('report-point', message, true));
});

function photoData(file) {
  if (!file) return Promise.resolve(null);
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 2 * 1024 * 1024) {
    return Promise.reject(new Error('Use uma imagem JPG, PNG ou WebP de até 2 MB.'));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Não foi possível abrir a foto.'));
    reader.readAsDataURL(file);
  });
}

function setSuggestedPosition(position, address) {
  suggestedPosition = position;
  if (address) $('suggest-address').value = address;
  $('suggest-options').hidden = true;
  feedback('suggest-point', 'Ponto selecionado · ' + coordinates(position));
}

$('suggest-address').addEventListener('input', () => {
  suggestedPosition = undefined;
  $('suggest-options').hidden = true;
  feedback('suggest-point');
});
$('suggest-search').addEventListener('click', async () => {
  const query = $('suggest-address').value.trim();
  feedback('suggest-point', 'Buscando endereço…');
  try {
    const places = await api('search?q=' + encodeURIComponent(query));
    if ($('suggest-address').value.trim() !== query) return;
    suggestions($('suggest-options'), places, place => {
      setSuggestedPosition(place.position, (place.address || place.name).slice(0, 150));
      $('suggest-description').focus();
    });
    $('suggest-options').querySelector('button')?.focus();
    feedback('suggest-point', places.length ? 'Selecione um endereço.' : 'Nenhum endereço encontrado.');
  } catch (error) { feedback('suggest-point', error.message, true); }
});
$('suggest-pick').addEventListener('click', () => {
  const returnToSuggestion = () => {
    go('suggest');
    $('suggest-pick').focus();
  };
  if (!requestMapPoint('Selecione o local sugerido no mapa.', point => {
    go('suggest');
    setSuggestedPosition(point);
    $('suggest-address').focus();
  }, returnToSuggestion)) {
    returnToSuggestion();
    feedback('suggest-point', 'O mapa está indisponível. Use a busca de endereços.', true);
  }
});

async function loadSuggestions() {
  try {
    const items = await api('suggestions/mine');
    $('my-suggestions').replaceChildren(...(items.length ? items.map(place => {
      const card = el('article', 'item');
      card.append(communityFigure(place), el('span', 'tag', place.statusLabel),
        el('h3', '', place.name), el('p', 'meta', place.address));
      if (place.review) card.append(el('p', 'meta', place.review));
      return card;
    }) : [el('p', 'meta', 'Suas sugestões enviadas neste navegador aparecem aqui.')]));
  } catch (error) { $('my-suggestions').textContent = error.message; }
}

$('suggest-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  busy(form, async () => {
    if (!suggestedPosition) return feedback('suggest-status', 'Selecione um endereço ou marque o local no mapa.', true);
    try {
      await api('suggestions', { method: 'POST', body: {
        name: $('suggest-name').value, address: $('suggest-address').value, category: $('suggest-category').value,
        position: suggestedPosition, description: $('suggest-description').value,
        resources: [...$('suggest-resources').querySelectorAll('input:checked')].map(input => input.value),
        photo: await photoData($('suggest-photo').files[0])
      } });
      form.reset();
      suggestedPosition = undefined;
      feedback('suggest-point');
      feedback('suggest-status', 'Sugestão enviada para revisão.');
      loadSuggestions();
    } catch (error) { feedback('suggest-status', error.message, true); }
  });
});

async function loadMine() {
  try {
    const reports = await api('reports/mine');
    $('my-reports').replaceChildren(...(reports.length ? reports.map(report => {
      const item = el('article', 'item');
      item.append(el('span', 'tag ' + (report.status === 'published' ? 'verified' : 'warning'), report.statusLabel),
        el('h3', '', report.type), el('p', '', report.location + ' · ' + readableDate(report.date)),
        el('p', '', report.description));
      if (report.review) item.append(el('p', 'meta', 'Revisão · ' + report.review));
      return item;
    }) : [el('p', 'meta', 'Você ainda não tem ocorrências registradas neste navegador.')]));
  } catch (error) { $('my-reports').textContent = error.message; }
}

$('report-form').addEventListener('submit', event => {
  event.preventDefault();
  const form = event.currentTarget;
  busy(form, async () => {
    if (!reportPosition) return feedback('report-status', 'Selecione um ponto pela busca, localização ou mapa.', true);
    try {
      feedback('report-status', 'Enviando ocorrência…');
      const photo = await photoData($('report-photo').files[0]);
      await api('reports', { method: 'POST', body: {
        type: $('report-type').value, location: $('report-location').value.trim(), position: reportPosition,
        date: $('report-date').value, description: $('report-description').value, photo
      } });
      form.reset();
      $('report-date').value = today();
      reportPosition = undefined;
      feedback('report-point');
      feedback('report-status', 'Ocorrência enviada. Você pode acompanhar a análise ao lado.');
      loadMine();
    } catch (error) { feedback('report-status', error.message, true); }
  });
});

function moderationField(label, control) {
  const field = el('label', 'field', label);
  field.append(control);
  return field;
}

function moderationCard(report) {
  const form = el('form', 'panel info-card form-stack');
  const note = el('textarea');
  note.required = true;
  note.minLength = 5;
  note.maxLength = 600;
  note.rows = 2;
  note.value = report.review || '';
  const type = el('select');
  content.reportTypes.forEach(value => type.add(new Option(value, value)));
  type.value = report.type;
  const location = el('input');
  location.value = report.location;
  location.required = true;
  location.maxLength = 150;
  const description = el('textarea');
  description.value = report.description;
  description.required = true;
  description.minLength = 10;
  description.maxLength = 600;
  description.rows = 3;
  const decision = el('select');
  for (const [label, value] of [['Selecione', ''], ['Publicar', 'published'], ['Rejeitar', 'rejected']]) decision.add(new Option(label, value));
  decision.required = true;
  form.append(el('h3', '', report.statusLabel), el('p', 'meta', readableDate(report.date) + ' · ' + coordinates(report.position)),
    moderationField('Tipo', type), moderationField('Local', location), moderationField('Descrição', description));
  if (report.photo) {
    const photo = el('img', 'moderator-photo');
    photo.alt = 'Foto anexada à ocorrência';
    photo.src = report.photo;
    form.append(photo);
  }
  const submit = el('button', 'button primary', 'Salvar revisão');
  submit.type = 'submit';
  form.append(moderationField('Decisão', decision), moderationField('Motivo da revisão', note), submit);
  form.addEventListener('submit', event => {
    event.preventDefault();
    busy(form, async () => {
      try {
        await api('moderation/reports/' + report.id, { method: 'PATCH', key: moderatorKey, body: {
          status: decision.value, review: note.value, updated: report.updated,
          fields: { type: type.value, location: location.value, description: description.value }
        } });
        await loadModeration();
        feedback('moderation-status', 'Revisão salva.');
        clearRoute();
        loadPublicReports();
      } catch (error) { feedback('moderation-status', error.message, true); }
    });
  });
  return form;
}

function suggestionReviewCard(place) {
  const form = el('form', 'panel info-card form-stack');
  const review = el('textarea');
  review.required = true;
  review.minLength = 5;
  review.maxLength = 600;
  review.value = place.review || '';
  const status = el('select');
  for (const [label, value] of [['Selecione', ''], ['Publicar', 'published'], ['Rejeitar', 'rejected']]) status.add(new Option(label, value));
  status.required = true;
  form.append(el('span', 'tag', place.statusLabel), el('h3', '', place.name), el('p', 'meta', place.address),
    el('p', 'meta', place.resources.map(resource => content.resources[resource]).join(' · ')),
    el('p', '', place.description));
  if (place.photo) {
    const preview = el('img', 'moderator-photo');
    preview.src = place.photo;
    preview.alt = 'Foto anexada à sugestão';
    form.append(preview);
  }
  const submit = el('button', 'button primary', 'Salvar revisão da sugestão');
  submit.type = 'submit';
  form.append(moderationField('Decisão', status), moderationField('Motivo da revisão', review), submit);
  form.addEventListener('submit', event => {
    event.preventDefault();
    busy(form, async () => {
      try {
        await api('moderation/suggestions/' + place.id, { method: 'PATCH', key: moderatorKey,
          body: { status: status.value, review: review.value, updated: place.updated } });
        const updated = await api('content');
        content.places = updated.places;
        refreshMapPlaces();
        renderPlaces();
        renderTransport();
        await loadModeration();
        feedback('moderation-status', 'Revisão da sugestão salva.');
      } catch (error) { feedback('moderation-status', error.message, true); }
    });
  });
  return form;
}

async function loadModeration() {
  const [reports, submitted] = await Promise.all([
    api('moderation/reports', { key: moderatorKey }),
    api('moderation/suggestions', { key: moderatorKey })
  ]);
  $('moderation-list').replaceChildren(...(reports.length ? reports.map(moderationCard) : [el('p', 'meta', 'Nenhuma ocorrência para revisar.')]));
  $('suggest-moderation-list').replaceChildren(...(submitted.length ? submitted.map(suggestionReviewCard) : [el('p', 'meta', 'Nenhuma sugestão para revisar.')]));
}

$('moderation-form').addEventListener('submit', event => {
  event.preventDefault();
  busy(event.currentTarget, async () => {
    moderatorKey = $('moderator-key').value;
    try {
      await loadModeration();
      $('moderator-key').value = '';
      feedback('moderation-status', 'Fila carregada.');
    } catch (error) {
      moderatorKey = undefined;
      $('moderation-list').replaceChildren();
      $('suggest-moderation-list').replaceChildren();
      feedback('moderation-status', error.message, true);
    }
  });
});

async function init() {
  window.addEventListener('hashchange', renderView);
  $('report-date').value = today();
  $('report-date').max = today();
  loadProfile();
  renderView();
  try {
    content = await api('content');
    $('moderation-link').hidden = !content.moderationEnabled;
    content.reportTypes.forEach(type => $('report-type').add(new Option(type, type)));
    for (const category of [...content.categories].sort((a, b) => a.localeCompare(b, 'pt-BR'))) {
      $('place-category').add(new Option(category, category));
      $('suggest-category').add(new Option(category, category));
    }
    const panels = {
      'place-filters': { ...content.resources, verified: 'Informação verificada', benefit: 'Com gratuidade ou desconto', covered: 'Local coberto' },
      'suggest-resources': content.resources
    };
    for (const [panel, resources] of Object.entries(panels)) {
      for (const [value, name] of Object.entries(resources)) {
        const label = el('label', 'check');
        const check = el('input');
        check.type = 'checkbox';
        check.value = value;
        label.append(check, name);
        $(panel).append(label);
      }
    }
    refreshMapPlaces();
    renderPlaces();
    renderBenefits();
    renderTransport();
  } catch (error) {
    const notice = el('p', 'feedback error', 'Não foi possível carregar a base do IncluiSP. Recarregue a página para tentar novamente.');
    notice.setAttribute('role', 'alert');
    $('main').prepend(notice);
  }
}

init();
