import { test } from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { makeServer } from '../server.mjs';
import { classifyRoute, decodeShape } from '../mobility.mjs';

const origin = [-23.55815, -46.66032];
const middle = [-23.55975, -46.65800];
const destination = [-23.56138, -46.65614];
const date = '2025-01-01';

// Valhalla encodes coordinate deltas at six decimal places.
function encode(points) {
  let previous = [0, 0];
  return points.map(point => {
    const scaled = point.map(coordinate => Math.round(coordinate * 1e6));
    const encoded = scaled.map((coordinate, index) => {
      const delta = coordinate - previous[index];
      let value = delta < 0 ? ~(delta << 1) : delta << 1;
      let result = '';
      while (value >= 32) {
        result += String.fromCharCode((32 | (value & 31)) + 63);
        value >>= 5;
      }
      return result + String.fromCharCode(value + 63);
    }).join('');
    previous = scaled;
    return encoded;
  }).join('');
}

async function start(t, config = {}) {
  const server = await makeServer({ database: ':memory:', moderatorKey: 'test-key', ...config });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => server.close(resolve)));
  return (path, { method = 'GET', data, cookie, moderator = false } = {}) =>
    fetch('http://127.0.0.1:' + server.address().port + '/api/' + path, {
      method,
      headers: {
        ...(data && { 'Content-Type': 'application/json' }),
        ...(cookie && { Cookie: cookie }),
        ...(moderator && { Authorization: 'Bearer test-key' })
      },
      body: data && JSON.stringify(data)
    });
}

test('a geometria de rua preserva os pontos e a cobertura desconhecida', () => {
  const points = [origin, middle, destination];
  assert.deepEqual(decodeShape(encode(points)), points);
  assert.throws(() => decodeShape('_'));
  assert.equal(classifyRoute(points, []).status, 'Rota com informações insuficientes');
  const near = { position: [-23.559, -46.6591], status: 'published' };
  const far = { position: [-23.57, -46.65], status: 'published' };
  const pending = { position: middle, status: 'pending' };
  assert.deepEqual(classifyRoute(points, [far, pending, near]).barriers, [near]);
});

test('planejador consulta o perfil do provedor e retorna alternativas reais ou uma limitação', async t => {
  const trip = {
    summary: { length: 0.68, time: 585 },
    legs: [{ shape: encode([origin, middle, destination]), maneuvers: [{ instruction: 'Siga pela Avenida Paulista.' }] }]
  };
  const request = await start(t, {
    provider: async (url, options) => {
      const payload = JSON.parse(options.body);
      if (payload.locations[0].lat === destination[0]) return {};
      assert.deepEqual(payload.costing_options.pedestrian, { type: 'wheelchair', use_hills: 0, shortest: false });
      return { trip, alternates: [{ trip: { ...trip, summary: { length: 0.85, time: 650 } } }] };
    }
  });
  const data = { origin, destination, profile: { avoidStairs: true, preference: 'flat', maxDistance: 700 } };
  const response = await request('routes', { method: 'POST', data });
  assert.equal(response.status, 200);
  const { routes, source } = await response.json();
  assert.match(source, /Valhalla/);
  assert.deepEqual(routes.map(route => route.meters), [680, 850]);
  assert.deepEqual(routes.map(route => route.exceedsDistance), [false, true]);
  assert.deepEqual(routes[0].geometry, [origin, middle, destination]);
  assert.deepEqual(routes[0].steps, ['Siga pela Avenida Paulista.']);
  const unavailable = await request('routes', { method: 'POST', data: { origin: destination, destination: origin } });
  assert.equal(unavailable.status, 503);
  assert.equal((await unavailable.json()).routes, undefined);
  assert.equal((await request('routes', { method: 'POST', data: { origin, destination: origin } })).status, 422);
});

test('busca local, geocodificação em São Paulo e respostas documentadas', async t => {
  const request = await start(t, { provider: async target => {
    assert.equal(target.searchParams.get('lang'), null);
    return { features: [
      { geometry: { coordinates: [-46.63, -23.55] }, properties: { name: 'Mercado Municipal', city: 'São Paulo' } },
      { geometry: { coordinates: [0, 0] }, properties: { name: 'Fora da cidade' } }
    ] };
  } });
  const content = await (await request('content')).json();
  assert.ok(content.places.some(place => place.resources.includes('restroom') && place.url.startsWith('https:')));
  assert.ok(content.places.every(({ photo }) =>
    photo?.alt && photo.credit && (!photo.url || photo.sourceUrl)));
  assert.ok(content.benefits.every(benefit => benefit.photo?.alt && benefit.url));
  assert.ok(content.benefits.some(benefit => benefit.id === 'bilhete'));
  assert.equal((await (await request('search?q=consolacao')).json())[0].id, 'consolacao');
  assert.deepEqual((await (await request('search?q=mercado')).json()).map(place => place.name), ['Mercado Municipal']);
  const ask = async question => (await (await request('assistant', { method: 'POST', data: { question } })).json());
  const answer = await ask('Como pedir o bilhete único?');
  assert.match(answer.sources[0].url, /www\.sptrans\.com\.br/);
  assert.equal((await ask('Quais são os horários em Marte?')).sources.length, 0);
  assert.equal((await ask('Como chego à Avenida Paulista?')).action, 'routes');
});

