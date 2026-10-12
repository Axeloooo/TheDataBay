export type JobLifecycleStatus = "queued" | "running" | "completed" | "failed";

export type VectorSpec = {
  model: string;
  dimension: number;
};

export type DatasetStats = {
  total_rows: number;
  total_columns: number;
  empty_rows_skipped: number;
  has_header: boolean;
};

export type JobResponse = {
  job_id: string;
  status: JobLifecycleStatus;
  listing_id: string;
};

export type JobStatusResponse = {
  job_id: string;
  status: JobLifecycleStatus;
  listing_id?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  vector_spec?: VectorSpec | null;
  stats?: DatasetStats | null;
  dataset_url?: string | null;
  dataset_hash?: string | null;
  filename: string;
};
