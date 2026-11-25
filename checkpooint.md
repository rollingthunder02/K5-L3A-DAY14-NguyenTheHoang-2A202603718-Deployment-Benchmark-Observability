# Day 14 — Hướng dẫn thực hành theo checkpoint

Thứ tự lớp K5: **CP0 → CP1 → CP2 → CP3 (Part 4) → CP4 (Part 5) → CP5 (Part 6) → CP6 (Part 3) → CP7 → CP8**. CP0–CP7 làm trong 4 giờ tại lớp. CP8 làm sau buổi lab, trước hạn nộp theo [SUBMISSION.md](SUBMISSION.md) hoặc thông báo của Lab Coach. Nếu kẹt 10 phút, ghi lỗi và hỏi Lab Coach để giữ giờ cho CP5.

Đề chi tiết ở [CODE_LAB.md](CODE_LAB.md). Khi lệnh trong đề khác với lưu ý của lớp, dùng [README.md](README.md) và [CHECKPOINTS.md](CHECKPOINTS.md). Đọc [RULES.md](RULES.md) trước khi làm. Mọi số đo và ảnh dùng kết quả bạn tự chạy.

## CP0 · Chuẩn bị (10 phút)

1. Dùng bản fork cá nhân, đặt tên theo mẫu trong SUBMISSION. Từ PowerShell mở Ubuntu/WSL2 bằng `wsl`. Trong Docker Desktop bật tích hợp với distro WSL của bạn.
2. Trong WSL, vào repo và thiết lập môi trường. Mở terminal mới thì vào lại repo và source lại venv. Ở terminal mới, chạy lại hai dòng cd/export ở dưới và dòng source. Trong các bước sau, **mỗi khối có `cd "$REPO/..."` bắt đầu từ terminal WSL đã thiết lập biến này**.

```bash
cd '/mnt/d/Lab new/K5-L3A-DAY14-NguyenTheHoang-2A202603718-Deployment-Benchmark-Observability'
export REPO="$PWD"
git remote -v
python3 --version
docker compose version
docker run --rm hello-world
python3 -m venv .venv
source .venv/bin/activate
python -c 'import os; print(os.name)'
mkdir -p screenshots
```

**Qua mốc khi** Python ≥ 3.11, lệnh cuối kiểm tra Python in `posix`, Docker chạy được và `origin` trỏ đến fork. Nếu thiếu module `venv`, cài gói `python3-venv` tương ứng với Python trong WSL. Tạo `MISSION_ANSWERS.md` ở gốc repo, đặt các mục Part 1–5, kết quả Part 6 và **AI log**. Trong AI log ghi câu hỏi, gợi ý nhận được, phần bạn tự sửa và cách tự kiểm tra.

## CP1 · Localhost vs Production (20 phút)

```bash
cd "$REPO/01-localhost-vs-production/develop"
python -m pip install -r requirements.txt
python app.py
```

Ở terminal thứ hai:

```bash
curl -i -X POST 'http://localhost:8000/ask?question=Hello'
```

Bản develop nhận `question` qua query string. Sau khi thấy 200, dừng server bằng Ctrl+C. Đọc `develop/app.py` rồi đối chiếu `production/app.py` và `production/config.py`. Nếu muốn xem trực tiếp các probe, chạy `python -m pip install -r requirements.txt` rồi `python app.py` trong `01-localhost-vs-production/production` và gọi `/health`, `/ready`. Dừng trước CP2.

**Ghi vào Part 1:** ít nhất 5 anti-pattern, chỉ ra dòng code, lưu kết quả gọi develop và lập bảng `Tiêu chí | Develop | Production | Vì sao quan trọng`. So sánh cấu hình, log, lỗi, health/readiness và vòng đời ứng dụng.

## CP2 · Docker (30 phút)

Từ gốc repo, build với context `.` vì các lệnh COPY dùng đường dẫn tính từ gốc.

