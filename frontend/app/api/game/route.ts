import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api/game", "");
  const url = `${BACKEND_URL}/api/game${path}`;
  const body = await req.text();

  const upstream = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  if (upstream.headers.get("content-type")?.includes("text/event-stream")) {
    return new Response(upstream.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
      },
    });
  }

  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}

export async function GET(req: NextRequest) {
  const path = req.nextUrl.pathname.replace("/api", "");
  const upstream = await fetch(`${BACKEND_URL}${path}`);
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