test('ocorrências pendentes são privadas até a revisão com chave', async t => {
  const request = await start(t);
  const payload = { type: 'Rampa bloqueada', location: 'Av. Paulista', position: origin, date, description: 'Descrição de teste do fluxo.' };
  assert.equal((await request('reports', { method: 'POST', data: { ...payload, date: '2025-02-31' } })).status, 422);
  assert.equal((await request('reports', { method: 'POST', data: { ...payload, photo: 'data:image/png;base64,aGVsbG8=' } })).status, 422);
  const photo = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jrXYAAAAASUVORK5CYII=';
  const created = await request('reports', { method: 'POST', data: { ...payload, photo } });
  assert.equal(created.status, 201);
  const cookie = created.headers.get('set-cookie').split(';')[0];
  const { id } = await created.json();
  assert.deepEqual(await (await request('reports')).json(), []);
  assert.deepEqual(await (await request('reports/mine')).json(), []);
  const [pending] = await (await request('reports/mine', { cookie })).json();
  assert.equal(pending.statusLabel, 'Em análise');
  assert.equal(pending.photo, undefined);
  assert.equal((await request('moderation/reports')).status, 401);
  const [reviewItem] = await (await request('moderation/reports', { moderator: true })).json();
  assert.equal(reviewItem.photo, photo);
  const review = { status: 'published', review: 'Revisão de teste.', updated: reviewItem.updated, fields: { location: 'Av. Paulista, 100' } };
  assert.equal((await request('moderation/reports/' + id, { method: 'PATCH', moderator: true, data: review })).status, 200);
  const [published] = await (await request('reports')).json();
  assert.equal(published.location, review.fields.location);
  assert.equal(published.photo, undefined);
  assert.equal(published.review, undefined);
  assert.equal((await request('moderation/reports/' + id, { method: 'PATCH', moderator: true, data: review })).status, 409);
  assert.equal((await request('moderation/reports/' + id, { method: 'PATCH', moderator: true,
    data: { ...review, status: 'rejected', updated: published.updated } })).status, 200);
  assert.deepEqual(await (await request('reports')).json(), []);
});

test('catálogo publica uma sugestão e sua foto apenas após revisão', async t => {
  const request = await start(t);
  const payload = { name: 'Biblioteca de teste', address: 'Av. Paulista, 100', category: 'Biblioteca',
    description: 'A entrada da biblioteca tem rampa.', position: origin, resources: ['ramp'],
    photo: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jrXYAAAAASUVORK5CYII=' };
  const created = await request('suggestions', { method: 'POST', data: payload });
  assert.equal(created.status, 201);
  const cookie = created.headers.get('set-cookie').split(';')[0];
  const { id } = await created.json();
  assert.deepEqual(await (await request('suggestions/mine')).json(), []);
  const [mine] = await (await request('suggestions/mine', { cookie })).json();
  assert.equal(mine.status, 'pending');
  assert.equal(mine.photo, undefined);
  assert.equal((await request('suggestions/' + id + '/photo')).status, 404);
  const moderation = 'moderation/suggestions/' + id;
  const decision = { status: 'published', review: 'Verificado no local.', updated: mine.updated };
  assert.equal((await request(moderation, { method: 'PATCH', data: decision })).status, 401);
  assert.equal((await request(moderation, { method: 'PATCH', moderator: true, data: decision })).status, 200);
  const place = (await (await request('content')).json()).places.find(entry => entry.id === id);
  assert.equal(place.community, true);
  assert.equal(place.hasPhoto, true);
  assert.equal(place.photo, undefined);
  assert.equal((await request('suggestions/' + id + '/photo')).headers.get('content-type'), 'image/png');
  assert.equal((await (await request('search?q=biblioteca%20de%20teste')).json())[0].id, id);
});

test('busca paginada inclui rede de metrô e paradas, e o assistente prioriza orientação em alagamentos', async t => {
  const request = await start(t);
  const metro = await (await request('transit?mode=metro&q=linha%2017')).json();
  assert.ok(metro.items.some(point => point.name === 'Aeroporto de Congonhas'));
  assert.equal((await (await request('transit?mode=metro&q=linha%206')).json()).total, 6);
  const bus = await (await request('transit?mode=bus&page=1')).json();
  assert.equal(bus.total, 22578);
  assert.equal(bus.start, 21);
  assert.equal(bus.items.length, 20);
  assert.ok(bus.hasNext);
  const rain = await (await request('assistant', { method: 'POST', data: { question: 'Como chego a um abrigo se a rua alagou?' } })).json();
  assert.match(rain.answer, /193/);
  assert.equal(rain.action, 'places');
  const maintenance = await (await request('assistant', { method: 'POST',
    data: { question: 'E se o elevador da estação estiver quebrado?' } })).json();
  assert.match(maintenance.answer, /0800 770 7722/);
  assert.ok(maintenance.sources.some(source => source.url === 'https://www.metro.sp.gov.br/fale-conosco/'));
});
