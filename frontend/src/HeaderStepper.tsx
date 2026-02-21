import React, { useMemo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import { Upload, ScanSearch, Sparkles } from 'lucide-react'

/* Small global CSS for header-stepper: noise, pulse, connector fill, reduced-motion */
const headerStepperStyles = `
  .header-stepper-bg {
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
    position: relative;
    overflow: hidden;
  }
  .header-stepper-glow {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.35;
    pointer-events: none;
  }
  .header-stepper-glow-1 {
    width: 320px;
    height: 320px;
    background: #a5b4fc;
    top: -120px;
    left: 10%;
  }
  .header-stepper-glow-2 {
    width: 280px;
    height: 280px;
    background: #c4b5fd;
    top: -80px;
    right: 15%;
  }
  .header-stepper-noise {
    position: absolute;
    inset: 0;
    opacity: 0.06;
    pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  }
  .header-stepper-glass {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(148, 163, 184, 0.35);
  }
  @keyframes header-stepper-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.92; transform: scale(1.02); }
  }
  @media (prefers-reduced-motion: reduce) {
    .header-stepper-pulse-active {
      animation: none !important;
    }
    .header-stepper-connector-fill {
      transition: none !important;
    }
  }
`

const STEPS = [
  { key: 1, label: 'Upload', Icon: Upload },
  { key: 2, label: 'Extract BOM', Icon: ScanSearch },
  { key: 3, label: 'Optimize', Icon: Sparkles },
] as const

export interface HeaderStepperProps {
  currentStep: 1 | 2 | 3
  logo?: React.ReactNode
  statusText?: string
  contentMaxWidth?: string
  onStepClick?: (step: 1 | 2 | 3) => void
}

export function HeaderStepper({
  currentStep,
  logo,
  statusText = 'Schematic → BOM → Substitutes',
  contentMaxWidth = 'max-w-4xl',
  onStepClick,
}: HeaderStepperProps) {
  const prefersReducedMotion = useReducedMotion()

  const defaultLogo = useMemo(
    () => (
      <h1 className="text-[1.75rem] font-extrabold tracking-tight bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
        CircuitScout
      </h1>
    ),
    []
  )

  return (
    <>
      <style>{headerStepperStyles}</style>
      <div className="header-stepper-bg">
        <div className="header-stepper-glow header-stepper-glow-1" aria-hidden />
        <div className="header-stepper-glow header-stepper-glow-2" aria-hidden />
        <div className="header-stepper-noise" aria-hidden />

        <header className="header-stepper-glass">
          <div
            className={`mx-auto ${contentMaxWidth} px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4`}
          >
            <div className="flex items-center justify-between sm:justify-start min-w-0">
              <div className="min-w-0">{logo ?? defaultLogo}</div>
              <span className="sm:hidden text-xs text-slate-500 font-medium truncate max-w-[140px]">
                {statusText}
              </span>
            </div>

            <nav
              className="flex items-center justify-center gap-0 flex-1"
              aria-label="Progress"
            >
              {STEPS.map((step, i) => {
                const isActive = currentStep === step.key
                const isPast = currentStep > step.key
                const Icon = step.Icon

                return (
                  <React.Fragment key={step.key}>
                    <div className="flex flex-col items-center">
                      <motion.button
                        type="button"
                        onClick={() => onStepClick?.(step.key)}
                        disabled={!onStepClick}
                        className={`
                          relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-200
                          focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2
                          ${onStepClick ? 'cursor-pointer' : 'cursor-default'}
                          ${isActive
                            ? 'border-transparent bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-200/50 ring-2 ring-indigo-400/50 ring-offset-2 ring-offset-white header-stepper-pulse-active'
                            : isPast
                              ? 'border-indigo-200 bg-indigo-50 text-indigo-600'
                              : 'border-slate-200 bg-slate-50 text-slate-400'}
                          hover:shadow-md hover:-translate-y-0.5
                        `}
                        style={
                          isActive && !prefersReducedMotion
                            ? {
                                animation: 'header-stepper-pulse 2.5s ease-in-out infinite',
                              }
                            : undefined
                        }
                        aria-current={isActive ? 'step' : undefined}
                        aria-label={`Step ${step.key}: ${step.label}`}
                      >
                        <Icon className="w-5 h-5" strokeWidth={2.25} aria-hidden />
                      </motion.button>
                      <span
                        className={`
                          mt-1.5 text-xs font-medium
                          ${isActive ? 'text-indigo-600' : isPast ? 'text-slate-600' : 'text-slate-400'}
                        `}
                      >
                        {step.label}
                      </span>
                    </div>

                    {i < STEPS.length - 1 && (
                      <div className="flex items-center mx-2 sm:mx-4 w-12 sm:w-16">
                        <div
                          className="relative h-1 w-full rounded-full bg-slate-200 overflow-hidden"
                          aria-hidden
                        >
                          <motion.div
                            className="header-stepper-connector-fill absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-300 to-violet-300 origin-left"
                            initial={false}
                            animate={{
                              scaleX: currentStep > step.key ? 1 : 0,
                            }}
                            transition={{
                              duration: prefersReducedMotion ? 0 : 0.4,
                              ease: 'easeOut',
                            }}
                            style={{ width: '100%' }}
                          />
                        </div>
                      </div>
                    )}
                  </React.Fragment>
                )
              })}
            </nav>

            <div className="hidden sm:block text-right">
              <span className="text-sm text-slate-500 font-medium">{statusText}</span>
            </div>
          </div>
        </header>
      </div>
    </>
  )
}

export default HeaderStepper
