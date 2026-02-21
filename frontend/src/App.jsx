import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { extractImage, getJobStatus, getSubstitutes, exportBomToCsv } from './api.js'
import HeaderStepper from './HeaderStepper'
import CopilotBridge from './components/CopilotBridge'

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
    <motion.div
      className="rounded-2xl border border-slate-200/80 bg-white p-7 shadow-sm"
      whileHover={{ y: -2, boxShadow: '0 4px 14px rgba(0,0,0,0.06)' }}
      transition={{ duration: 0.2 }}
    >
      <h2 className="text-lg font-semibold text-slate-800 mb-1">Upload schematic</h2>
      <p className="text-sm text-slate-500 mb-5">Supported formats: PNG, JPG, JPEG, GIF, WebP</p>
      <div className="flex flex-wrap items-center gap-4 gap-y-3">
        <div className="flex flex-col gap-1">
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_IMAGE_TYPES}
            className="hidden"
            onChange={(e) => onFileChange(e.target.files?.[0])}
          />
          <motion.button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="rounded-xl bg-slate-100 px-4 py-2.5 text-sm font-medium text-slate-700 border border-slate-200 hover:bg-slate-200 hover:border-slate-300"
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.98 }}
          >
            Choose image
          </motion.button>
          {file && (
            <span className="text-xs text-slate-500 truncate max-w-[220px]" title={file.name}>
              {file.name}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-3">
            <button
              type="button"
              role="switch"
              aria-checked={chaosMode}
              onClick={() => onChaosToggle(!chaosMode)}
              className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 ${chaosMode ? 'bg-indigo-600' : 'bg-slate-200'}`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform ${chaosMode ? 'translate-x-5' : 'translate-x-0.5'}`}
              />
            </button>
            <span className="text-sm font-medium text-slate-700">Chaos Mode</span>
          </div>
          <p className="text-xs text-slate-400">Simulate failures or fewer substitutes</p>
        </div>

        <motion.button
          type="button"
          onClick={handleExtract}
          disabled={disabled || !file || extracting}
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-200/50 hover:from-indigo-500 hover:to-violet-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-indigo-600 disabled:hover:to-violet-600"
          whileHover={disabled || !file || extracting ? {} : { y: -2, boxShadow: '0 6px 20px rgba(99, 102, 241, 0.35)' }}
          whileTap={disabled || !file || extracting ? {} : { scale: 0.98 }}
        >
          {extracting ? 'Analyzing…' : 'Analyze'}
        </motion.button>
      </div>
      {previewUrl && (
        <div className="mt-5 pt-5 border-t border-slate-100">
          <p className="text-xs font-medium text-slate-500 mb-2">Preview</p>
          <img src={previewUrl} alt="Schematic preview" className="max-h-36 rounded-xl border border-slate-200 object-contain bg-slate-50" />
        </div>
      )}
    </motion.div>
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
    <motion.div
      className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm"
      whileHover={{ y: -2, boxShadow: '0 4px 14px rgba(0,0,0,0.06)' }}
      transition={{ duration: 0.2 }}
    >
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
    </motion.div>
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
    <motion.div
      className="rounded-2xl border border-slate-200/80 bg-white shadow-sm overflow-hidden"
      initial={false}
      whileHover={{ y: -2, boxShadow: '0 4px 14px rgba(0,0,0,0.06)' }}
      transition={{ duration: 0.2 }}
    >
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-semibold text-slate-800">BOM results</h2>
        <p className="text-sm text-slate-500 mt-0.5">{items.length} item(s)</p>
      </div>
      <div className="divide-y divide-slate-100">
        {items.map((item, i) => (
          <BOMRow key={i} item={item} onFetchSubstitutes={onFetchSubstitutes} />
        ))}
      </div>
    </motion.div>
  )
}

export default function App({ disableCopilot = false }) {
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

  const handleAnalyzeForCopilot = useCallback(() => {
    if (file) handleExtract(file)
  }, [file, handleExtract])

  return (
    <div className="min-h-screen ui-page-bg ui-page-grid flex flex-col">
      {!disableCopilot && (
        <CopilotBridge
          currentStep={currentStep}
          chaosMode={chaosMode}
          bomItems={bomItems}
          hasFile={!!file}
          onAnalyze={handleAnalyzeForCopilot}
          onToggleChaosMode={setChaosMode}
          onExportCsv={handleExportCsv}
          setStep={undefined}
        />
      )}
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
          <motion.button
            type="button"
            onClick={handleExportCsv}
            disabled={!bomItems.length}
            className="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={bomItems.length ? { y: -1, boxShadow: '0 4px 12px rgba(5, 150, 105, 0.3)' } : {}}
            whileTap={bomItems.length ? { scale: 0.98 } : {}}
          >
            Export CSV
          </motion.button>
        </div>

        {debugMessage && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
            <p className="text-sm font-semibold text-amber-800 mb-1">Debug / last error</p>
            <pre className="text-xs text-amber-900 whitespace-pre-wrap break-all">{debugMessage}</pre>
            <p className="text-xs text-amber-700 mt-2">Check backend connection or try again.</p>
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
