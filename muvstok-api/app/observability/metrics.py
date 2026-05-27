from prometheus_client import Counter

jobs_created_total = Counter("muvstok_jobs_created_total", "Total Muvstok jobs created.")
jobs_published_total = Counter("muvstok_jobs_published_total", "Total Muvstok jobs published.")
sku_processed_total = Counter("muvstok_sku_processed_total", "Total Muvstok SKUs processed.")