```bash
cd "$REPO"
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run --rm -d --name day14-docker-demo -p 8000:8000 my-agent:develop
curl -i -X POST 'http://localhost:8000/ask?question=Hello'
docker stop day14-docker-demo
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent

cd "$REPO/02-docker/production"
touch .env.local
docker compose -p k5-day14-docker up -d --build
docker compose -p k5-day14-docker ps
curl -i http://localhost/health
curl -i http://localhost/ask -H 'Content-Type: application/json' -d '{"question":"Hello"}'
docker compose -p k5-day14-docker down
```

Nếu stack chưa sẵn sàng, xem `docker compose -p k5-day14-docker logs --tail=50` trước khi `down`. Nếu cổng 80/443 bị chiếm, kiểm tra service nào đang dùng cổng. **Ghi vào Part 2:** trả lời 4 câu Exercise 2.1, lưu HTTP output, ghi 2 kích thước từ `docker images`, tính phần trăm giảm bằng `(develop - production) / develop × 100%`, vẽ luồng client → Nginx → agent và vị trí Redis/Qdrant. Đọc thứ tự COPY để giải thích lúc nào layer cài dependencies được tái sử dụng.

## CP3 · API Security (25 phút, Part 4)

```bash
cd "$REPO/04-api-gateway/develop"
python -m pip install -r requirements.txt
AGENT_API_KEY=secret-key-123 python app.py
```

Ở terminal gọi API, chạy hai lệnh và lưu 401, 200:

```bash
curl -i http://localhost:8000/ask -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -i http://localhost:8000/ask -H 'X-API-Key: secret-key-123' -H 'Content-Type: application/json' -d '{"question":"Hello"}'
```

Ctrl+C ở terminal server, đổi sang bản JWT:

```bash
cd "$REPO/04-api-gateway/production"
python -m pip install -r requirements.txt
python app.py
```

Ở terminal gọi API:

```bash
TOKEN=$(curl -fsS http://localhost:8000/auth/token -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"demo123"}' |
  python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
test -n "$TOKEN" || echo 'Chưa lấy được JWT, kiểm tra server trước khi chạy tiếp'
```

Khi đã lấy được token:

```bash
curl -i http://localhost:8000/ask -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"question":"Explain JWT"}'
for i in {1..20}; do
  curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8000/ask \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
done
```

**Qua mốc khi** thấy 429 trong vòng lặp bằng tài khoản student (10 request/phút). Ghi Part 4: code kiểm key, luồng JWT, thuật toán và giới hạn theo role trong `rate_limiter.py`, cách `cost_guard.py` kiểm ngân sách và cộng usage. Dán output đã che token, dừng server.

## CP4 · Scaling & Reliability (20 phút, Part 5)

Đọc Exercise 5.1–5.5, đối chiếu nơi lưu session trong `develop/app.py` và `production/app.py`. Thực hành kiểm tra bằng stack có Redis:

```bash
cd "$REPO/05-scaling-reliability/production"
python -m pip install -r requirements.txt
touch .env.local
docker compose -p k5-day14-scaling up -d --build --scale agent=3
docker compose -p k5-day14-scaling ps
curl -i http://localhost:8080/health
curl -i http://localhost:8080/ready
python test_stateless.py
docker compose -p k5-day14-scaling down
```

**Ghi vào Part 5:** khác nhau giữa liveness và readiness, cách Uvicorn xử lý SIGTERM, vì sao session trong RAM có thể đứt giữa các replica, log test và cách đọc `served_by` cùng history. Stack dùng `POST /chat`, cổng 8080. Script gửi 5 câu trong cùng session rồi kiểm history. Dùng output thực tế để kết luận.

## CP5 · Hoàn thiện agent production (60 phút, Part 6)

Làm trực tiếp trong `06-lab-complete/`. Hợp đồng HTTP và Docker nằm trong [README của Part 6](06-lab-complete/README.md). Dùng code mẫu Part 1, 4, 5 để hiểu cách ghép và đối chiếu hợp đồng trước khi áp dụng.

