'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react'
import { AnalysisResult } from '@/types'

interface StoreState {
  result: AnalysisResult | null
  meta: { company: string; sector: string } | null
  showPatienceBanner: boolean
  setAnalysis: (result: AnalysisResult, company: string, sector: string, wasSlow?: boolean) => void
  clearPatienceBanner: () => void
  clearAnalysis: () => void
}

const Store = createContext<StoreState | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [meta, setMeta] = useState<{ company: string; sector: string } | null>(null)
  const [showPatienceBanner, setShowPatienceBanner] = useState(false)

  const setAnalysis = (r: AnalysisResult, company: string, sector: string, wasSlow = false) => {
    setResult(r)
    setMeta({ company, sector })
    setShowPatienceBanner(wasSlow)
  }

  const clearPatienceBanner = () => {
    setShowPatienceBanner(false)
  }

  const clearAnalysis = () => {
    setResult(null)
    setMeta(null)
    setShowPatienceBanner(false)
  }

  return (
    <Store.Provider value={{ result, meta, showPatienceBanner, setAnalysis, clearPatienceBanner, clearAnalysis }}>
      {children}
    </Store.Provider>
  )
}

export function useStore() {
  const ctx = useContext(Store)
  if (!ctx) throw new Error('useStore must be used inside StoreProvider')
  return ctx
}
