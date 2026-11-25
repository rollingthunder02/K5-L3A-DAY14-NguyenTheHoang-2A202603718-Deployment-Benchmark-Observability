# Benchmark & Observability Report — Day 14

- **Họ tên:** Nguyễn Thế Hoàng
- **Ngày chạy CP7:** 25/11/2026 (GMT+7)
- **Môi trường CP7:** Ubuntu WSL2 trên Windows, Python 3.11.18, 20 CPU logic và 7.751 MiB RAM theo WSL. Agent và công cụ đo chạy trên cùng máy qua loopback.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của `load_test.py`, theo dõi độ trễ của phần lớn request thành công. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của `load_test.py`, tính trên tất cả request trong lượt đo. |
| Accuracy trên golden dataset | 100% và 0 regression sau sửa | Quality gate cuối của CP7. Eval baseline dùng ngưỡng mặc định 80%. |

### Kiểm tra `/metrics` (Exercise 7.1)

Sau một lần gọi hợp lệ, `/metrics` xuất `http_requests_total` kiểu Counter, `agent_in_flight_requests` kiểu Gauge và `agent_question_length_chars` kiểu Histogram với `agent_question_length_chars_count 1.0`. Histogram ghi số ký tự của câu hỏi trong `/ask` theo bucket, không dùng nội dung câu hỏi làm label. Middleware dùng route template và gom URL không khớp vào `unmatched`, giúp số time series giữ ổn định khi ID hoặc đường dẫn thay đổi.

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

Mỗi lượt gửi 300 request, với `MOCK_SLOW_RATE=0.03` và `MOCK_ERROR_RATE=0.01`. Dữ liệu gốc nằm trong `reports/load_v2_c*.json`. Percentile chỉ tính trên phản hồi 200. RPS và error rate tính trên toàn bộ lượt gọi.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.33 | 192.5 | 221.5 | 1687.7 | 1.00% | PASS |
| 10 | 43.42 | 195.4 | 226.1 | 1680.5 | 1.00% | PASS |
| 50 | 96.52 | 234.8 | 333.3 | 1734.9 | 1.67% | PASS |
| 100 | 49.75 | 593.1 | 3821.3 | 4044.1 | 1.00% | FAIL · p95 |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS tăng gần 10 lần khi tăng concurrency từ 1 lên 10. Ở 50, RPS đạt 96.52, rồi giảm còn 49.75 ở 100 trong khi p95 tăng lên 3821.3 ms. Client và server chia sẻ cùng máy, nên hàng đợi xử lý, kết nối và chi phí lập lịch đều có thể góp phần ở tải cao. Một lượt đo mỗi mức chưa đủ để xác định nút thắt cụ thể hoặc suy rộng sang môi trường cloud.

### 2.2 Tail latency

Mỗi lượt gửi 300 request ở concurrency 20, giữ `MOCK_ERROR_RATE=0.01` và khởi động lại v2 với từng mức `MOCK_SLOW_RATE`. Nguồn số liệu là `reports/load_v2_slow_*.json`.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 237.0 | 443.3 | 468.9 |
| 0.03 (mặc định) | 251.5 | 285.4 | 1703.2 |
| 0.1 | 378.5 | 1696.5 | 1726.8 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

Khi tỷ lệ mô phỏng tăng từ 0 lên 3%, p99 tăng 1234.3 ms còn trung bình tăng 14.5 ms. p95 của lượt 3% thấp hơn lượt 0%, cho thấy độ dao động giữa các lượt chạy ngắn. Khi tỷ lệ chậm tăng đến 10%, p95 cũng vượt ngưỡng 500 ms. Percentile phản ánh nhóm người dùng gặp request chậm rõ hơn trung bình.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

Ba lượt eval dùng cùng 23 câu, `MOCK_ERROR_RATE=0` và `MOCK_SLOW_RATE=0` để so sánh chất lượng và độ trễ cơ bản. Kết quả gốc nằm trong `reports/eval_*.json`.

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 58.1 | 108.8 | 114.6 |
| Tổng cost (USD) | 0.000418 | 0.000757 | 0.000798 |
| Cost / câu đúng (USD) | 0.00041775 | 0.00003607 | 0.00003472 |
| Latency p95 (ms) | 190.1 | 214.9 | 215.3 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%, 0 regression so với v1) | PASS (ngưỡng 100%, 0 regression so với v2) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| `security-02` | `token`, `hết hạn`, `chữ ký` | Thêm tài liệu JWT phân biệt token có chữ ký và thời hạn với API key. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Thêm tài liệu HPA về các metric cấu hình để điều chỉnh số pod. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

