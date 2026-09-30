# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đinh Kim Thái
- **MSSV:** 2A202602417
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/thaidinh1206/K4-L3-DAY13-DinhKimThai-2A202602417-Monitoring-LLMOps.git
- **Commit SHA cuối:** 73848c10f1a39028b72ffc129f6002d3df543ce0
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602417`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Pass toàn bộ: Basic JSON schema, Correlation ID propagation, Log enrichment, PII scrubbing |
| `validate_dashboard.py` | 6/6 panel hợp lệ | 6/6 panel hợp lệ | Đạt chuẩn contract cấu trúc config/dashboard.yaml và hiển thị live trên /dashboard |
| `pytest` | 22 passed | 22 passed | Toàn bộ 22 unit tests đều pass |
| Số traces hợp lệ | 10 traces | 63 observations | Đầy đủ cây quan hệ root, retrieval và generation trên project cá nhân Langfuse |
| Số PII leak | 0 | 0 | Đã scrub sạch toàn bộ email, phone VN, CCCD, thẻ thanh toán |
| Latency P95 / TTFT P95 | 2228.4ms / Chưa đo | 842ms / 50ms | P95 latency ổn định đạt chuẩn ngưỡng SLO <= 3000ms |
| Retrieval success rate | 100% (10/10) | 100% | Toàn bộ các lượt retrieval đều thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware`, request trước tiên được xóa context cũ (`clear_contextvars()`), sau đó trích xuất header `x-request-id` nếu có hoặc tự sinh mới theo format `req-<8-char-hex>` bằng `f"req-{uuid.uuid4().hex[:8]}"`. Correlation ID được bind vào structlog contextvars và gán vào `request.state.correlation_id`. Cuối cùng, middleware gắn `x-request-id` và `x-response-time-ms` vào header của HTTP response trả về.
- **Các metadata được ghi vào structured log:** Các trường bắt buộc gồm `ts` (ISO UTC), `level`, `service="api"`, `event` (`request_received`, `response_sent`, `request_failed`), `correlation_id`, `env` (môi trường runtime), `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model` (`claude-sonnet-4-5`), kèm các metric vận hành (`latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`).
- **Cách bảo đảm PII được scrub trước khi ghi:** Trong `app/logging_config.py`, processor `scrub_event` được đăng ký vào pipeline structlog ngay trước `JsonlFileProcessor` và `JSONRenderer`. Processor này duyệt đệ quy các trường (trừ các khóa định danh an toàn) và áp dụng bộ regex trong `app/pii.py` để che email, số điện thoại VN (+84/0), CCCD (12 số), thẻ tín dụng (16 số) và hộ chiếu thành các thẻ `[REDACTED_...]` trước khi dữ liệu được serialize thành JSON và ghi xuống file `data/logs.jsonl` hoặc stdout.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt điểm tuyệt đối 100/100 (0 records thiếu trường bắt buộc, 0 records thiếu enrichment context, 10 unique correlation IDs, 0 rò rỉ PII). Kiểm tra trực tiếp file `data/logs.jsonl` thấy các thông tin PII giả như email sinh viên, số điện thoại, thẻ tín dụng đều đã được che thành công.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Traces được ghi nhận trực tiếp vào project cá nhân `day13-k4-l3b-2A202602417` trên Langfuse Cloud thông qua API keys cấu hình trong `.env`. Trong metadata của mỗi trace thể hiện rõ `user_id_hash`, `session_id`, `environment="dev"`, `tags=["lab", feature, model]` và `correlation_id` khớp chính xác với từng dòng log trong `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:** Mỗi trace bắt đầu từ root span `day13-agent-request` bao bọc lấy observation `lab-agent-run` (type `agent`). Bên dưới phân nhánh thành 2 child observations rõ ràng: `retrieval` (type `retriever`) thực hiện tìm kiếm context và `generation` (type `generation`) gọi FakeLLM với đầy đủ thông tin model (`claude-sonnet-4-5`), template prompt đã bind, `input_tokens`, `output_tokens`, `cost_usd` và `ttft_ms`.
- **Cách nối trace với log:** Cả structured log và trace đều dùng chung trường định danh duy nhất `correlation_id` (dạng `req-<8-hex>`). Khi một request đi qua middleware, `correlation_id` được gán vào `structlog` contextvars để in vào file `data/logs.jsonl`, đồng thời truyền vào `propagate_attributes` của Langfuse để gắn vào `trace.metadata`. Khi điều tra, chỉ cần copy `correlation_id` từ log là tìm thấy ngay trace tương ứng trên Langfuse và ngược lại.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (mang label `baseline` và `production`)
- **Version/label candidate:** Version 2 (mang label `candidate`)
- **Trace ID của mỗi version:**
  - **Version 1 (`production` / `baseline`):** Trace ID `2ae56ba7e7c3bdc1c5c7febee34fd812` (Correlation ID: `req-6acc4e04`)
  - **Version 2 (`candidate` / promoted `production`):** Trace ID `36c0ca244357517602d0a9123078bf35` (Correlation ID: `req-18dd7dd8`)
- **Cách promote và rollback `production`:** Ban đầu Version 1 được gắn nhãn `baseline` và `production`. Khi cần promote Version 2 lên phục vụ người dùng thực tế, ta chỉ cần chuyển nhãn `production` trỏ sang Version 2 trên giao diện Langfuse UI (hoặc qua Langfuse SDK) mà không phải sửa hay deploy lại mã nguồn ứng dụng. Khi phát hiện Version 2 có vấn đề (hoặc cần khôi phục lại trạng thái cũ), ta thực hiện rollback tức thời bằng cách chuyển nhãn `production` quay trở lại trỏ về Version 1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dựng đủ 6 panel theo đúng contract `config/dashboard.yaml` sử dụng nguồn dữ liệu chuẩn `data/logs.jsonl` trong time range 60 phút và tự động refresh 30 giây:
  1. *Latency percentiles and TTFT (ms):* Đo P50, P95, P99 và TTFT P95 (ngưỡng threshold: P95 <= 3000ms).
  2. *Request traffic (req/min):* Đo tổng số request và tốc độ lưu lượng theo thời gian (ngưỡng >= 1 req/min).
  3. *Error rate and retrieval success (%):* Đo tỉ lệ lỗi tổng thể (threshold <= 2%), breakdown theo `error_type` và tỉ lệ thành công của retrieval tool (threshold >= 90%).
  4. *Cost over time (USD):* Đo chi phí tích lũy theo phút và toàn bộ cửa sổ (ngưỡng <= 2.5 USD).
  5. *Input and output tokens (tokens):* Đo tổng token đầu vào (`tokens_in`) và đầu ra (`tokens_out`) (ngưỡng <= 50,000 tokens).
  6. *Quality proxy (score 0-1):* Đo điểm chất lượng trung bình dựa trên heuristic context, answer & keywords (ngưỡng mean >= 0.75).
- **SLO và lý do chọn:** Primary SLO được đặt là `fast_successful_requests` với mục tiêu 99.5% request đạt chất lượng trong chu kỳ 28 ngày. Điều kiện đạt SLI: `event == "response_sent" and latency_ms <= 3000` trên tổng số `request_received`. Lý do chọn: Đảm bảo đa số người dùng nhận được phản hồi chính xác trong thời gian chấp nhận được (< 3 giây), cân bằng giữa trải nghiệm người dùng và chi phí tài nguyên.
- **Cách tính error budget:** Với target SLO là 99.5%, phần Error Budget cho phép là `100% - 99.5% = 0.5%`. Nếu hệ thống tiếp nhận 10,000 request trong chu kỳ 28 ngày, số lượng request tối đa được phép bị lỗi hoặc phản hồi chậm quá 3000ms là `10,000 * 0.5% = 50 requests`.
- **Ba alert và runbook tương ứng:**
  1. `HighLatencyP95` (Warning, duration 5m, kênh Slack `#k4-l3b-alerts`): Kích hoạt khi `p95(latency_ms) > 3000ms` kéo dài 5 phút. Runbook: Kiểm tra panel Latency, lọc log tìm `correlation_id` chậm, mở trace so sánh `retrieval` vs `generation`, rollback prompt nếu model sinh câu trả lời quá dài.
  2. `HighErrorRate` (Critical, duration 5m, kênh Slack `#k4-l3b-alerts`): Kích hoạt khi tỉ lệ lỗi `> 2%` trong 5 phút. Runbook: Kiểm tra panel Errors, lọc log theo `request_failed` và `error_type`, mở trace lỗi tìm span exception, restart service hoặc rollback config.
  3. `LowRetrievalSuccess` (Warning, duration 5m, kênh Slack `#k4-l3b-alerts`): Kích hoạt khi `tool_success_rate < 90%` trong 5 phút. Runbook: Kiểm tra panel Errors/Retrieval, lọc log tìm request lỗi tool, kiểm tra kết nối vector store và kích hoạt fallback corpus.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `2026-09-30 05:38:15Z` — `2026-09-30 05:38:32Z`
