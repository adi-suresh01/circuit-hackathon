import { useState, useCallback, useRef, useEffect } from 'react'
import { extractImage, getJobStatus, getSubstitutes, exportBomToCsv } from './api.js'
import HeaderStepper from './HeaderStepper'

const POLL_INTERVAL_MS = 1500

const CONTENT_MAX = 'max-w-4xl'

const ACCEPTED_IMAGE_TYPES = 'image/png,image/jpeg,image/jpg,image/gif,image/webp'

function UploadCard({ file, onFileChange, chaosMode, onChaosToggle, onExtract, extracting, disabled }) {
  const inputRef = useRef(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])
  const handleExtract = () => {
    if (!file) return
    onExtract(file)
  }
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-slate-800 mb-1">Upload schematic</h2>
      <p className="text-sm text-slate-500 mb-4">Supported formats: PNG, JPG, JPEG, GIF, WebP</p>
      <div className="flex flex-wrap items-center gap-4 gap-y-3">
        <div className="flex flex-col gap-1">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_IMAGE_TYPES}
            className="hidden"
            onChange={(e) => onFileChange(e.target.files?.[0])}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="rounded-lg bg-slate-100 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-200 border border-slate-200"
          >
            Choose image
          </button>
          {file && (
            <span className="text-xs text-slate-500 truncate max-w-[220px]" title={file.name}>
              {file.name}
            </span>
          )}
        </div>
        <label className="flex items-center gap-2 cursor-pointer min-h-[42px]">
          <input type="checkbox" checked={chaosMode} onChange={(e) => onChaosToggle(e.target.checked)} className="rounded border-slate-300" />
          <span className="text-sm text-slate-600">Chaos Mode</span>
        </label>
        <button
          type="button"
          onClick={handleExtract}
          disabled={disabled || !file || extracting}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {extracting ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>
      {previewUrl && (
        <div className="mt-4 pt-4 border-t border-slate-100">
          <p className="text-xs font-medium text-slate-500 mb-2">Preview</p>
          <img src={previewUrl} alt="Schematic preview" className="max-h-36 rounded-lg border border-slate-200 object-contain bg-slate-50" />
        </div>
      )}
    </div>
  )
}