So với v1, v2 trước sửa có thêm bước retrieval, dùng nhiều hơn 50.7 token/câu và p95 tăng 24.8 ms. Tổng chi phí mock tăng, nhưng chi phí trên một câu đúng giảm từ 0.00041775 USD xuống 0.00003607 USD vì số câu đúng tăng từ 1 lên 21. Sau khi sửa knowledge base, v2 đúng thêm hai câu, không có regression và chi phí trên câu đúng giảm tiếp còn 0.00003472 USD.

**Áp dụng quality gate trong CI:** trong job pull request, khởi động v2 với lỗi mô phỏng tắt, chờ `/health`, rồi chạy `python eval/run_eval.py --url http://127.0.0.1:8002 --min-accuracy 0.85 --baseline <đường-dẫn-baseline-đã-duyệt>`. Script thoát mã `1` nếu accuracy dưới ngưỡng hoặc một câu từng đúng trở thành sai. Đặt job này làm required status check và để mã thoát lan tới CI để PR lỗi không thể merge. Lượt chạy cuối CP7 dùng ngưỡng nghiêm hơn `1.0` với `reports/eval_v2.json` làm baseline.

---

## 4. Observability stack (production)

- **Ngày chạy CP8:** 25/11/2026 (GMT+7)
- **Môi trường CP8:** Docker Desktop trên Windows với backend WSL2. Các service chạy trong Compose project `k5-day14-observability`, agent giới hạn 0,5 CPU và 256 MiB RAM mỗi replica.

Prometheus `v3.16.0` và Grafana `13.2.4` thoát mã 139 trên máy chạy bài. Lượt đo dùng `PROMETHEUS_IMAGE=prom/prometheus:v3.5.0` và `GRAFANA_IMAGE=grafana/grafana:12.1.1`. Hai biến này được lưu trong `production/.env` cục bộ để Compose dùng khi chạy lại trên máy này. Cấu hình scrape và các ngưỡng cảnh báo giữ theo đề. Bộ kiểm thử quy tắc Prometheus có sẵn chạy thành công với `promtool`.

### 4.1 Ảnh minh chứng

- [x] [Grafana trong lượt Locust 100 user với 1 replica](screenshots/grafana-dashboard.png)
- [x] [Jaeger với trace chậm và span LLM](screenshots/jaeger-slow-trace.png)
- [x] [Jaeger với trace lỗi và event exception](screenshots/jaeger-error-trace.png)
- [x] [Hai cảnh báo A và B cùng firing trong Prometheus](screenshots/prometheus-alert-firing.png)

### 4.2 Thí nghiệm phá hệ thống

Locust giữ khoảng 30 user. A và B được bật cùng lúc để ghi bằng chứng hai cảnh báo firing trên cùng một trang. Thời gian tính từ khi áp dụng cấu hình đến lần đầu quan sát trạng thái `firing` qua API Prometheus.

| # | Thay đổi | Alert nào firing | Thời gian đến firing | Panel phản ánh |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 76.0 s | Error rate |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 136.1 s | Latency p95 |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 157.4 s | Cost burn rate (USD/giờ) |
| D | `docker pause` 1 instance | `AgentInstanceDown` | 41.5 s | Instances up |
| E | `AGENT_VERSION=v1` | Không firing tại lúc kiểm tra | — | Retrieval hit ratio, Tokens/s |

Khi hai cảnh báo A và B firing, Prometheus ghi tỷ lệ 5xx 20.4% và p95 1.89 giây ở thời điểm ghi nhận tương ứng. Prometheus ghi nhận mức cao nhất 16.00 USD/giờ trong cửa sổ đo C. Ở D, replica bị pause vẫn có tên trong DNS nên Prometheus còn thử scrape và ghi `up = 0`. Log Nginx ghi 31 phản hồi 504 cho `POST /ask` trong cửa sổ pause. Các phản hồi do gateway tạo nằm ngoài bộ đếm HTTP của agent.

