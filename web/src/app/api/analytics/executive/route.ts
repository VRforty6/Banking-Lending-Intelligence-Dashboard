import { ZodError } from "zod";

import { parseExecutiveFilters } from "@/lib/analytics/filters";
import { fetchExecutiveData } from "@/lib/server/executive";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const filters = parseExecutiveFilters(new URL(request.url).searchParams);
    const data = await fetchExecutiveData(filters);

    return Response.json(data, {
      headers: {
        "Cache-Control": "public, max-age=0, s-maxage=300, stale-while-revalidate=600",
      },
    });
  } catch (error) {
    if (error instanceof ZodError) {
      return Response.json(
        {
          error: "Invalid filters",
          details: error.issues.map((issue) => issue.message),
        },
        { status: 400 },
      );
    }

    console.error("Executive analytics request failed", error);
    return Response.json(
      {
        error: "Analytics are temporarily unavailable",
        details:
          process.env.NODE_ENV === "development" && error instanceof Error
            ? error.message
            : undefined,
      },
      { status: 503 },
    );
  }
}
