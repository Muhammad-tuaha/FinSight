# FinSight Frontend

Next.js 14 + TypeScript + Tailwind dashboard for the PSX Financial Analysis pipeline.

## Quick Start

```bash
cd finsight-frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Requirements

- Node.js 18+
- Flask backend running at `localhost:5000` (from `FINSIGHT/app.py`)

## Add /health to your Flask app.py

```python
@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200
```

## Expected Flask /analyze response shape

```json
{
  "ratios": {
    "current_ratio": 1.42,
    "quick_ratio": 0.98,
    "gross_margin": 28.4,
    "net_margin": 6.8,
    "roa": 4.2,
    "roe": 14.7,
    "debt_to_equity": 1.83,
    "interest_coverage": 2.9,
    "asset_turnover": 0.62,
    "inventory_turnover": 5.3,
    "receivables_turnover": 7.1
  },
  "red_flags": [
    {
      "priority": "HIGH",
      "title": "Elevated Debt-to-Equity",
      "description": "D/E ratio of 1.83 exceeds sector norms..."
    }
  ],
  "summary": "Executive summary text...",
  "financial_data": {
    "revenue": 285400,
    "net_income": 19406
  }
}
```

## Project Structure

```
finsight-frontend/
├── app/
│   ├── api/analyze/route.ts   # Next.js API route → proxies to Flask
│   ├── upload/page.tsx        # Upload + form page
│   ├── results/page.tsx       # 4-tab results dashboard
│   ├── layout.tsx             # Root layout with sidebar
│   └── globals.css
├── components/
│   ├── ui/Sidebar.tsx         # Navigation + backend status
│   └── charts/RatioCharts.tsx # Recharts radar/bar/pie
├── lib/
│   ├── api.ts                 # Flask client + ratio helpers
│   └── store.ts               # React context for analysis state
└── types/index.ts             # TypeScript interfaces
```

## Future: Jamal's Benchmarking Layer

When `/analyze` returns `benchmarks`, add a fifth tab in `results/page.tsx`:
```ts
benchmarks?: {
  sector: string
  peer_rank: number
  total_peers: number
  deviations: Record<string, number>
}
```
