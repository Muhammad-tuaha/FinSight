'use client'

import React, { createContext, useContext, useState, ReactNode } from 'react'
import { AnalysisResult } from '@/types'

interface StoreState {
  result: AnalysisResult | null
  meta: { company: string; sector: string } | null
  setAnalysis: (result: AnalysisResult, company: string, sector: string) => void
  clearAnalysis: () => void
}

const Store = createContext<StoreState | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [meta, setMeta] = useState<{ company: string; sector: string } | null>(null)

  const setAnalysis = (r: AnalysisResult, company: string, sector: string) => {
    setResult(r)
    setMeta({ company, sector })
  }

  const clearAnalysis = () => {
    setResult(null)
    setMeta(null)
  }

  return (
    <Store.Provider value={{ result, meta, setAnalysis, clearAnalysis }}>
      {children}
    </Store.Provider>
  )
}

export function useStore() {
  const ctx = useContext(Store)
  if (!ctx) throw new Error('useStore must be used inside StoreProvider')
  return ctx
}
