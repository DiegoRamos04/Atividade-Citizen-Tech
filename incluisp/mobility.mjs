export const normalize = (value = '') => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

export function isSaoPauloPoint(point) {
  return Array.isArray(point) && point.length === 2 &&
    point.every(Number.isFinite) && point[0] >= -24 && point[0] <= -23.32 &&
    point[1] >= -46.84 && point[1] <= -46.35;
}

export function lookupAnswer(question, knowledge) {
  const text = normalize(question);
  const asksForRoute = /\b(como (chego|chegar|vou|ir)|tracar (uma )?rota|melhor (rota|caminho)|qual (a |o )?(rota|caminho))\b/.test(text);
  const scored = knowledge.map(entry => ({
    entry,
    score: entry.topics.reduce((sum, topic) => {
      const term = normalize(topic);
      const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return sum + (new RegExp(`(^|[^a-z0-9])${escaped}(?=[^a-z0-9]|$)`).test(text) ? term.length + 3 : 0);
    }, 0)
  })).filter(result => result.score > 0).sort((a, b) => (b.entry.priority || 0) - (a.entry.priority || 0) || b.score - a.score);
  const match = scored[0]?.entry;
  if (match && (match.priority || !asksForRoute)) {
    const { answer, sources, action } = match;
    return { answer, sources, action };
  }
  if (asksForRoute) {
    return { answer: 'Abra Rotas e mapa e informe a origem e o destino. O planejador mostra os percursos retornados pelo serviço, as barreiras documentadas nas proximidades e o que ainda precisa ser confirmado.', sources: [], action: 'routes' };
  }
  return {
    answer: 'A base do IncluiSP ainda não tem informação suficiente para responder a essa pergunta. Tente informar o nome do local, da estação ou do serviço. Você também pode consultar os canais oficiais em Transporte e ajuda.',
    sources: [], action: 'transport'
  };
}

export function decodeShape(encoded) {
  if (typeof encoded !== 'string' || encoded.length > 750000) throw new Error('Geometria inválida.');
  let index = 0;
  let lat = 0;
  let lng = 0;
  const points = [];
  const next = () => {
    let result = 0;
    for (let shift = 0; shift < 32; shift += 5) {
      const byte = encoded.charCodeAt(index++) - 63;
      if (!Number.isInteger(byte) || byte < 0 || byte > 63) throw new Error('Geometria inválida.');
      result |= (byte & 31) << shift;
      if (byte < 32) return (result & 1) ? ~(result >> 1) : result >> 1;
    }
    throw new Error('Geometria inválida.');
  };
  while (index < encoded.length) {
    lat += next();
    lng += next();
    points.push([lat / 1e6, lng / 1e6]);
  }
  if (points.length < 2 || !points.every(isSaoPauloPoint)) throw new Error('Geometria indisponível em São Paulo.');
  return points;
}

function segmentDistance(point, start, end) {
  const metersPerDegree = 111195;
  const longitudeScale = Math.cos(point[0] * Math.PI / 180);
  const x = (start[1] - point[1]) * longitudeScale;
  const y = start[0] - point[0];
  const dx = (end[1] - start[1]) * longitudeScale;
  const dy = end[0] - start[0];
  const length = dx * dx + dy * dy;
  const ratio = length ? Math.max(0, Math.min(1, -(x * dx + y * dy) / length)) : 0;
  return Math.hypot(x + ratio * dx, y + ratio * dy) * metersPerDegree;
}

export function classifyRoute(points, reports) {
  const barriers = reports.filter(report =>
    report.status === 'published' && points.some((end, i) =>
      i > 0 && segmentDistance(report.position, points[i - 1], end) <= 25)
  );
  return {
    status: barriers.length ? 'Rota com barreiras identificadas' : 'Rota com informações insuficientes',
    barriers
  };
}

export function parseRoutes(response, reports, profile = {}) {
  const trips = [response.trip, ...(response.alternates || []).map(item => item.trip)];
  const routes = trips.filter(trip => trip?.legs?.length && Number.isFinite(trip.summary?.length) &&
    trip.summary.length > 0 && Number.isFinite(trip.summary.time)).map(trip => {
    const points = trip.legs.flatMap(leg => decodeShape(leg.shape));
    const meters = Math.round(trip.summary.length * 1000);
    return {
      geometry: points,
      meters,
      minutes: Math.max(1, Math.round(trip.summary.time / 60)),
      ...classifyRoute(points, reports),
      exceedsDistance: Boolean(profile.maxDistance && meters > profile.maxDistance),
      steps: trip.legs.flatMap(leg => (leg.maneuvers || []).map(step => step.instruction).filter(Boolean))
    };
  });
  return routes.sort((a, b) => a.barriers.length - b.barriers.length ||
    Number(a.exceedsDistance) - Number(b.exceedsDistance) ||
    (profile.preference === 'short' ? a.meters - b.meters : 0));
}
