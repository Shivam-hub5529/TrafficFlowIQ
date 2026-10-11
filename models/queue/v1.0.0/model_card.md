# Model card: queue-v1.0.0

**Task:** probability that a freeway link has at least one queued 5-minute interval (speed <= 60% of free-flow) in the next 30 minutes,
from the previous 60 minutes of data only.

**Data source:** `synthetic` (SYNTHETIC stand-in, replace with TrafficFlowBench for real results)
**Split:** chronological by whole day, 90-minute purge gap. Val starts 2025-02-04, test starts 2025-02-10.
**Model:** LightGBM + isotonic calibration (fit on validation). Decision threshold 0.522 (max F1 on validation).

| Metric (test) | Value |
|---|---|
| prevalence | 0.081 |
| threshold | 0.522 |
| iou | 0.844 |
| precision | 0.975 |
| recall | 0.863 |
| f1 | 0.915 |
| roc_auc | 0.976 |
| pr_auc | 0.915 |

**Known limits:** calibrator and threshold share the validation set (slightly optimistic); queues driven by events not
visible in the 60-minute window (e.g. a crash 10 minutes from now) cannot be predicted.
