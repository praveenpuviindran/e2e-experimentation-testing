# Tableau Online Build Guide (MindLift)

This guide is for **Tableau Online / Tableau Public web authoring** where it says **Connect to Data -> Upload from file**.

## 0) Generate the upload files
Run:

```bash
make tableau-export
```

This creates:
- `data/processed/tableau/mindlift_tableau_user_level.csv` (main file)
- `data/processed/tableau/mindlift_tableau_upload_bundle.zip` (bundle)

## 1) Exactly what to upload in Tableau Online
At **Connect to Data -> Upload from file**, upload:

`data/processed/tableau/mindlift_tableau_user_level.csv`

Use this one file for all worksheets below.

## 2) Data type checks in Tableau (important)
In Data Source page, confirm:
- `signup_ts`: Date & Time
- `signup_date`: Date
- `signup_week`: String
- `user_id`: Number (whole)
- `assigned_variant`: String
- `actually_exposed_variant`: String
- `saw_treatment`: Number (whole)
- Metric flags (`activated_within_7d`, `retained_d7`, `retained_d30`, `cancelled_30d`): Number (whole)
- `time_to_first_match_hours`: Number (decimal)
- `support_tickets_30d`: Number (whole)

## 3) Create calculated fields (copy/paste)
1. `Activation Rate 7D`
```tableau
AVG([activated_within_7d])
```

2. `D7 Retention Rate`
```tableau
AVG([retained_d7])
```

3. `D30 Retention Rate`
```tableau
AVG([retained_d30])
```

4. `Cancellation Rate 30D`
```tableau
AVG([cancelled_30d])
```

5. `Support Tickets per User`
```tableau
AVG([support_tickets_30d])
```

6. `Match Latency (hrs)`
```tableau
AVG([time_to_first_match_hours])
```

7. `Users`
```tableau
COUNT([user_id])
```

8. `Onboarding Start Rate`
```tableau
AVG([onboarding_started])
```

9. `Onboarding Completion Rate`
```tableau
AVG([onboarding_completed])
```

10. `Booking Rate`
```tableau
AVG([session_booked])
```

11. `Noncompliance Flag`
```tableau
IIF([assigned_variant] <> [actually_exposed_variant], 1, 0)
```

12. `Noncompliance Rate`
```tableau
AVG([Noncompliance Flag])
```

13. `Activation Lift vs Control`
```tableau
WINDOW_AVG(IF [assigned_variant] = 'treatment' THEN [Activation Rate 7D] END)
-
WINDOW_AVG(IF [assigned_variant] = 'control' THEN [Activation Rate 7D] END)
```

## 4) Build worksheets (exact drag/drop)

## Sheet 1: KPI Cards
- Marks: Text
- Rows: `Measure Names`
- Text: `Measure Values`
- Filter `Measure Names` to:
  - `Activation Rate 7D`
  - `D7 Retention Rate`
  - `D30 Retention Rate`
  - `Cancellation Rate 30D`
  - `Support Tickets per User`
  - `Match Latency (hrs)`
- Columns: `assigned_variant`
- Format percentages for rate fields.

## Sheet 2: Funnel by Variant
- Columns: `Measure Names`
- Rows: `Measure Values`
- Filter `Measure Names` to:
  - `Users`
  - `SUM([onboarding_started])`
  - `SUM([onboarding_completed])`
  - `SUM([session_booked])`
  - `SUM([activated_within_7d])`
- Color: `assigned_variant`
- Marks: Bar

## Sheet 3: Daily Activation Trend
- Columns: `signup_date`
- Rows: `Activation Rate 7D`
- Color: `assigned_variant`
- Marks: Line

## Sheet 4: Retention Comparison
- Columns: `assigned_variant`
- Rows: `Measure Values`
- Filter `Measure Names` to:
  - `D7 Retention Rate`
  - `D30 Retention Rate`
- Color: `Measure Names`
- Marks: Bar

## Sheet 5: Guardrail Comparison
- Columns: `assigned_variant`
- Rows: `Measure Values`
- Filter `Measure Names` to:
  - `Cancellation Rate 30D`
  - `Match Latency (hrs)`
  - `Support Tickets per User`
- Color: `Measure Names`
- Marks: Bar

## Sheet 6: Activation by Acquisition Channel
- Columns: `acquisition_channel`
- Rows: `Activation Rate 7D`
- Color: `assigned_variant`
- Marks: Bar

## Sheet 7: Activation by Device
- Columns: `device`
- Rows: `Activation Rate 7D`
- Color: `assigned_variant`
- Marks: Bar

## Sheet 8: Activation by Age Bucket
- Columns: `age_bucket`
- Rows: `Activation Rate 7D`
- Color: `assigned_variant`
- Marks: Bar

## Sheet 9: Noncompliance Snapshot
- Columns: `assigned_variant`
- Rows: `Noncompliance Rate`
- Marks: Bar

## 5) Build final dashboard
- Create new Dashboard, size: Automatic
- Place sheets in this order:
  - Top row: KPI Cards
  - Middle left: Funnel by Variant
  - Middle right: Daily Activation Trend
  - Bottom left: Retention Comparison
  - Bottom middle: Guardrail Comparison
  - Bottom right: Noncompliance Snapshot
  - Second dashboard tab (segments): Sheets 6, 7, 8
- Add global filters to dashboard:
  - `signup_date`
  - `acquisition_channel`
  - `device`
  - `age_bucket`
  - `country`

## 6) Publish
- Click **Publish** in Tableau Online
- Name suggestion: `MindLift Experiment Dashboard`
- Add project description linking to your repo and readout.
