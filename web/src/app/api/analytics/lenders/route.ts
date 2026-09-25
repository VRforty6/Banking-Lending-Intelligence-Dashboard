import { z, ZodError } from "zod";

import { searchLenders } from "@/lib/server/geography";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const searchSchema = z.object({
  q: z.string().trim().max(80).default(""),
});

export async function GET(request: Request): Promise<Response> {
  try {
    const url = new URL(request.url);
    const { q } = searchSchema.parse({ q: url.searchParams.get("q") ?? "" });
    return Response.json({ lenders: await searchLenders(q) }, {
      headers: { "Cache-Control": "public, max-age=0, s-maxage=300" },
    });
  } catch (error) {
    if (error instanceof ZodError) {
      return Response.json(
        { error: "Invalid lender search", details: error.issues.map((issue) => issue.message) },
        { status: 400 },
      );
    }
    console.error("Lender search failed", error);
    return Response.json({ error: "Lender search is temporarily unavailable" }, { status: 503 });
  }
}