```bash
cd "$REPO/06-lab-complete"
python -m pip install -r requirements.txt
rg -n TODO app Dockerfile docker-compose.yml .dockerignore .env.example railway.toml render.yaml
python check_production_ready.py --static-only
```

| Thứ tự | Sửa ở đâu | Tự kiểm sau khi sửa |
|---|---|---|
| 1 | `app/config.py`, `.env.example`, `app/main.py` | Đọc biến môi trường theo hợp đồng, thêm `/health` và log JSON mỗi dòng. |
| 2 | `app/auth.py` và dependency của `/ask` | Thiếu/sai `X-API-Key` → 401. Key đúng và body có `question` → 200 khi Redis sẵn sàng. |
| 3 | `app/redis_client.py`, `/ready` | Redis còn sống → 200. Redis mất kết nối → `/ready` 503 trong khi `/health` vẫn 200. |
| 4 | `app/rate_limiter.py` | Key được cấp tối đa `RATE_LIMIT_PER_MINUTE` lượt trong 60 giây. Dùng thao tác nguyên tử Redis cho cập nhật bộ đếm và TTL. Vượt → 429, state còn sau restart agent. |
| 5 | `app/cost_guard.py`, `/ask` | Kiểm kỳ ngân sách trước khi gọi và ghi chi phí sau khi xử lý. Vượt ngân sách ngày hoặc tháng → 402. State dùng Redis để chia sẻ giữa worker. |
| 6 | `app/main.py`, `Dockerfile`, `.dockerignore` | Dọn kết nối khi shutdown, giữ hành vi SIGTERM của Uvicorn. Image multi-stage, Python slim, non-root, HEALTHCHECK, dưới 500 MB. CMD dùng `exec uvicorn`, nghe `PORT` và chạy 2 workers. |
| 7 | `docker-compose.yml`, `railway.toml` hoặc `render.yaml` | Compose có agent + Redis, `REDIS_URL` nội bộ trỏ `redis` và agent có `depends_on`. Deploy config trỏ health check về `/health`, secret đặt từ môi trường. |

Chạy `--static-only` sau khi sửa các file cấu hình. Sau khi Compose hợp lệ, test từ cùng thư mục:

```bash
docker compose -p k5-day14-final config --quiet
docker compose -p k5-day14-final up -d --build
docker compose -p k5-day14-final ps
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
docker compose -p k5-day14-final stop redis
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
docker compose -p k5-day14-final up -d redis
docker compose -p k5-day14-final down
python check_production_ready.py
```

Nếu Compose của bạn yêu cầu key qua env, đặt key test local trước khi chạy. Khi một tiêu chí fail, xem dòng lỗi của chính tiêu chí đó, sửa file tương ứng rồi chạy lại. `--skip-docker` dùng trong lúc phát triển. **Qua mốc khi** bản đầy đủ in **PASS 12/12**. Dán phần “Checklist Deliverable” vào `MISSION_ANSWERS.md`. Giữ nguyên script chấm.

## CP6 · Deploy agent Part 6 (25 phút, Part 3)

Chọn Railway hoặc Render. Dùng service từ `06-lab-complete/` của fork, với Dockerfile và cấu hình đã làm ở CP5.

1. Tạo service agent trên cloud. Với Railway, repo lab hướng dẫn dùng `railway login`, `railway link` để nối dự án đã tạo, rồi chạy `railway up` trong `06-lab-complete/`, chọn đúng service agent nếu dự án có nhiều service. Nếu tích hợp bằng GitHub, chọn thư mục gốc của service là `06-lab-complete`. Với Render, dùng cấu hình của Part 6 và đặt đúng thư mục build.
2. Tạo Redis trong dự án. Đặt `REDIS_URL` của agent bằng URL kết nối Redis. Đặt `AGENT_API_KEY` mới và các biến cần từ `.env.example` trên nền tảng. Để `PORT` của process khớp cổng nền tảng định tuyến.
3. Bật public domain, xem log build/startup, rồi tự kiểm. Nếu `/health` trả 200 nhưng `/ready` trả 503, kiểm tra host, cổng và thông tin xác thực Redis trong môi trường của **service agent**.

