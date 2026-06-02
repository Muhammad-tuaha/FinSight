'use client'

import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import { FinancialRatios, RedFlag } from '@/types'

interface Props {
  ratios: FinancialRatios
  ratiosPrior?: FinancialRatios | null
  redFlags: RedFlag[]
}

export default function RatioCharts({ ratios, ratiosPrior, redFlags }: Props) {
  const radarData = [
    { subject: 'Liquidity',      value: Math.min(100, ((ratios.current_ratio ?? 0) / 3) * 100) },
    { subject: 'Quick Ratio',    value: Math.min(100, ((ratios.quick_ratio ?? 0) / 2) * 100) },
    { subject: 'Net Margin',     value: Math.min(100, ((ratios.net_margin ?? 0) / 20) * 100) },
    { subject: 'ROE',            value: Math.min(100, ((ratios.roe ?? 0) / 25) * 100) },
    { subject: 'Debt Control',   value: Math.min(100, Math.max(0, (3 - (ratios.debt_to_equity ?? 0)) / 3 * 100)) },
    { subject: 'Efficiency',     value: Math.min(100, ((ratios.asset_turnover ?? 0) / 1.5) * 100) },
  ]

  const yoyKeys: { key: keyof FinancialRatios; label: string }[] = [
    { key: 'net_margin', label: 'Net Margin %' },
    { key: 'roe', label: 'ROE %' },
    { key: 'current_ratio', label: 'Current Ratio' },
    { key: 'debt_to_equity', label: 'Debt/Equity' },
  ]

  const hasPrior = ratiosPrior && yoyKeys.some(({ key }) => ratiosPrior[key] != null && ratios[key] != null)

  const yoyData = hasPrior
    ? yoyKeys
        .filter(({ key }) => ratios[key] != null && ratiosPrior![key] != null)
        .map(({ key, label }) => ({
          name: label,
          current: Number(ratios[key]),
          prior: Number(ratiosPrior![key]),
        }))
    : []

  const barData = [
    {
      name: 'Liquidity',
      score: Math.round(Math.min(100, (((ratios.current_ratio ?? 0) + (ratios.quick_ratio ?? 0)) / 4) * 100)),
    },
    {
      name: 'Profitability',
      score: Math.round(Math.min(100, (((ratios.net_margin ?? 0) + (ratios.roe ?? 0)) / 35) * 100)),
    },
    {
      name: 'Leverage',
      score: Math.round(Math.min(100, Math.max(0, (3 - (ratios.debt_to_equity ?? 0)) / 3 * 100))),
    },
    {
      name: 'Efficiency',
      score: Math.round(Math.min(100, (((ratios.asset_turnover ?? 0) + (ratios.inventory_turnover ?? 0) / 8) / 2) * 100)),
    },
  ]

  const barColor = (score: number) =>
    score >= 65 ? '#00e5a0' : score >= 40 ? '#f5a623' : '#ff4d4d'

  const high   = redFlags.filter(f => f.priority === 'HIGH').length
  const medium = redFlags.filter(f => f.priority === 'MEDIUM').length
  const low    = redFlags.filter(f => f.priority === 'LOW').length
  const pieData = redFlags.length === 0
    ? [{ name: 'None', value: 1, color: '#1d2535' }]
    : [
        { name: 'High',   value: high,   color: '#ff4d4d' },
        { name: 'Medium', value: medium, color: '#f5a623' },
        { name: 'Low',    value: low,    color: '#4d9fff' },
      ].filter(d => d.value > 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {hasPrior && yoyData.length > 0 && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', marginBottom: 16 }}>
            Current vs Prior Period
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={yoyData} barSize={28}>
              <XAxis dataKey="name" tick={{ fill: '#8b92a8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#555e72', fontSize: 10, fontFamily: 'IBM Plex Mono, monospace' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#161b26', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
              />
              <Legend />
              <Bar dataKey="prior" name="Prior" fill="#64748b" radius={[4, 4, 0, 0]} />
              <Bar dataKey="current" name="Current" fill="#00e5a0" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
        <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', marginBottom: 16 }}>
          Liquidity & Profitability Overview
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData}>
            <PolarGrid stroke="rgba(255,255,255,0.07)" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: '#8b92a8', fontSize: 11, fontFamily: 'IBM Plex Mono, monospace' }}
            />
            <Radar
              name="Company"
              dataKey="value"
              stroke="#00e5a0"
              fill="#00e5a0"
              fillOpacity={0.12}
              strokeWidth={2}
              dot={{ r: 4, fill: '#00e5a0', strokeWidth: 0 }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', marginBottom: 16 }}>
            Category Scores
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barSize={32}>
              <XAxis dataKey="name" tick={{ fill: '#8b92a8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fill: '#555e72', fontSize: 10, fontFamily: 'IBM Plex Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
              <Tooltip
                contentStyle={{ background: '#161b26', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
                formatter={(v: number) => [`${v}%`, 'Score']}
              />
              <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                {barData.map((entry, i) => (
                  <Cell key={i} fill={barColor(entry.score)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--text3)', fontFamily: 'IBM Plex Mono, monospace', marginBottom: 16 }}>
            Red Flag Distribution
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#161b26', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 4 }}>
            {pieData.map((d, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text2)' }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                {d.name}: {d.value}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