- **Triệu chứng từ metrics:** Dashboard ghi nhận `p95(latency_ms)` tăng vọt lên **4378 ms** (vượt ngưỡng SLO P95 <= 3000 ms), trong khi lưu lượng đạt 34 requests, error rate duy trì 0.0% và retrieval success rate đạt 100.0%. Hệ thống không bị crash hay trả mã lỗi 5xx mà bị suy giảm nghiêm trọng về thời gian đáp ứng (tail latency spike).
- **Log line và correlation ID liên quan:**
  - Correlation ID: `req-64efba6e` (feature: `monitoring`, session: `k4-l3b-challenge-s05`, user_id_hash: `68e37dc7cb5e`, latency: `2654 ms`).
  - Log line (dòng 69 trong `data/logs.jsonl`):
    ```json
    {"service": "api", "latency_ms": 2654, "ttft_ms": 50, "tokens_in": 35, "tokens_out": 160, "cost_usd": 0.002505, "quality_score": 0.8, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "env": "dev", "user_id_hash": "68e37dc7cb5e", "correlation_id": "req-64efba6e", "feature": "monitoring", "session_id": "k4-l3b-challenge-s05", "model": "claude-sonnet-4-5", "level": "info", "ts": "2026-09-30T05:38:23.798450Z"}
    ```
