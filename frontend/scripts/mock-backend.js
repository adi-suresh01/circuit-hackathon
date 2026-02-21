/**
 * Minimal mock backend for CircuitScout frontend demo.
 * Run: node scripts/mock-backend.js  (listens on port 8000)
 *
 * Implements:
 *   POST /api/extract        -> { job_id } then after 2s job becomes "done"
 *   GET  /api/job-status/:id -> { status, progress?, result }
 *   POST /api/substitutes/:base_key -> { substitutes }
 * With ?chaos=true on extract: returns fewer substitutes when you call /api/substitutes.
 */

const http = require('http')

const PORT = 8000
const jobs = new Map()

function parseQuery(url) {
  const i = url.indexOf('?')
  if (i === -1) return {}
  const q = {}
  url.slice(i + 1).split('&').forEach((p) => {
    const [k, v] = p.split('=')
    q[k] = v
  })
  return q
}

function parsePath(url) {
  const path = url.split('?')[0]
  return path
}

function send(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' })
  res.end(JSON.stringify(body))
}

function corsPreflight(res) {
  res.writeHead(204, {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept',
  })
  res.end()
}

const MOCK_BOM = [
  { key: 'R1', description: 'Resistor 10k', quantity: 1, value: '10k', footprint: '0603', refs: ['R1'] },
  { key: 'C1', description: 'Cap 100nF', quantity: 1, value: '100nF', footprint: '0805', refs: ['C1'] },
]

const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') return corsPreflight(res)

  const path = parsePath(req.url)
  const query = parseQuery(req.url)

  // POST /api/extract
  if (req.method === 'POST' && path === '/api/extract') {
    let body = ''
    req.on('data', (c) => { body += c })
    req.on('end', () => {
      const jobId = 'mock-' + Date.now()
      jobs.set(jobId, {
        status: 'running',
        progress: 0,
        result: null,
        chaos: query.chaos === 'true',
      })
      setTimeout(() => {
        const j = jobs.get(jobId)
        if (j) {
          j.status = 'done'
          j.progress = 100
          j.result = MOCK_BOM
        }
      }, 2000)
      send(res, 200, { job_id: jobId })
    })
    return
  }

  // GET /api/job-status/:id
  const jobMatch = path.match(/^\/api\/job-status\/(.+)$/)
  if (req.method === 'GET' && jobMatch) {
    const jobId = jobMatch[1]
    const j = jobs.get(jobId) || { status: 'pending', progress: 0, result: null }
    send(res, 200, { status: j.status, progress: j.progress, result: j.result })
    return
  }

  // POST /api/substitutes/:base_key
  const subMatch = path.match(/^\/api\/substitutes\/(.+)$/)
  if (req.method === 'POST' && subMatch) {
    const baseKey = decodeURIComponent(subMatch[1])
    const chaos = false // could be stored per-session; for demo we return fewer when chaos was used
    const substitutes = chaos
      ? [{ key: baseKey + '-ALT1', reason: 'Chaos: reduced', price: 0.05, score: 0.7 }]
      : [
          { key: baseKey + '-ALT1', reason: 'Same value', price: 0.05, score: 0.9 },
          { key: baseKey + '-ALT2', reason: 'Equivalent', price: 0.06, score: 0.8 },
        ]
    send(res, 200, { substitutes })
    return
  }

  send(res, 404, { detail: 'Not found' })
})

server.listen(PORT, () => console.log(`Mock backend http://localhost:${PORT}`))