```bash
URL='https://THAY-BANG-DOMAIN-CUA-BAN'
read -rsp 'API key: ' KEY; echo
curl -i "$URL/health"
curl -i "$URL/ready"
curl -i "$URL/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -i "$URL/ask" -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
unset KEY
```

Kỳ vọng theo thứ tự **200 / 200 / 401 / 200**. Che thông tin nhạy cảm trong output trước khi chụp. Chụp `screenshots/dashboard.png`, `screenshots/running.png`, `screenshots/test.png`. Tạo `DEPLOYMENT.md` có URL, nền tảng, lệnh test, tên biến đã đặt và link ảnh. Ghi kết quả deploy vào Part 3 của `MISSION_ANSWERS.md`, đọc `03-cloud-deployment/production-cloud-run/cloudbuild.yaml` và `service.yaml`, so sánh cách Railway và Render khai báo build, health check, secret, rồi viết 3–5 dòng về luồng build → đẩy image → triển khai (Exercise 3.3 chỉ đọc cấu hình).

## CP7 · Benchmark local (45 phút, Part 7 Bước 1)

```bash
cd "$REPO"
cp -n 06-lab-complete/benchmark-observability/BENCHMARK_REPORT_TEMPLATE.md BENCHMARK_REPORT.md
cd "$REPO/06-lab-complete/benchmark-observability/develop"
python -m pip install -r requirements.txt
mkdir -p reports
```

Chạy v1 và v2 ở **hai terminal riêng**, cả hai đứng trong thư mục `develop` của Part 7:

```bash
# Terminal v1
AGENT_VERSION=v1 PORT=8001 MOCK_ERROR_RATE=0 python app.py
```

```bash
# Terminal v2
AGENT_VERSION=v2 PORT=8002 MOCK_ERROR_RATE=0 MOCK_SLOW_RATE=0.03 python app.py
```

Ở terminal thứ ba, cũng đứng trong `develop`:

```bash
curl -fsS http://localhost:8002/ask -H 'Content-Type: application/json' -d '{"question":"Prometheus là gì?"}'
curl -fsS http://localhost:8002/metrics
```

- **7.1** Lấy ví dụ Counter, Gauge, Histogram từ `/metrics` và giải thích vì sao dùng route template làm label. Trong `app.py`, khai báo Histogram `agent_question_length_chars` và gọi `observe(len(body.question))` trong `/ask`. Restart v2 và gọi lại `/ask`, tìm tên metric trong `/metrics`.
- **7.2** Đo v2 với 300 request ở mỗi mức concurrency. Ghi RPS, p50/p95/p99 và kết quả SLO (mặc định p95 ≤ 500 ms, lỗi ≤ 2%). Exit code 1 có thể là SLO fail. Đọc JSON và ghi kết quả đúng lần chạy.

```bash
for c in 1 10 50 100; do
  python load_test.py --url http://localhost:8002 --requests 300 --concurrency "$c" --out "reports/load_v2_c$c.json"
done
```

Đo tail latency ở `0`, `0.03`, `0.1`. Với **từng mức**, Ctrl+C ở terminal v2, chạy lại lệnh bật v2 với `MOCK_SLOW_RATE` tương ứng. Ở terminal benchmark đặt `s` bằng đúng mức đang chạy rồi đo. Giữ nguyên số request, concurrency và tỷ lệ lỗi cho cả ba lần.

```bash
s=0  # lần sau đặt 0.03, rồi 0.1
python load_test.py --url http://localhost:8002 --requests 300 --concurrency 20 \
  --out "reports/load_v2_slow_$s.json"
```

