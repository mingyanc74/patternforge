import {
  CheckCircle2,
  CircleAlert,
  CircleMinus,
  LoaderCircle,
} from "lucide-react";
import type { Job } from "../api";
import { active } from "../utils";

export function Status({ job }: { job: Job }) {
  const Icon = active(job)
    ? LoaderCircle
    : job.status === "SUCCESS"
      ? CheckCircle2
      : job.status === "FAILED"
        ? CircleAlert
        : CircleMinus;
  return (
    <span className={`badge ${job.status.toLowerCase()}`}>
      <Icon className={active(job) ? "spin" : ""} />
      {job.cancel_requested && active(job)
        ? "Cancelling"
        : job.stage === "RETRYING"
          ? "Retrying"
          : {
              QUEUED: "Queued",
              RUNNING: "Running",
              SUCCESS: "Succeeded",
              FAILED: "Failed",
              CANCELLED: "Cancelled",
            }[job.status]}
    </span>
  );
}
