from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


def calculate_dashboard_metrics() -> dict[str, Any]:
    if not LOG_PATH.exists():
        records = []
    else:
        records = []
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue

    req_received = [r for r in records if r.get("event") == "request_received"]
    resp_sent = [r for r in records if r.get("event") == "response_sent"]
    req_failed = [r for r in records if r.get("event") == "request_failed"]

    # 1. Latency & TTFT
    latencies = sorted([int(r["latency_ms"]) for r in resp_sent if "latency_ms" in r])
    ttfts = sorted([int(r["ttft_ms"]) for r in resp_sent if "ttft_ms" in r])

    def p(arr: list[int], q: float) -> int:
        if not arr:
            return 0
        idx = int(len(arr) * (q / 100.0))
        return arr[min(idx, len(arr) - 1)]

    p50_lat = p(latencies, 50)
    p95_lat = p(latencies, 95)
    p99_lat = p(latencies, 99)
    p95_ttft = p(ttfts, 95)

    # 2. Traffic
    total_requests = len(req_received)
    rpm = round(total_requests / 60.0, 2) if total_requests else 0.0

    # 3. Errors & Retrieval
    total_attempts = total_requests or (len(resp_sent) + len(req_failed)) or 1
    error_rate = round((len(req_failed) / total_attempts) * 100, 2)
    error_breakdown: dict[str, int] = {}
    for r in req_failed:
        etype = r.get("error_type", "Unknown")
        error_breakdown[etype] = error_breakdown.get(etype, 0) + 1

    tool_ops = [r for r in resp_sent + req_failed if r.get("tool_name") == "retrieval"]
    tool_successes = [r for r in tool_ops if r.get("tool_success") is True]
    retrieval_success_rate = round((len(tool_successes) / len(tool_ops) * 100), 1) if tool_ops else 100.0

    # 4. Cost
    total_cost = round(sum(float(r.get("cost_usd", 0.0)) for r in resp_sent), 6)

    # 5. Tokens
    sum_tokens_in = sum(int(r.get("tokens_in", 0)) for r in resp_sent)
    sum_tokens_out = sum(int(r.get("tokens_out", 0)) for r in resp_sent)
    total_tokens = sum_tokens_in + sum_tokens_out

    # 6. Quality
    scores = [float(r["quality_score"]) for r in resp_sent if "quality_score" in r]
    avg_quality = round(sum(scores) / len(scores), 2) if scores else 0.85

    return {
        "p50_lat": p50_lat,
        "p95_lat": p95_lat,
        "p99_lat": p99_lat,
        "p95_ttft": p95_ttft,
        "total_requests": total_requests,
        "rpm": rpm,
        "error_rate": error_rate,
        "error_breakdown": error_breakdown,
        "retrieval_success_rate": retrieval_success_rate,
        "total_cost": total_cost,
        "tokens_in": sum_tokens_in,
        "tokens_out": sum_tokens_out,
        "total_tokens": total_tokens,
        "avg_quality": avg_quality,
        "records_count": len(records),
    }


