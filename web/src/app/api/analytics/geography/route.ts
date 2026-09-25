import { ZodError } from "zod";

import { parseGeographyFilters } from "@/lib/analytics/geography";
import { fetchGeographyData } from "@/lib/server/geography";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request): Promise<Response> {
  try {
    const filters = parseGeographyFilters(new URL(request.url).searchParams);
    const data = await fetchGeographyData(filters);
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
    console.error("Geographic analytics request failed", error);
    return Response.json(
      {
        error: "Geographic analytics are temporarily unavailable",
        details:
          process.env.NODE_ENV === "development" && error instanceof Error
            ? error.message
            : undefined,
      },
      { status: 503 },
    );
  }
}
