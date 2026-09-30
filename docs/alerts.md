# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: HighLatencyP95
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack #k4-l3b-alerts
- SLI/SLO liên quan: Latency P95 của response_sent.latency_ms (SLO <= 3000ms)
- Điều kiện và thời gian duy trì: p95(latency_ms) > 3000ms kéo dài liên tục 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn trước khi nhận được câu trả lời từ chatbot.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Latency để xác nhận P95/P99 và khoảng thời gian tăng vọt.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao bất thường.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính (`retrieval` vs `generation`) để xác định bước gây chậm.
- Mitigation tạm thời: Nếu do prompt mới làm sinh quá dài thì rollback prompt về version cũ; nếu do retrieval chậm thì kích hoạt cache hoặc fallback context.
- Owner: student-2A202602417

## Alert 2

- Tên: HighErrorRate
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack #k4-l3b-alerts
- SLI/SLO liên quan: Error rate (tỉ lệ request_failed trên request_received, SLO <= 2%)
- Điều kiện và thời gian duy trì: error_rate_pct > 2% duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng gặp lỗi 500 hoặc không nhận được phản hồi từ hệ thống.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Errors kiểm tra tỉ lệ lỗi và breakdown theo `error_type`.
  2. Lọc `data/logs.jsonl` tìm các event `request_failed` có `correlation_id` tương ứng để xem thông điệp lỗi chi tiết.
  3. Mở trace có cùng `correlation_id` trên Langfuse kiểm tra span nào bị đánh dấu đỏ / exception.
- Mitigation tạm thời: Khởi động lại service nếu nghẽn tài nguyên; rollback prompt/config về bản ổn định gần nhất; chuyển hướng traffic nếu cần.
- Owner: student-2A202602417

## Alert 3

- Tên: LowRetrievalSuccess
- Severity: warning
- Duration: 5m
- Kênh thông báo: Slack #k4-l3b-alerts
- SLI/SLO liên quan: Tỉ lệ thành công của Retrieval tool (SLO >= 90%)
- Điều kiện và thời gian duy trì: tool_success_rate_pct < 90% duy trì trong 5 phút
- Ảnh hưởng tới người dùng: Chatbot trả lời không có tài liệu dẫn chứng, chất lượng câu trả lời bị suy giảm.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard panel Errors xem tỉ lệ retrieval success giảm từ mốc thời gian nào.
  2. Lọc log `data/logs.jsonl` kiểm tra các sự kiện có `tool_name="retrieval"` và `tool_success=False`.
  3. Mở trace tương ứng trên Langfuse kiểm tra observation `retrieval` xem vector store có gặp lỗi timeout hay không.
- Mitigation tạm thời: Chuyển sang fallback corpus tĩnh hoặc khởi động lại vector store connection pool.
- Owner: student-2A202602417
