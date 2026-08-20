import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const API_ORIGIN = process.env.HVAC_API_ORIGIN || 'http://127.0.0.1:8000';

async function proxy(req: NextRequest, path: string[]) {
  const dest = `${API_ORIGIN}/api/${path.join('/')}${req.nextUrl.search}`;
  try {
    const headers = new Headers(req.headers);
    headers.delete('host');
    const method = req.method.toUpperCase();
    const res = await fetch(dest, {
      method,
      headers,
      body: method === 'GET' || method === 'HEAD' ? undefined : await req.arrayBuffer(),
      cache: 'no-store',
    });
    const out = new Headers(res.headers);
    return new NextResponse(res.body, { status: res.status, headers: out });
  } catch {
    return NextResponse.json(
      {
        code: 'BACKEND_OFFLINE',
        message: 'HVAC API is not running on port 8000. Start: uvicorn backend.main:app --reload --port 8000',
      },
      { status: 503 }
    );
  }
}

type Ctx = { params: { path: string[] } };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path);
}
