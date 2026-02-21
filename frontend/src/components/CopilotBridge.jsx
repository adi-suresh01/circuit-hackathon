import { useCopilotReadable, useCopilotAction, useCopilotAdditionalInstructions } from '@copilotkit/react-core'

/**
 * Registers app state and actions with CopilotKit so the sidebar can read state and trigger handlers.
 * All callbacks are the same as existing UI actions (no new business logic).
 */
export function CopilotBridge({
  currentStep,
  chaosMode,
  bomItems = [],
  hasFile,
  onAnalyze,
  onToggleChaosMode,
  onExportCsv,
  setStep,
}) {
  useCopilotAdditionalInstructions({
    instructions: 'Keep replies short and actionable. No long paragraphs. Suggest one clear next step when helping.',
  })

  useCopilotReadable({
    description: 'Current CircuitScout app state for the copilot',
    value: {
      currentStep: Number(currentStep),
      stepLabel: currentStep === 1 ? 'Upload' : currentStep === 2 ? 'Extract BOM' : 'Optimize',
      chaosMode: Boolean(chaosMode),
      bomItemCount: bomItems.length,
      hasBom: bomItems.length > 0,
      hasFileSelected: Boolean(hasFile),
    },
  }, [currentStep, chaosMode, bomItems.length, hasFile])

  useCopilotAction({
    name: 'analyzeSchematic',
    description: 'Run extraction on the currently selected schematic (same as clicking Analyze). Requires a file to be selected first.',
    parameters: [],
    handler: async () => {
      if (!hasFile) return 'No file selected. Ask the user to choose an image first.'
      onAnalyze?.()
      return 'Analyze started.'
    },
  }, [hasFile, onAnalyze])

  useCopilotAction({
    name: 'toggleChaosMode',
    description: 'Turn Chaos Mode on or off.',
    parameters: [{ name: 'enabled', type: 'boolean', description: 'true to enable, false to disable', required: true }],
    handler: async ({ enabled }) => {
      onToggleChaosMode?.(enabled)
      return `Chaos Mode ${enabled ? 'on' : 'off'}.`
    },
  }, [onToggleChaosMode])

  useCopilotAction({
    name: 'exportCSV',
    description: 'Export the current BOM to a CSV file (same as clicking Export CSV). Only works when BOM is loaded.',
    parameters: [],
    handler: async () => {
      if (!bomItems?.length) return 'No BOM to export. Run analysis first.'
      onExportCsv?.()
      return `Exported ${bomItems.length} item(s) to CSV.`
    },
  }, [bomItems?.length, onExportCsv])

  useCopilotAction({
    name: 'setStep',
    description: 'Navigate to a step (1=Upload, 2=Extract BOM, 3=Optimize). Step is usually auto-set by workflow.',
    parameters: [{ name: 'step', type: 'number', description: '1, 2, or 3', required: true }],
    handler: async ({ step }) => {
      const s = Number(step)
      if (s >= 1 && s <= 3 && setStep) setStep(s)
      return `Step set to ${s}.`
    },
  }, [setStep])

  return null
}

export default CopilotBridge