- **Trace ID và span gây ảnh hưởng:**
  - Trace ID: `baf636d90981bf9f20c0ad8e0e83fe82`
  - Span gây ảnh hưởng: Child span `retrieval` (loại `retriever`) chiếm **2.50s** trong tổng thời gian **2.65s** của request, trong khi child span `generation` chỉ mất **0.15s** ($0.002505, 195 tokens).
- **Root cause:** Sự cố `rag_slow` được kích hoạt trên hệ thống gây nghẽn trễ 2.5s ở tầng RAG retrieval (truy vấn context/vector store). Nguyên nhân gốc rễ nằm hoàn toàn ở tầng tìm kiếm tài liệu (retrieval bottleneck), không phải do quá trình sinh văn bản của mô hình LLM hay nghẽn mạng API.
- **Fix action:**
  1. Hủy kích hoạt sự cố trên hệ thống bằng lệnh: `python scripts/inject_incident.py --disable`.
  2. Khôi phục và tái lập kết nối tầng retrieval/vector database.
  3. Bổ sung cơ chế timeout (ví dụ 1.5s) kèm fallback cho retrieval span để tránh làm treo toàn bộ luồng xử lý của agent.
- **Preventive measure:**
  1. Kích hoạt alert `HighLatencyP95` (Warning, p95 > 3000ms trong 5m) và thiết lập thêm alert riêng cho `retrieval_latency_p95 > 1500ms`.
  2. Bổ sung circuit breaker và bộ nhớ đệm (caching) cho các truy vấn retrieval thường gặp.
  3. Đưa kịch bản kiểm thử độ trễ RAG (`scripts/load_test.py`) vào CI/CD pipeline trước khi release.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định triển khai recursive scrubbing (`scrub_event`) ở tầng middleware structlog ngay trước khi ghi JSON và sử dụng `@observe` phân tách rõ 2 child span riêng biệt (`retriever` và `generation`). Lý do: Đảm bảo dữ liệu nhạy cảm (PII) không bao giờ bị ghi lén vào logs/traces, đồng thời cho phép phân lập chính xác nguồn gốc gây chậm (do RAG hay do LLM) khi điều tra sự cố.
- **Một lỗi/blocker đã gặp:** Khi thực hiện rollback prompt từ v2 về v1, hệ thống vẫn phản hồi với prompt v2 do cơ chế in-memory cache của Langfuse SDK (`cache_ttl_seconds=60`).
- **Cách tìm nguyên nhân và xử lý:** Kiểm tra mã nguồn khởi tạo Langfuse prompt client trong `app/agent.py`, nhận diện TTL bộ nhớ đệm 60s. Khắc phục bằng cách chạm reload file server và kiểm tra sau thời gian hết hạn TTL, xác nhận prompt v1 đã được phục hồi thành công.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - *Metrics (Dashboard):* Cung cấp cái nhìn vĩ mô (Aggregated) về sức khỏe hệ thống (P95 latency, error rate, token traffic), giúp trả lời câu hỏi: *Có sự cố gì đang diễn ra và xảy ra vào lúc nào?*
  - *Logs (Structured JSONL):* Cung cấp bản ghi chi tiết từng sự kiện có ngữ cảnh (`correlation_id`, `session_id`, `user_id_hash`), giúp trả lời câu hỏi: *Request cụ thể nào bị ảnh hưởng?*
  - *Traces (Waterfall Spans):* Cung cấp chi tiết vi mô sâu bên trong từng bước thực thi của một request, giúp trả lời câu hỏi: *Thành phần nào (retrieval hay generation) là nguyên nhân gốc rễ gây ra lỗi hoặc chậm trễ?*
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  - *Prompt versioning:* Quản lý vòng đời prompt có cấu trúc như mã nguồn, tách biệt môi trường staging/production.
  - *Token & Cost:* Giám sát chặt chẽ ngân sách vận hành LLM, ngăn ngừa rủi ro bùng nổ token ngoài ý muốn.
  - *SLO & Error Budget:* Thước đo định lượng cam kết chất lượng dịch vụ với người dùng và đặt ra giới hạn an toàn cho việc thử nghiệm các tính năng mới.
  - *Rollback:* Cơ chế sống còn giúp khôi phục hệ thống về trạng thái ổn định chỉ trong vài giây khi phiên bản prompt mới phát sinh lỗi chất lượng hoặc độ trễ.
- **Điều quan trọng nhất đã học:** Hiểu rõ và làm chủ toàn bộ vòng đời quan sát hệ thống LLMOps: từ chuẩn hóa logging, làm sạch PII, phân tầng distributed tracing, xây dựng bảng điều khiển vận hành cho đến quy trình ứng phó và truy vết sự cố theo chuẩn công nghiệp.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Hệ thống hiện đang chạy trên môi trường lab với mock data cho RAG và LLM; trong tương lai có thể tích hợp trực tiếp với OpenTelemetry collector và cơ sở dữ liệu vector production (như Qdrant hoặc Pinecone).

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
