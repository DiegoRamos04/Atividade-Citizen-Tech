import { createServer } from 'node:http';
import { randomUUID, timingSafeEqual } from 'node:crypto';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, dirname, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DatabaseSync } from 'node:sqlite';
import base from './data/base.json' with { type: 'json' };
import transit from './data/transit.json' with { type: 'json' };
import { isSaoPauloPoint, lookupAnswer, normalize, parseRoutes } from './mobility.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const statusCodes = { pending: 'Em análise', published: 'Publicado', rejected: 'Rejeitado' };
const photoOrigins = [...new Set([...base.places, ...base.benefits]
  .filter(item => item.photo?.url?.startsWith('https://'))
  .map(item => new URL(item.photo.url).origin))].join(' ');
const transitDirectory = Object.fromEntries(Object.entries(transit).map(([mode, rows]) => [mode,
  rows.map(([name, lat, lon, detail, address]) => ({
    item: { name, position: [lat, lon], detail: mode === 'bus' ? 'Código ' + detail : detail, address },
    search: normalize([name, detail, address].join(' '))
  }))
]));

function fail(status, message) {
  throw Object.assign(new Error(message), { status });
}

async function readJSON(request) {
  if (!request.headers['content-type']?.startsWith('application/json')) fail(415, 'Envie dados em JSON.');
  if (Number(request.headers['content-length']) > 2900000) fail(413, 'O envio excede o tamanho permitido.');
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 2900000) fail(413, 'O envio excede o tamanho permitido.');
    chunks.push(chunk);
  }
  try {
    const body = JSON.parse(Buffer.concat(chunks));
    if (body && typeof body === 'object' && !Array.isArray(body)) return body;
  } catch {}
  fail(400, 'O conteúdo enviado é inválido.');
}

function reportFields(data) {
  const { type, position, description, location, date } = data;
  if (!base.reportTypes.includes(type) || !isSaoPauloPoint(position) ||
      typeof description !== 'string' || description.trim().length < 10 || description.length > 600 ||
      typeof location !== 'string' || !location.trim() || location.length > 150 ||
      typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) ||
      new Date(date).toISOString().slice(0, 10) !== date ||
      date > new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' }).format()) {
    fail(422, 'Confira o tipo, a localização em São Paulo, a data e a descrição, que deve ter entre 10 e 600 caracteres.');
  }
  return { type, position, description: description.trim(), location: location.trim(), date };
}

function validatePhoto(photo) {
  if (!photo) return null;
  const match = typeof photo === 'string' && /^data:image\/(jpeg|png|webp);base64,([\w+/]+={0,2})$/.exec(photo);
  if (!match || match[2].length > 2796204) fail(422, 'Use uma imagem JPG, PNG ou WebP de até 2 MB.');
  const bytes = Buffer.from(match[2], 'base64');
  const valid = {
    jpeg: bytes.subarray(0, 3).equals(Buffer.from([255, 216, 255])),
    png: bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])),
    webp: bytes.toString('ascii', 0, 4) === 'RIFF' && bytes.toString('ascii', 8, 12) === 'WEBP'
  };
  if (!valid[match[1]]) fail(422, 'O formato da imagem é inválido.');
  return photo;
}

function readReport(row, audience = 'public') {
  const { photo, ...details } = JSON.parse(row.payload);
  return { ...details, id: row.id, status: row.status, statusLabel: statusCodes[row.status],
    ...(audience !== 'public' && { review: row.review }), ...(audience === 'moderator' && { photo }),
    updated: row.updated };
}

function suggestionFields({ name, address, category, position, description, resources = [] }) {
  const validText = (value, min, max) => typeof value === 'string' && value.trim().length >= min && value.length <= max;
  if (!validText(name, 3, 100) || !validText(address, 3, 150) || !validText(description, 10, 600) ||
      !base.categories.includes(category) || !isSaoPauloPoint(position) || !Array.isArray(resources) ||
      resources.length > Object.keys(base.resources).length || resources.some(resource => !Object.hasOwn(base.resources, resource))) {
    fail(422, 'Confira o nome, a categoria, o ponto no mapa e a descrição do local.');
  }
  return { name: name.trim(), address: address.trim(), category, position, description: description.trim(), resources: [...new Set(resources)] };
}

function publicSuggestion(row) {
  const { photo, ...place } = JSON.parse(row.payload);
  return { ...place, id: row.id, community: true, hasPhoto: Boolean(photo) };
}

async function loadProvider(url, options) {
  const result = await fetch(url, { ...options, signal: AbortSignal.timeout(8500) });
  if (!result.ok) throw new Error(`Resposta externa ${result.status}`);
  return result.json();
}