Ở E, đánh giá v1 qua Nginx đạt 1/23 câu (4.3%) và có 22 regression so với baseline v2 đã duyệt. Trong production, chạy eval định kỳ theo phiên bản và ở bước canary, rồi cảnh báo khi accuracy hoặc số câu regression vượt ngưỡng. Các alert vận hành hiện tại theo dõi latency, lỗi HTTP, khả dụng và chi phí.

[Ảnh dashboard và trang Alerts của các thí nghiệm](screenshots/experiments/)

### 4.3 Debug bằng trace

**Trace chậm**

Trace `dd49a46df21973da9e7f7d9eda9ca417` có span `POST /ask` dài 1722.4 ms. Span `chat mock-llm-small` chiếm 1698.4 ms (98.6%). [Ảnh Jaeger](screenshots/jaeger-slow-trace.png)

Log JSON cùng `trace_id`

```json
{"ts": "2026-11-25T10:52:23.816714+00:00", "level": "INFO", "service": "observable-agent", "instance": "976c18e6f320", "event": "llm_call", "trace_id": "dd49a46df21973da9e7f7d9eda9ca417", "span_id": "9a2766cd7c2c0fb1", "request_id": "ee3a07706127", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 95, "output_tokens": 55, "cost_usd": 4.7e-05, "llm_ms": 1698.2}
```

**Trace lỗi**

Trace `bbeb48bc7cf9cfa82d7efdc917d46f7e` có span `POST /ask` dài 858.3 ms. Span `chat mock-llm-small` chiếm 838.3 ms (97.7%). Span này có event `exception` với thông báo `Upstream LLM error: 503 Service Unavailable (mock)`. [Ảnh Jaeger](screenshots/jaeger-error-trace.png)

Log JSON cùng `trace_id`

```json
{"ts": "2026-11-25T10:52:28.110921+00:00", "level": "INFO", "service": "observable-agent", "instance": "3ea08b823e96", "event": "llm_error", "trace_id": "bbeb48bc7cf9cfa82d7efdc917d46f7e", "span_id": "73c0044c0ce2c379", "request_id": "4411537f5a8e", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

Locust tăng 10 user mỗi giây. Cả hai lượt chạy dùng agent v2, `mock-llm-small`, `MOCK_ERROR_RATE=0.01` và `MOCK_SLOW_RATE=0.03`. Bảng dùng riêng hàng `POST /ask` trong các file CSV, vì Locust cũng gọi `GET /health`. RPS tính trên toàn lượt chạy và Failures là số request lỗi.

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 60.32 | 190 | 240 | 1700 | 70 (0.97%) |
| 3 | 60.09 | 190 | 220 | 1700 | 68 (0.95%) |

Khi tăng từ 1 lên 3 replica, p95 giảm từ 240 ms xuống 220 ms. RPS giảm 0.4% với cùng 100 user. p99 vẫn ở khoảng 1.7 giây, phù hợp với nhánh chờ mô phỏng trong span LLM. Thêm replica có thể giảm tranh chấp CPU và hàng đợi ở agent, đồng thời giữ nguyên độ trễ do mỗi lượt gọi LLM mô phỏng. Mỗi mốc có một lượt đo và Locust dùng số user cố định có thời gian nghỉ, nên số liệu chưa xác định công suất tối đa.

---

## 6. Kết luận

- p95 và p99 phản ánh các nhóm request chậm mà trung bình dễ che khuất. Khi mô phỏng 3% request chậm trong CP7, p99 tăng rõ nhất.
- Accuracy và chi phí trên mỗi câu đúng giúp so sánh các bản agent. Quality gate trên golden dataset phát hiện regression dù chỉ số vận hành có thể vẫn bình thường.
- Metrics cho biết thời điểm và loại bất thường. Trace chỉ ra span chiếm thời gian hoặc phát sinh lỗi. `trace_id` nối span đó với log JSON cùng request.

Ở production, mình sẽ theo dõi riêng tỷ lệ 502/504 và latency tại gateway, bổ sung synthetic check từ phía người dùng và chạy eval định kỳ theo phiên bản agent. Cảnh báo chất lượng dựa trên accuracy và số câu regression để phát hiện lỗi nội dung sau deploy.
