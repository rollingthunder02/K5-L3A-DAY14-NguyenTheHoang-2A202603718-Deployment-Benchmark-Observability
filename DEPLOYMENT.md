# Day 14 — Triển khai agent

## Trạng thái

Render báo **Deploy succeeded · Live** cho commit `be98ae7` trên nhánh `codex/cp6-render`. Hai tài nguyên được tạo từ cùng một Blueprint.

- URL public: [k5-day14-hoang-agent.onrender.com](https://k5-day14-hoang-agent.onrender.com)
- [Blueprint sync](https://dashboard.render.com/blueprint/exs-dc3a3t7lot8c739ioukg/sync/exe-dc3a3tflot8c739iovig)
- [Kết quả deploy trên Render](https://dashboard.render.com/web/srv-dc3a43cipgvc73834gg0/deploys/dep-dc3a43kipgvc73834hdg)

## Nền tảng và cấu hình

- Nền tảng: Render. Blueprint `06-lab-complete/render.yaml` chọn nhánh `codex/cp6-render`, build Docker trong `06-lab-complete/` và cấu hình `/health`.
- Render Key Value tương thích Redis và chỉ nhận kết nối nội bộ. Blueprint gán `REDIS_URL` qua `fromService.connectionString`.
- Render sinh `AGENT_API_KEY` và cấp `PORT`. Blueprint đặt `ENVIRONMENT=production`. Agent dùng hạn mức mặc định nếu không ghi đè.

Render dùng vùng `singapore` và gói Free cho web service và Key Value. [Tài liệu Render Blueprints](https://render.com/docs/infrastructure-as-code)

## Kiểm tra sau triển khai

Nhập key bằng prompt ẩn. Các lệnh chỉ in mã HTTP.

```bash
BASE='https://k5-day14-hoang-agent.onrender.com'
read -rsp 'API key: ' KEY; echo
curl -sS --max-time 20 -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS --max-time 20 -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS --max-time 20 -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS --max-time 20 -o /dev/null -w '%{http_code}\n' "$BASE/ask" \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
unset KEY
```

| Kiểm tra | Kết quả thực tế |
| --- | --- |
| `GET /health` | `200`, `{"status":"ok"}` |
| `GET /ready` | `200`, `{"status":"ready"}` |
| `POST /ask` thiếu key | `401`, `{"detail":"Missing or invalid API key"}` |
| `POST /ask` có key | `200` với JSON `{"question":"Hello"}` gửi lên agent. |

## Ảnh minh chứng

- [Dashboard · Blueprint tạo web service và Key Value](screenshots/dashboard.png)
- [Web service · Deploy succeeded và Live](screenshots/running.png)
- [Kiểm tra HTTP public · 200, 200, 401, 200](screenshots/test.png)