def render_dashboard_html() -> str:
    m = calculate_dashboard_metrics()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>K4-L3B Day 13 Monitoring &amp; LLMOps Dashboard</title>
  <meta http-equiv="refresh" content="30">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f172a;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid #334155;
      margin-bottom: 24px;
    }}
    .header h1 {{
      font-size: 24px;
      font-weight: 700;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .meta-tags {{
      display: flex;
      gap: 12px;
      font-size: 13px;
    }}
    .badge {{
      background: #1e293b;
      padding: 6px 12px;
      border-radius: 6px;
      border: 1px solid #475569;
      color: #94a3b8;
    }}
    .badge strong {{ color: #e2e8f0; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }}
    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .card-title {{
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
    }}
    .card-title span.id {{
      color: #38bdf8;
      font-weight: 600;
    }}
    .stat-main {{
      font-size: 32px;
      font-weight: 800;
      color: #f1f5f9;
      margin: 8px 0;
    }}
    .stat-main span.unit {{
      font-size: 16px;
      color: #94a3b8;
      font-weight: 400;
    }}
    .stat-sub {{
      display: flex;
      gap: 12px;
      margin-top: 10px;
      font-size: 13px;
      color: #cbd5e1;
    }}
    .threshold {{
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px dashed #334155;
      font-size: 12px;
      color: #10b981;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .threshold.warn {{ color: #f59e0b; }}
    .threshold.err {{ color: #ef4444; }}
    .pill {{
      display: inline-block;
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>⚡ K4-L3B Day 13 Monitoring &amp; LLMOps</h1>
      <p style="color: #64748b; font-size: 13px; margin-top: 4px;">Service: day13-l3b-monitoring-llmops-lab | Student: Đinh Kim Thái (2A202602417)</p>
    </div>
    <div class="meta-tags">
      <div class="badge">Time Range: <strong>60 minutes</strong></div>
      <div class="badge">Refresh: <strong>30s</strong></div>
      <div class="badge">Total Records: <strong>{m['records_count']}</strong></div>
    </div>
  </div>

  <div class="grid">
    <!-- Panel 1: Latency -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Latency percentiles and TTFT</span>
          <span class="id">#latency</span>
        </div>
        <div class="stat-main">{m['p95_lat']} <span class="unit">ms (P95)</span></div>
        <div class="stat-sub">
          <span>P50: <strong>{m['p50_lat']}ms</strong></span>
          <span>•</span>
          <span>P99: <strong>{m['p99_lat']}ms</strong></span>
          <span>•</span>
          <span>TTFT P95: <strong>{m['p95_ttft']}ms</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">SLO Target</span>
        <span>Threshold: P95 &le; 3000 ms</span>
      </div>
    </div>

    <!-- Panel 2: Traffic -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Request traffic</span>
          <span class="id">#traffic</span>
        </div>
        <div class="stat-main">{m['total_requests']} <span class="unit">requests</span></div>
        <div class="stat-sub">
          <span>Traffic Rate: <strong>{m['rpm']} req/min</strong></span>
          <span>•</span>
          <span>Source: <strong>data/logs.jsonl</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">Threshold</span>
        <span>Expected traffic rate &ge; 1 req/min</span>
      </div>
    </div>

    <!-- Panel 3: Errors -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Error rate &amp; retrieval success</span>
          <span class="id">#errors</span>
        </div>
        <div class="stat-main">{m['error_rate']}% <span class="unit">errors</span></div>
        <div class="stat-sub">
          <span>Retrieval Success: <strong>{m['retrieval_success_rate']}%</strong></span>
          <span>•</span>
          <span>Errors: <strong>{len(m['error_breakdown'])} types</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">Threshold</span>
        <span>Error rate &le; 2.0% | Retrieval &ge; 90.0%</span>
      </div>
    </div>

    <!-- Panel 4: Cost -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Cost over time</span>
          <span class="id">#cost</span>
        </div>
        <div class="stat-main">${m['total_cost']:.4f} <span class="unit">USD</span></div>
        <div class="stat-sub">
          <span>Agg: <strong>Total window sum</strong></span>
          <span>•</span>
          <span>Model: <strong>claude-sonnet-4-5</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">Threshold</span>
        <span>Total Window Cost &le; $2.50 USD</span>
      </div>
    </div>

    <!-- Panel 5: Tokens -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Input and output tokens</span>
          <span class="id">#tokens</span>
        </div>
        <div class="stat-main">{m['total_tokens']:,} <span class="unit">tokens</span></div>
        <div class="stat-sub">
          <span>In: <strong>{m['tokens_in']:,}</strong></span>
          <span>•</span>
          <span>Out: <strong>{m['tokens_out']:,}</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">Threshold</span>
        <span>Total Tokens &le; 50,000 tokens</span>
      </div>
    </div>

    <!-- Panel 6: Quality -->
    <div class="card">
      <div>
        <div class="card-title">
          <span>Quality proxy</span>
          <span class="id">#quality</span>
        </div>
        <div class="stat-main">{m['avg_quality']} <span class="unit">/ 1.0</span></div>
        <div class="stat-sub">
          <span>Aggregation: <strong>Mean score</strong></span>
          <span>•</span>
          <span>Metric: <strong>Heuristic quality</strong></span>
        </div>
      </div>
      <div class="threshold">
        <span class="pill">Threshold</span>
        <span>Average Quality Score &ge; 0.75</span>
      </div>
    </div>
  </div>
</body>
</html>
"""