function JobStatusCard({ jobId, status, progress, lastUpdated, logEntries }) {
  if (!jobId) return null
  const badgeClass = {
    pending: 'bg-amber-100 text-amber-800',
    running: 'bg-blue-100 text-blue-800',
    done: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }[status] || 'bg-slate-100 text-slate-800'
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-slate-800 mb-1">Job status</h2>
      <div className="flex flex-wrap gap-3 items-center mb-3">
        <span className="text-xs font-mono text-slate-500">job_id: {jobId}</span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass}`}>{status}</span>
        {typeof progress === 'number' && <span className="text-xs text-slate-600">Progress: {progress}%</span>}
        {lastUpdated && <span className="text-xs text-slate-400">Updated: {lastUpdated}</span>}
      </div>
      {logEntries?.length > 0 && (
        <div className="mt-2 rounded-lg bg-slate-50 p-3 max-h-32 overflow-y-auto">
          <p className="text-xs font-medium text-slate-600 mb-1">Progress log</p>
          <ul className="text-xs text-slate-600 space-y-0.5">
            {logEntries.map((entry, i) => (
              <li key={i}>{entry}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function BOMRow({ item, onFetchSubstitutes }) {
  const [open, setOpen] = useState(false)
  const [subs, setSubs] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const baseKey = item.key ?? item.part_number ?? item.mpn ?? JSON.stringify(item)

  const fetchSubs = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const data = await onFetchSubstitutes(baseKey, item.quantity ?? 1)
      setSubs(data.substitutes ?? [])
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }, [baseKey, item.quantity, onFetchSubstitutes])

  const toggle = () => {
    if (!open && !subs && !loading) fetchSubs()
    setOpen((o) => !o)
  }

  return (
    <div className="border-b border-slate-100 last:border-0">
      <div
        className="flex flex-wrap items-center gap-2 py-2.5 px-6 hover:bg-slate-50 cursor-pointer"
        onClick={toggle}
      >
        <span className="font-mono text-sm text-slate-800">{baseKey}</span>
        <span className="text-sm text-slate-600">{item.description ?? '-'}</span>
        <span className="text-sm text-slate-500">Qty: {item.quantity ?? 1}</span>
        <span className="text-xs text-slate-400 ml-auto">{open ? '▼' : '▶'}</span>
      </div>
      {open && (
        <div className="pl-6 pr-6 pb-3 pt-1 bg-slate-50/50">
          {loading && <p className="text-xs text-slate-500 py-2">Loading substitutes…</p>}
          {err && <p className="text-xs text-red-600 py-2">{err}</p>}
          {subs && subs.length === 0 && <p className="text-xs text-slate-500 py-2">No substitutes returned.</p>}
          {subs && subs.length > 0 && (
            <ul className="space-y-2 mt-1">
              {subs.map((s, i) => (
                <li key={i} className="text-xs rounded-lg bg-white p-2 border border-slate-100">
                  <span className="font-mono text-slate-700">{s.key}</span>
                  {s.reason != null && <span className="text-slate-600 ml-2">— {s.reason}</span>}
                  {s.price != null && <span className="text-green-600 ml-2">${s.price}</span>}
                  {s.score != null && <span className="text-slate-400 ml-2">(score: {s.score})</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

function BOMList({ items, onFetchSubstitutes }) {
  if (!items?.length) return null
  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-semibold text-slate-800">BOM results</h2>
        <p className="text-sm text-slate-500 mt-0.5">{items.length} item(s)</p>
      </div>
      <div className="divide-y divide-slate-100">
        {items.map((item, i) => (
          <BOMRow key={i} item={item} onFetchSubstitutes={onFetchSubstitutes} />
        ))}
      </div>
    </div>
  )
}

const COMPONENT_TYPES = ['Resistor', 'Capacitor', 'Inductor', 'IC', 'Connector', 'Diode', 'Transistor', 'Other']

// Converts table row to pipeline BOM item (same shape as extract/manual JSON).
// Row uses "pkg" not "package" to avoid reserved-word issues in JS.
function rowToBomItem(row, index) {
  const ref = (row.ref || '').trim() || `Part-${index + 1}`
  const qty = parseInt(row.quantity, 10)
  const pkg = row.pkg ?? row.package ?? ''
  return {
    key: ref,
    refdes: ref,
    refs: [ref],
    type: row.componentType || 'Other',
    description: row.componentType ? ([row.componentType, row.value].filter(Boolean).join(' ') || ref) : ref,
    value: row.value || '',
    footprint: pkg,
    package: pkg,
    quantity: Number.isFinite(qty) && qty > 0 ? qty : 1,
  }
}

function ManualBOMSection({
  tableRows,
  setTableRows,
  onUseFromTable,
  manualBomJson,
  setManualBomJson,
  onUseFromJson,
  showToast,
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const addRow = () => setTableRows((prev) => [...prev, { id: Math.random().toString(36).slice(2), ref: '', componentType: '', value: '', pkg: '', quantity: '' }])
  const removeRow = (i) => setTableRows((prev) => prev.filter((_, idx) => idx !== i))
  const updateRow = (i, field, value) =>
    setTableRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)))

  const handleUseFromTable = () => {
    const items = tableRows.map((r, i) => rowToBomItem(r, i)).filter((item) => item.quantity >= 1)
    if (!items.length) {
      showToast('Add at least one row with quantity ≥ 1.', true)
      return
    }
    onUseFromTable(items)
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-slate-800 mb-1">Manual BOM fallback</h2>
      <p className="text-sm text-slate-500 mb-4">Add parts in the table below, then click &quot;Use manual BOM&quot; to use them as the BOM.</p>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-slate-200">
              <th className="text-left py-2 pr-2 font-medium text-slate-600">Ref</th>
              <th className="text-left py-2 pr-2 font-medium text-slate-600">Component type</th>
              <th className="text-left py-2 pr-2 font-medium text-slate-600">Value</th>
              <th className="text-left py-2 pr-2 font-medium text-slate-600">Package</th>
              <th className="text-left py-2 pr-2 font-medium text-slate-600">Quantity</th>
              <th className="w-20 py-2" />
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, i) => (
              <tr key={row.id ?? i} className="border-b border-slate-100">
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.ref ?? ''}
                    onChange={(e) => updateRow(i, 'ref', e.target.value)}
                    placeholder="e.g. R1"
                    className="w-full rounded border border-slate-200 px-2 py-1 text-slate-800"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <select
                    value={row.componentType ?? ''}
                    onChange={(e) => updateRow(i, 'componentType', e.target.value)}
                    className="w-full rounded border border-slate-200 px-2 py-1 text-slate-800 bg-white"
                  >
                    <option value="">Select…</option>
                    {COMPONENT_TYPES.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.value ?? ''}
                    onChange={(e) => updateRow(i, 'value', e.target.value)}
                    placeholder="e.g. 10k"
                    className="w-full rounded border border-slate-200 px-2 py-1 text-slate-800"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    value={row.pkg ?? ''}
                    onChange={(e) => updateRow(i, 'pkg', e.target.value)}
                    placeholder="e.g. 0603"
                    className="w-full rounded border border-slate-200 px-2 py-1 text-slate-800"
                  />
                </td>
                <td className="py-1.5 pr-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    value={row.quantity ?? ''}
                    onChange={(e) => updateRow(i, 'quantity', e.target.value)}
                    placeholder="1"
                    className="w-16 rounded border border-slate-200 px-2 py-1 text-slate-800"
                  />
                </td>
                <td className="py-1.5 pl-2">
                  <button
                    type="button"
                    onClick={() => removeRow(i)}
                    className="text-xs text-red-600 hover:text-red-700"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap gap-3 mt-4">
        <button
          type="button"
          onClick={addRow}
          className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
        >
          + Add part
        </button>
        <button
          type="button"
          onClick={handleUseFromTable}
          className="rounded-lg bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Use manual BOM
        </button>
      </div>

      <div className="mt-6 border-t border-slate-200 pt-4">
        <button
          type="button"
          onClick={() => setAdvancedOpen((o) => !o)}
          className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-800"
        >
          <span className="text-slate-400">{advancedOpen ? '▼' : '▶'}</span>
          Advanced (JSON)
        </button>
        {advancedOpen && (
          <div className="mt-3">
            <p className="text-xs text-slate-500 mb-2">Paste BOM JSON (array or object with items) to load as manual BOM.</p>
            <textarea
              value={manualBomJson}
              onChange={(e) => setManualBomJson(e.target.value)}
              placeholder='[{"key":"R1","quantity":1,"description":"10k"},...]'
              className="w-full h-24 rounded-lg border border-slate-200 p-2 text-sm font-mono"
            />
            <button
              type="button"
              onClick={onUseFromJson}
              className="mt-2 rounded-lg bg-slate-600 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Use manual BOM from JSON
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [file, setFile] = useState(null)
  const [chaosMode, setChaosMode] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [logEntries, setLogEntries] = useState([])
  const [toast, setToast] = useState(null)
  const [debugMessage, setDebugMessage] = useState(null)
  const [manualBomJson, setManualBomJson] = useState('')
  const [tableRows, setTableRows] = useState(() => [
    { id: 'row-1', ref: '', componentType: '', value: '', pkg: '', quantity: '' },
    { id: 'row-2', ref: '', componentType: '', value: '', pkg: '', quantity: '' },
  ])
  const pollRef = useRef(null)

  const addLog = useCallback((msg) => {
    setLogEntries((prev) => [...prev, `${new Date().toISOString().slice(11, 19)} ${msg}`])
  }, [])

  const showToast = useCallback((message, isError = false) => {
    setToast({ message, isError })
    setTimeout(() => setToast(null), 5000)
  }, [])

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback(
    (id) => {
      stopPolling()
      setJobId(id)
      setStatus('pending')
      setProgress(0)
      setResult(null)
      setLogEntries((prev) => [...prev, `Job ${id} started`])
      const poll = async () => {
        try {
          const data = await getJobStatus(id)
          setStatus(data.status)
          setProgress(data.progress ?? null)
          setLastUpdated(new Date().toLocaleTimeString())
          if (data.status === 'done' && data.result != null) {
            setResult(Array.isArray(data.result) ? data.result : data.result?.items ?? [])
            addLog('Job done')
            stopPolling()
          } else if (data.status === 'failed') {
            addLog('Job failed')
            stopPolling()
            showToast('Job failed', true)
          } else {
            addLog(`${data.status} ${data.progress != null ? data.progress + '%' : ''}`)
          }
        } catch (e) {
          setDebugMessage(e.message)
          addLog(`Error: ${e.message}`)
          showToast(e.message, true)
        }
      }
      poll()
      pollRef.current = setInterval(poll, POLL_INTERVAL_MS)
    },
    [addLog, stopPolling, showToast]
  )

  const handleExtract = useCallback(
    async (selectedFile) => {
      setExtracting(true)
      setDebugMessage(null)
      try {
        // Backend should forward this job to AWS Strands. Strands must call back POST /api/strands-callback with { job_id, status, result }.
        const data = await extractImage(selectedFile, chaosMode)
        const id = data.job_id
        if (id) startPolling(id)
        else showToast('No job_id in response', true)
      } catch (e) {
        setDebugMessage(e.message)
        showToast(e.message, true)
        addLog(`Extract error: ${e.message}`)
      } finally {
        setExtracting(false)
      }
    },
    [chaosMode, startPolling, showToast, addLog]
  )

  const handleFetchSubstitutes = useCallback(async (baseKey, qty) => {
    return getSubstitutes(baseKey, qty)
  }, [])

  const applyManualBom = useCallback(
    (items) => {
      setResult(items)
      setStatus('done')
      setJobId(null)
      stopPolling()
      showToast('Manual BOM loaded')
    },
    [stopPolling, showToast]
  )

  const handleUseManualBomFromTable = useCallback(
    (items) => {
      applyManualBom(items)
    },
    [applyManualBom]
  )

  const handleUseManualBomFromJson = useCallback(() => {
    try {
      const parsed = JSON.parse(manualBomJson)
      const items = Array.isArray(parsed) ? parsed : parsed?.items ?? parsed?.components ?? []
      if (items.length) {
        applyManualBom(items)
      } else {
        showToast('JSON has no BOM items array', true)
      }
    } catch (e) {
      setDebugMessage(e.message)
      showToast('Invalid JSON: ' + e.message, true)
    }
  }, [manualBomJson, applyManualBom, showToast])

  const handleExportCsv = useCallback(() => {
    if (!result?.length) {
      showToast('No BOM to export', true)
      return
    }
    exportBomToCsv(result)
    showToast('CSV exported')
  }, [result, showToast])

  const bomItems = result ?? []

  // Step indicator: 1 Upload (default), 2 Extract (analyze clicked / polling), 3 Optimize (BOM + substitutes ready)
  const currentStep = bomItems.length > 0 ? 3 : extracting || (jobId && status !== 'done') ? 2 : 1

  return (
    <div className="min-h-screen page-bg flex flex-col">
      <HeaderStepper
        currentStep={currentStep}
        statusText="Schematic → BOM → Substitutes"
        contentMaxWidth={CONTENT_MAX}
      />
      <main className={`flex-1 mx-auto ${CONTENT_MAX} w-full px-6 py-8 space-y-6`}>
        <UploadCard
          file={file}
          onFileChange={setFile}
          chaosMode={chaosMode}
          onChaosToggle={setChaosMode}
          onExtract={handleExtract}
          extracting={extracting}
          disabled={extracting}
        />
        <JobStatusCard jobId={jobId} status={status} progress={progress} lastUpdated={lastUpdated} logEntries={logEntries} />
        <BOMList items={bomItems} onFetchSubstitutes={handleFetchSubstitutes} />

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={!bomItems.length}
            className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Export CSV
          </button>
        </div>

        <ManualBOMSection
          tableRows={tableRows}
          setTableRows={setTableRows}
          onUseFromTable={handleUseManualBomFromTable}
          manualBomJson={manualBomJson}
          setManualBomJson={setManualBomJson}
          onUseFromJson={handleUseManualBomFromJson}
          showToast={showToast}
        />

        {debugMessage && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
            <p className="text-sm font-semibold text-amber-800 mb-1">Debug / last error</p>
            <pre className="text-xs text-amber-900 whitespace-pre-wrap break-all">{debugMessage}</pre>
            <p className="text-xs text-amber-700 mt-2">If backend is down, use Manual BOM paste above to demo.</p>
          </div>
        )}
      </main>

      {toast && (
        <div
          className={`fixed bottom-4 right-4 rounded-lg px-4 py-2 text-sm shadow-lg z-10 ${
            toast.isError ? 'bg-red-600 text-white' : 'bg-slate-800 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}

      <footer className="border-t border-slate-200 bg-white py-3">
        <div className={`mx-auto ${CONTENT_MAX} px-6 text-center`}>
          <span className="inline-block rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
            Data Source: Mock Supplier Provider (API-ready)
          </span>
        </div>
      </footer>
    </div>
  )
}
