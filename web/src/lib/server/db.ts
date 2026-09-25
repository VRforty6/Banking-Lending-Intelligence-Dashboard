import "server-only";

import { config as loadDotenv } from "dotenv";
import { resolve } from "node:path";
import { Pool } from "pg";
import { z } from "zod";

if (!process.env.POSTGRES_HOST) {
  loadDotenv({ path: resolve(process.cwd(), "..", ".env"), quiet: true });
}

const databaseEnvironmentSchema = z.object({
  POSTGRES_HOST: z.string().min(1),
  POSTGRES_PORT: z.coerce.number().int().positive().default(5432),
  POSTGRES_DB: z.string().min(1),
  POSTGRES_USER: z.string().min(1),
  POSTGRES_PASSWORD: z.string(),
  POSTGRES_SSL: z
    .enum(["true", "false"])
    .default("false")
    .transform((value) => value === "true"),
});

function readDatabaseEnvironment() {
  return databaseEnvironmentSchema.parse(process.env);
}

const globalForPool = globalThis as typeof globalThis & {
  hmdaPool?: Pool;
};

export function getDatabasePool(): Pool {
  if (!globalForPool.hmdaPool) {
    const environment = readDatabaseEnvironment();
    globalForPool.hmdaPool = new Pool({
      host: environment.POSTGRES_HOST,
      port: environment.POSTGRES_PORT,
      database: environment.POSTGRES_DB,
      user: environment.POSTGRES_USER,
      password: environment.POSTGRES_PASSWORD,
      ssl: environment.POSTGRES_SSL
        ? { rejectUnauthorized: true }
        : undefined,
      max: 8,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 5_000,
      statement_timeout: 10_000,
      application_name: "hmda-web-analytics",
    });
  }

  return globalForPool.hmdaPool;
}
