-- Create a view that summarizes run presence in normalized and scores
CREATE OR REPLACE VIEW ar_mvp.v_run_presence AS
WITH n AS (
  SELECT run_id, brand_id, source, COUNT(*) AS normalized_rows
  FROM ar_mvp.ar_content_normalized_v2
  WHERE run_id IS NOT NULL
  GROUP BY run_id, brand_id, source
),
s AS (
  SELECT run_id, brand_id, source, COUNT(*) AS scores_rows
  FROM ar_mvp.ar_content_scores_v2
  WHERE run_id IS NOT NULL
  GROUP BY run_id, brand_id, source
)
SELECT COALESCE(n.run_id, s.run_id) AS run_id,
       COALESCE(n.brand_id, s.brand_id) AS brand_id,
       COALESCE(n.source, s.source) AS source,
       n.normalized_rows,
       s.scores_rows,
       (n.normalized_rows IS NOT NULL) AS in_normalized,
       (s.scores_rows IS NOT NULL) AS in_scores
FROM n
FULL OUTER JOIN s
  ON n.run_id = s.run_id AND n.brand_id = s.brand_id AND n.source = s.source
ORDER BY brand_id, source, run_id
LIMIT 1000;