export async function makeServer({
  database = process.env.INCLUISP_DB || resolve(root, '.local/incluisp.sqlite'),
  moderatorKey = process.env.INCLUISP_MODERATOR_KEY || '',
  valhalla = process.env.INCLUISP_VALHALLA || 'https://valhalla1.openstreetmap.de/route',
  photon = process.env.INCLUISP_PHOTON || 'https://photon.komoot.io/api/',
  provider = loadProvider
} = {}) {
  if (database !== ':memory:') await mkdir(dirname(database), { recursive: true });
  const db = new DatabaseSync(database);
  db.exec(`PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS reports (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
      review TEXT, updated TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS reports_status_updated ON reports(status, updated);
    CREATE INDEX IF NOT EXISTS reports_owner_updated ON reports(owner, updated);
    CREATE TABLE IF NOT EXISTS suggestions (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL,
      review TEXT, updated TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS suggestions_status_updated ON suggestions(status, updated);
    CREATE INDEX IF NOT EXISTS suggestions_owner_updated ON suggestions(owner, updated);`);
  const listPublished = () => db.prepare("SELECT * FROM reports WHERE status='published' ORDER BY updated DESC").all().map(row => readReport(row));
  const catalog = () => [...base.places,
    ...db.prepare("SELECT * FROM suggestions WHERE status='published' ORDER BY updated DESC").all().map(publicSuggestion)];

  const server = createServer(async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    res.setHeader('Content-Security-Policy', `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https://tile.openstreetmap.org ${photoOrigins}; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'self'`);
    res.setHeader('Permissions-Policy', 'geolocation=(self)');
    const json = (status, data) => {
      res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify(data));
    };
    try {
      const url = new URL(req.url, 'http://localhost');
      const pathname = decodeURIComponent(url.pathname);
      const method = req.method;
      const session = /(?:^|;\s*)incluisp=([\da-f-]{36})(?:;|$)/.exec(req.headers.cookie || '')?.[1];
      const setOwner = () => {
        if (session) return session;
        const owner = randomUUID();
        res.setHeader('Set-Cookie', `incluisp=${owner}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000${req.socket.encrypted ? '; Secure' : ''}`);
        return owner;
      };
      if (pathname.startsWith('/api/') && ['POST', 'PATCH'].includes(method) && req.headers.origin &&
          new URL(req.headers.origin).host !== req.headers.host) fail(403, 'Origem da solicitação inválida.');

      if (method === 'GET' && pathname === '/api/content') {
        const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Sao_Paulo' }).format();
        const guides = base.knowledge.filter(entry => entry.guide).map(({ guide, answer, sources }) => ({ guide, answer, sources }));
        return json(200, { ...base, places: catalog(), knowledge: undefined, guides, moderationEnabled: Boolean(moderatorKey),
          benefits: base.benefits.filter(benefit => !benefit.expires || benefit.expires >= today) });
      }
      if (method === 'POST' && pathname === '/api/assistant') {
        const { question } = await readJSON(req);
        if (typeof question !== 'string' || !question.trim() || question.length > 400) fail(422, 'Envie uma pergunta com até 400 caracteres.');
        return json(200, lookupAnswer(question, base.knowledge));
      }
      if (method === 'GET' && pathname === '/api/transit') {
        const mode = url.searchParams.get('mode') || 'metro';
        const page = Number(url.searchParams.get('page') || 0);
        const query = normalize((url.searchParams.get('q') || '').slice(0, 150));
        if (!Object.hasOwn(transitDirectory, mode) || !Number.isSafeInteger(page) || page < 0) {
          fail(422, 'Selecione um tipo de local e uma página válidos.');
        }
        const matches = query ? transitDirectory[mode].filter(entry => entry.search.includes(query)) : transitDirectory[mode];
        const pageSize = 20;
        const offset = page * pageSize;
        return json(200, { total: matches.length, start: offset + 1, hasNext: offset + pageSize < matches.length,
          items: matches.slice(offset, offset + pageSize).map(entry => entry.item) });
      }
      if (method === 'GET' && pathname === '/api/search') {
        const query = (url.searchParams.get('q') || '').trim().slice(0, 150);
        if (query.length < 3) fail(422, 'Digite pelo menos 3 caracteres para buscar.');
        const term = normalize(query);
        const results = catalog().map(place => {
          const title = normalize([place.name, ...(place.aliases || [])].join(' '));
          return { place, rank: title.includes(term) ? 2 : normalize(place.address).includes(term) ? 1 : 0 };
        }).filter(result => result.rank).sort((a, b) => b.rank - a.rank).map(result => result.place);
        if (results.length) return json(200, results);
        const target = new URL(photon);
        target.search = new URLSearchParams({ q: query, limit: '6', bbox: '-46.84,-24,-46.35,-23.32', lat: '-23.55', lon: '-46.63' });
        try {
          const { features } = await provider(target);
          return json(200, features.filter(feature => isSaoPauloPoint(feature.geometry?.coordinates?.slice().reverse())).map((feature, index) => {
            const props = feature.properties;
            return { id: `search-${index}`, name: props.name || [props.street, props.housenumber].filter(Boolean).join(', ') || 'Endereço em São Paulo',
              address: [...new Set([props.street, props.housenumber, props.district || props.suburb, props.city].filter(Boolean))].join(', '),
              position: feature.geometry.coordinates.slice().reverse() };
          }));
        } catch {
          fail(503, 'A busca externa está indisponível. Selecione um local do catálogo ou marque um ponto no mapa.');
        }
      }
      if (method === 'POST' && pathname === '/api/routes') {
        const { origin, destination, profile } = await readJSON(req);
        if (!isSaoPauloPoint(origin) || !isSaoPauloPoint(destination)) fail(422, 'Selecione origem e destino em São Paulo.');
        if (Math.hypot(origin[0] - destination[0], origin[1] - destination[1]) < 0.00005) fail(422, 'Selecione dois pontos diferentes.');
        const wheelchair = ['manual', 'motorized'].includes(profile?.mobility);
        const mobility = wheelchair || profile?.avoidStairs === true ? 'wheelchair' : 'foot';
        const options = { type: mobility, use_hills: profile?.preference === 'flat' ? 0 : 0.5, shortest: profile?.preference === 'short' };
        try {
          const routeData = await provider(valhalla, { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ locations: [origin, destination].map(([lat, lon]) => ({ lat, lon })),
              costing: 'pedestrian', costing_options: { pedestrian: options }, units: 'kilometers', language: 'pt-BR', alternates: 2 }) });
          const routes = parseRoutes(routeData, listPublished(), profile || {});
          if (routes.length) return json(200, { routes, source: 'Valhalla · OpenStreetMap', url: 'https://www.openstreetmap.org/copyright' });
        } catch (error) {
          console.warn('Roteamento indisponível:', error.message);
        }
        fail(503, 'Não foi possível obter um percurso de ruas para esses pontos. Revise a origem e o destino ou tente novamente mais tarde.');
      }
      if (method === 'GET' && pathname === '/api/reports') return json(200, listPublished());
      if (method === 'GET' && pathname === '/api/reports/mine') {
        const rows = session ? db.prepare('SELECT * FROM reports WHERE owner=? ORDER BY updated DESC').all(session) : [];
        return json(200, rows.map(row => readReport(row, 'owner')));
      }
      if (method === 'POST' && pathname === '/api/reports') {
        const data = await readJSON(req);
        const report = { ...reportFields(data), photo: validatePhoto(data.photo) };
        const owner = setOwner();
        const id = randomUUID();
        const updated = new Date().toISOString();
        db.prepare("INSERT INTO reports (id, owner, status, payload, updated) VALUES (?, ?, 'pending', ?, ?)").run(id, owner, JSON.stringify(report), updated);
        return json(201, { id, status: 'pending', statusLabel: statusCodes.pending });
      }
      if (method === 'GET' && pathname === '/api/suggestions/mine') {
        const rows = session ? db.prepare('SELECT * FROM suggestions WHERE owner=? ORDER BY updated DESC').all(session) : [];
        return json(200, rows.map(row => readReport(row, 'owner')));
      }
      if (method === 'POST' && pathname === '/api/suggestions') {
        const data = await readJSON(req);
        const place = { ...suggestionFields(data), photo: validatePhoto(data.photo) };
        const id = randomUUID();
        db.prepare("INSERT INTO suggestions (id, owner, status, payload, updated) VALUES (?, ?, 'pending', ?, ?)")
          .run(id, setOwner(), JSON.stringify(place), new Date().toISOString());
        return json(201, { id, status: 'pending', statusLabel: statusCodes.pending });
      }
      const suggestionPhoto = /^\/api\/suggestions\/([\da-f-]{36})\/photo$/.exec(pathname);
      if (method === 'GET' && suggestionPhoto) {
        const row = db.prepare("SELECT payload FROM suggestions WHERE id=? AND status='published'").get(suggestionPhoto[1]);
        const photo = row && JSON.parse(row.payload).photo;
        if (!photo) fail(404, 'Foto indisponível.');
        const [, format, bytes] = /^data:image\/(jpeg|png|webp);base64,(.+)$/.exec(photo);
        res.writeHead(200, { 'Content-Type': 'image/' + format, 'Cache-Control': 'no-store' });
        return res.end(Buffer.from(bytes, 'base64'));
      }
      if (pathname.startsWith('/api/moderation/')) {
        if (!moderatorKey) fail(404, 'A moderação está indisponível.');
        const expected = Buffer.from(`Bearer ${moderatorKey}`);
        const current = Buffer.from(req.headers.authorization || '');
        if (expected.length !== current.length || !timingSafeEqual(expected, current)) fail(401, 'Chave de moderação inválida.');
        if (method === 'GET' && pathname === '/api/moderation/reports') {
          return json(200, db.prepare('SELECT * FROM reports ORDER BY updated DESC').all().map(row => readReport(row, 'moderator')));
        }
        if (method === 'GET' && pathname === '/api/moderation/suggestions') {
          return json(200, db.prepare('SELECT * FROM suggestions ORDER BY updated DESC').all().map(row => readReport(row, 'moderator')));
        }
        const suggestionReview = /^\/api\/moderation\/suggestions\/([\da-f-]{36})$/.exec(pathname);
        if (method === 'PATCH' && suggestionReview) {
          const { status, review, updated } = await readJSON(req);
          if (!['published', 'rejected'].includes(status) || typeof review !== 'string' ||
              review.trim().length < 5 || review.length > 600 || typeof updated !== 'string') {
            fail(422, 'Informe a decisão e o motivo da revisão.');
          }
          const id = suggestionReview[1];
          const changes = db.prepare('UPDATE suggestions SET status=?, review=?, updated=? WHERE id=? AND updated=?')
            .run(status, review.trim(), new Date().toISOString(), id, updated).changes;
          if (!changes) fail(409, 'Recarregue a fila antes de revisar a sugestão.');
          return json(200, { id, status, statusLabel: statusCodes[status] });
        }
        if (method === 'PATCH' && pathname.startsWith('/api/moderation/reports/')) {
          const id = pathname.split('/').at(-1);
          const data = await readJSON(req);
          if (!['published', 'rejected'].includes(data.status) || typeof data.review !== 'string' ||
              data.review.trim().length < 5 || data.review.length > 600 || typeof data.updated !== 'string') fail(422, 'Informe a decisão, o motivo e a versão da revisão.');
          const existing = db.prepare('SELECT * FROM reports WHERE id=?').get(id);
          if (!existing) fail(404, 'Ocorrência não encontrada.');
          const original = JSON.parse(existing.payload);
          const corrected = data.fields ? reportFields({ ...original, ...data.fields }) : original;
          const updated = new Date().toISOString();
          const result = db.prepare('UPDATE reports SET status=?, payload=?, review=?, updated=? WHERE id=? AND updated=?')
            .run(data.status, JSON.stringify({ ...corrected, photo: original.photo }), data.review.trim(), updated, id, data.updated);
          if (!result.changes) fail(409, 'A ocorrência foi revisada em outra sessão. Recarregue a fila.');
          return json(200, { id, status: data.status, statusLabel: statusCodes[data.status] });
        }
      }
      if (pathname.startsWith('/api/')) fail(404, 'Operação não encontrada.');
      if (!['GET', 'HEAD'].includes(method)) fail(405, 'Método inválido.');

      const staticFiles = {
        '/': 'public/index.html', '/app.js': 'public/app.js', '/style.css': 'public/style.css',
        '/vendor/leaflet.js': 'node_modules/leaflet/dist/leaflet.js',
        '/vendor/leaflet.css': 'node_modules/leaflet/dist/leaflet.css',
        '/vendor/instrument.woff2': 'node_modules/@fontsource-variable/instrument-sans/files/instrument-sans-latin-wght-normal.woff2'
      };
      const icon = /^\/icons\/([a-z0-9-]+\.svg)$/.exec(pathname);
      const photo = /^\/photos\/[a-z0-9-]+\.(?:jpg|png)$/.test(pathname);
      const image = /^\/vendor\/images\/(layers(?:-2x)?\.png|marker-icon(?:-2x)?\.png|marker-shadow\.png)$/.exec(pathname);
      const file = staticFiles[pathname] || (icon && `node_modules/lucide/icons/${icon[1]}`) ||
        (photo && `public${pathname}`) || (image && `node_modules/leaflet/dist/images/${image[1]}`);
      if (!file) fail(404, 'Arquivo não encontrado.');
      const contents = await readFile(resolve(root, file)).catch(() => fail(404, 'Arquivo não encontrado.'));
      res.writeHead(200, { 'Content-Type': mime[extname(file)], 'Content-Length': contents.length, 'Cache-Control': 'no-cache' });
      res.end(method === 'HEAD' ? undefined : contents);
    } catch (error) {
      if (!error.status) console.error(error);
      if (!res.headersSent) json(error.status || 500, { error: error.status ? error.message : 'Não foi possível concluir a operação.' });
    }
  });
  server.on('close', () => db.close());
  return server;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = await makeServer();
  const host = process.env.HOST || '127.0.0.1';
  server.listen(Number(process.env.PORT || 3000), host, () => console.log(`IncluiSP disponível em http://${host}:${server.address().port}`));
}
