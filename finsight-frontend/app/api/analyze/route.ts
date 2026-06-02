// app/api/analyze/route.ts
import { NextRequest, NextResponse } from 'next/server';

// Ensure variable points to the versioned baseline route location
const FLASK_URL = process.env.FLASK_URL || 'http://127.0.0.1:5000/api/v1';

export async function POST(req: NextRequest) {
  try {
    const incomingFormData = await req.formData();

    const file = incomingFormData.get('file');
    const companyName = incomingFormData.get('company_name');
    const sector = incomingFormData.get('sector');

    if (!file) {
      return NextResponse.json({ error: 'Multipart upload error: Missing file parameter block.' }, { status: 400 });
    }

    // Standardize data naming parameters matching the app.py expected form variables
    const cleanFormData = new FormData();
    cleanFormData.append('file', file);
    if (companyName) cleanFormData.append('company_name', companyName);
    if (sector) cleanFormData.append('sector', sector);

    // Forward the file stream directly to your background analytical core
    const flaskRes = await fetch(`${FLASK_URL}/analyze`, {
      method: 'POST',
      body: cleanFormData,
    });

    if (!flaskRes.ok) {
      const err = await flaskRes.json().catch(() => ({ 
        error: 'FinSight Engine Error', 
        message: 'The backend analytical routine failed to complete processing operations.' 
      }));
      return NextResponse.json(err, { status: flaskRes.status });
    }

    const data = await flaskRes.json();
    return NextResponse.json(data);
    
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Unknown network connection runtime failure.';
    return NextResponse.json(
      { error: `Background analytical pipeline unreachable: ${msg}` },
      { status: 502 }
    );
  }
}

// Next.js App Router dynamic route options configuration matrix
export const runtime = 'nodejs';