import { z } from "zod";

export const HealthSchema = z.object({
  status: z.literal("ok"),
  service: z.string(),
  version: z.string(),
});
export type Health = z.infer<typeof HealthSchema>;

export const ReadyzSchema = z
  .object({
    status: z.union([z.literal("ready"), z.literal("degraded")]),
    service: z.string(),
    checks: z.record(z.string(), z.string()),
  })
  .catchall(z.unknown());
export type Readyz = z.infer<typeof ReadyzSchema>;