- **7.3** Lưu baseline trước khi sửa. Giữ `MOCK_ERROR_RATE=0` để lỗi mô phỏng không làm nhiễu kết quả đánh giá chất lượng.

```bash
python eval/run_eval.py --url http://localhost:8001 --out reports/eval_v1.json
python eval/run_eval.py --url http://localhost:8002 --baseline reports/eval_v1.json --out reports/eval_v2.json
```

Mở `reports/eval_v2.json`, đọc `missing_keywords` của các ca sai (xem `scaling-03` và `security-02`). Bổ sung `KNOWLEDGE_BASE` trong `develop/utils/mock_llm.py`, giữ nguyên golden dataset. **Restart v2** rồi chạy:

```bash
python eval/run_eval.py --url http://localhost:8002 --baseline reports/eval_v2.json \
  --min-accuracy 1.0 --out reports/eval_v2_fixed.json
```

**Qua mốc khi** v2 fixed đạt accuracy 100% và 0 regression. So sánh accuracy, token, tổng cost, cost/câu đúng. Theo Exercise 7.3, viết job CI hoặc mô tả cách job khởi động v2 với lỗi mô phỏng bằng 0, chờ HTTP sẵn sàng, chạy eval với `--min-accuracy 0.85` và để exit code quyết định trạng thái job. Xem mẫu trong [CODE_LAB.md](CODE_LAB.md). Điền phần local của report khi các kết quả còn mới, rồi dừng v1/v2.

## CP8 · Observability stack và nộp (Part 7 Bước 2)

### 7.4 · Lên stack, tạo tải, xem dashboard

```bash
cd "$REPO/06-lab-complete/benchmark-observability/production"
cp -n .env.example .env
docker compose -p k5-day14-observability up -d --build
docker compose -p k5-day14-observability ps
curl -i http://localhost:8080/ask -H 'X-API-Key: day14-lab-key' \
  -H 'Content-Type: application/json' -d '{"question":"Trong distributed tracing, span là gì?"}'
curl -i http://localhost:8080/metrics
```

