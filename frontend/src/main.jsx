import React from 'react'
import ReactDOM from 'react-dom/client'
import { MotionConfig } from 'framer-motion'
import { CopilotKit } from '@copilotkit/react-core'
import { CopilotSidebar } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import './index.css'
import './styles/ui.css'

const runtimeUrl = import.meta.env.VITE_COPILOT_RUNTIME_URL || 'http://localhost:8000/api/copilotkit'
const disableCopilot = import.meta.env.VITE_DISABLE_COPILOT === 'true' || import.meta.env.VITE_DISABLE_COPILOT === '1'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <MotionConfig reducedMotion="user">
        {disableCopilot ? (
          <App disableCopilot />
        ) : (
          <CopilotKit runtimeUrl={runtimeUrl} showDevConsole={false}>
            <CopilotSidebar
              defaultOpen={false}
              labels={{
                title: 'CircuitScout Copilot',
                initial: 'Upload a schematic or paste a BOM. I\'ll help you extract, substitute, and optimize.',
              }}
            >
              <App />
            </CopilotSidebar>
          </CopilotKit>
        )}
      </MotionConfig>
    </ErrorBoundary>
  </React.StrictMode>
)
