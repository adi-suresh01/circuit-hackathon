/**
 * CircuitScout API helpers.
 * Base URL from VITE_API_BASE (e.g. http://localhost:8000). No secrets/keys here.
 */

const getBaseUrl = () => import.meta.env.VITE_API_BASE || ''

/**
 * POST /api/extract — upload schematic image, optional chaos=true.
 * Backend should forward this job to AWS Strands; Strands calls back POST /api/strands-callback with { job_id, status, result }.
 * @param {File} file - Image file (multipart/form-data)
 * @param {boolean} chaos - If true, adds ?chaos=true
 * @returns {Promise<{ job_id: string }>}
 */
export async function extractImage(file, chaos = false) {
  const base = getBaseUrl()
  const url = `${base}/api/extract${chaos ? '?chaos=true' : ''}`
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(url, {
    method: 'POST',
    body: form,
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Extract failed: ${res.status}`)
  }
  return res.json()
}

/**
 * GET /api/job-status/:job_id
 * Response: { status: "pending"|"running"|"done"|"failed", progress?: number, result?: BOM_JSON }
 */
export async function getJobStatus(jobId) {
  const base = getBaseUrl()
  const res = await fetch(`${base}/api/job-status/${jobId}`, {
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Job status failed: ${res.status}`)
  }
  return res.json()
}

/**
 * POST /api/substitutes/:base_key — request substitutes for a BOM item.
 * Body: { qty }. Response: { substitutes: [ { key, score, reason, price } ] }
 */
export async function getSubstitutes(baseKey, qty = 1) {
  const base = getBaseUrl()
  const res = await fetch(`${base}/api/substitutes/${encodeURIComponent(baseKey)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ qty }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `Substitutes failed: ${res.status}`)
  }
  return res.json()
}

/**
 * Client-side CSV export from current BOM (no backend call).
 * triggerExport = exportBomToCsv
 */
export function exportBomToCsv(bomItems, filename = 'circuit-scout-bom.csv') {
  if (!bomItems?.length) return
  const headers = ['key', 'description', 'quantity', 'value', 'footprint', 'refs']
  const rows = bomItems.map((item) => [
    item.key ?? '',
    item.description ?? '',
    item.quantity ?? '',
    item.value ?? '',
    item.footprint ?? '',
    Array.isArray(item.refs) ? item.refs.join(';') : (item.refs ?? ''),
  ])
  const csv = [headers.join(','), ...rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