Nếu đã đổi key trong `.env`, dùng key local đó. Kỳ vọng `/ask` 200 với `X-Trace-ID` và `X-Served-By`, `/metrics` qua Nginx 404. Mở [Prometheus](http://localhost:9090), xem Target health có agent UP. Mở [Locust](http://localhost:8089), đặt 30 users, ramp-up 5/s, host `http://nginx` nếu được hỏi. Mở [Grafana](http://localhost:3000), dashboard “Day 14 — AI Agent Overview”, chụp `screenshots/grafana-dashboard.png` khi có tải. Ghi traffic, error rate, latency và in-flight.

### 7.5–7.6 · Tìm trace và làm alert firing

1. Mở [Jaeger](http://localhost:16686), chọn `observable-agent`, Find Traces, sắp theo Longest First. Mở trace chậm, xác định span tốn nhiều thời gian nhất và chụp `jaeger-slow-trace.png`.
2. Trong `.env` của **stack local**, đặt `MOCK_ERROR_RATE=0.2`. Chạy `docker compose -p k5-day14-observability up -d` và giữ Locust chạy. Mở [Prometheus Alerts](http://localhost:9090/alerts), ghi giờ thay đổi và giờ `AgentHighErrorRate` chuyển firing (ngưỡng >5% trong 1 phút). Tìm `error=true` trong Jaeger hoặc lấy ID từ `docker compose -p k5-day14-observability logs agent | rg llm_error`, mở trace và chụp `jaeger-error-trace.png`.
3. Khôi phục error rate baseline, đặt `MOCK_SLOW_RATE=0.3`, chạy lại Compose. Quan sát p95 >1 giây trong 2 phút cho `AgentHighLatencyP95`. Để chụp cả hai alert cùng firing theo CHECKPOINTS.md, đặt đồng thời `MOCK_ERROR_RATE=0.2` và `MOCK_SLOW_RATE=0.3`, chạy lại Compose và giữ tải cho đến khi cả hai firing. Chụp `screenshots/prometheus-alert-firing.png`, rồi khôi phục baseline.
4. Thử các biến thể còn lại trong template: `LLM_MODEL=mock-llm-large` để xem tốc độ chi phí, `AGENT_VERSION=v1` để xem retrieval/version, và pause một instance bằng `docker pause TÊN_CONTAINER` (lấy tên từ `docker compose -p k5-day14-observability ps`) để quan sát `AgentInstanceDown`. Chạy `docker unpause TÊN_CONTAINER` ngay sau khi xong. Ghi thời gian thực tế cho mỗi alert firing và tín hiệu quan sát được của từng thí nghiệm. Trả từng biến về baseline trước thí nghiệm kế tiếp.

```bash
docker compose -p k5-day14-observability run --rm --no-deps \
  -v "$PWD/prometheus:/p:ro" --entrypoint promtool prometheus test rules /p/alert_rules_test.yml
```

Nếu alert còn pending, giữ tải và kiểm lại ngưỡng, thời gian `for` và Target health. Đối chiếu trace ID với log và dán dòng JSON có cùng `trace_id` vào phần debug của report.

### 7.7 · Đo scale 1 so với 3 replica

Dừng bài chạy ở Locust Web UI. Khôi phục cùng một cấu hình baseline cho cả hai lần đo. Sau mỗi lệnh scale, đợi Prometheus và Nginx nhận số replica mới (~15 giây hoặc đến khi Targets hiển thị đúng).

```bash
docker compose -p k5-day14-observability up -d --scale agent=1
# Đợi 1 agent UP rồi chạy
docker compose -p k5-day14-observability run --rm locust -f /mnt/locust/locustfile.py --host http://nginx \
  --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_1

docker compose -p k5-day14-observability up -d --scale agent=3
# Đợi 3 agent UP rồi chạy
docker compose -p k5-day14-observability run --rm locust -f /mnt/locust/locustfile.py --host http://nginx \
  --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_3
```

Nếu Locust trả 1 vì có request lỗi, đọc CSV và ghi cả error rate. Lấy số từ dòng Aggregated ở mỗi file `_stats.csv`. So sánh RPS, p95 và error rate; đối chiếu panel LLM latency để giải thích. Khi đã lưu bằng chứng, chạy `docker compose -p k5-day14-observability down -v`.

### Kiểm tra trước khi nộp

```bash
cd "$REPO"
mkdir -p reports benchmark-results
cp 06-lab-complete/benchmark-observability/develop/reports/*.json reports/
cp 06-lab-complete/benchmark-observability/production/benchmark-results/scale_{1,3}_*.csv benchmark-results/
ls reports benchmark-results screenshots
git status --short
git log --all --oneline -- '*.env' '.env' '.env.local'
```

- [ ] `MISSION_ANSWERS.md` có Part 1–5, output PASS 12/12 và AI log.
- [ ] `DEPLOYMENT.md` có URL public và bốn lệnh kiểm tra. `screenshots/` có ba ảnh deploy và ít nhất bốn ảnh observability đã nêu.
- [ ] `BENCHMARK_REPORT.md` điền đủ các mục, có 4 JSON concurrency, 3 JSON tail latency, 3 JSON eval, CSV scale 1/3. Số trong report khớp JSON/CSV và có bằng chứng ít nhất hai alert firing.
- [ ] Code Part 6 ở `06-lab-complete/`; `git diff` không có thay đổi ngoài bài làm, secret, file `.env` hay dữ liệu cá nhân ngoài mục đề yêu cầu.
- [ ] Stage các tệp bài làm, xem `git diff --cached`, commit và push lên bản fork. Mở repo ở cửa sổ ẩn danh, thử URL deploy và nộp **một link repo** trên LMS.

Nếu kẹt, dùng [TROUBLESHOOTING.md](TROUBLESHOOTING.md) và đối chiếu [RUBRIC.md](RUBRIC.md) trước khi nộp.
