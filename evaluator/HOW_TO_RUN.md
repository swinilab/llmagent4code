# Chạy đánh giá một ứng dụng được sinh ra

## Cách nhanh nhất

Mở PowerShell tại thư mục gốc của repo (`F:\swelab\llmagent4code`):

```powershell
# Chạy thử 1 lần cho mỗi kịch bản (~10 phút) — dùng để kiểm tra pipeline
.\evaluator\run_app.ps1 -App claude-gen\app-claude -Runs 1

# Chạy đầy đủ theo giao thức: 5 lần cho mỗi kịch bản (~40-60 phút)
.\evaluator\run_app.ps1 -App claude-gen\app-claude -Runs 5
```

Script tự động kiểm tra môi trường trước khi chạy, tự tạo file override cần
thiết, rồi gọi evaluator. Kết quả nằm ở `evaluation-results\<app-id>\`.

## Yêu cầu trước khi chạy

**Docker Desktop phải đang chạy.** Đây là điều kiện quan trọng nhất — xem phần
"Docker chết giữa chừng" bên dưới.

**Môi trường Python của evaluator.** Nếu chưa có, tạo một lần duy nhất:

```powershell
uv venv evaluator\.venv-eval
uv pip install --python evaluator\.venv-eval\Scripts\python.exe httpx pyyaml "psycopg[binary]"
```

Lưu ý: không dùng `uv sync` cho việc này. Lệnh đó cài toàn bộ dependency của cả
dự án (bao gồm `mini-swe-agent` → `datasets` → `pyarrow`) và hiện đang thất bại
vì hết dung lượng ổ đĩa. Evaluator chỉ cần ba gói ở trên.

## Ba thứ script tự xử lý

Cả ba đều đã từng làm hỏng một lần chạy, nên script kiểm tra trước:

**1. Cổng bị chiếm.** Nếu còn stack cũ đang chạy từ lần trước, nó giữ cổng 8080
và evaluator sẽ chấm điểm container mà nó không hề khởi động — kết quả trông
hợp lệ nhưng không phải của deployment sạch. Script tự động `docker compose down -v`
các stack đánh giá còn sót.

**2. Cổng database.** Ba kịch bản (ASR-A2, ASR-A4, ASR-P1) đọc bằng chứng quyết
định trực tiếp từ PostgreSQL, không qua API — vì hỏi ứng dụng "anh đã rollback
chưa" thì cache có thể trả lời thay database. Việc đó cần một cổng host, nhưng
đặc tả không bắt buộc ứng dụng publish nó (nên ứng dụng **không sai** khi thiếu).
Script tự ghi `docker-compose.override.yml` chỉ để publish cổng này. Compose tự
động merge file đó, nên `docker-compose.yml` của ứng dụng không bị sửa, và bên
trong network mọi thứ giữ nguyên: ứng dụng vẫn chỉ đi qua `toxiproxy:8666`.

**3. Cổng 5432 đã có PostgreSQL khác.** Máy này đang chạy sẵn một PostgreSQL cục
bộ trên 5432. Nên override dùng **15432**. Nếu để 5432, trường hợp tốt là bind
thất bại; trường hợp xấu hơn là evaluator đọc nhầm database và kiểm tra các
assertion rollback trên những hàng mà ứng dụng chưa từng ghi.

Muốn đổi cổng: `-DbPort 25432` (nhớ xoá file override cũ để script ghi lại).

## Đọc kết quả

Mỗi lần chạy sinh ra hai file trong `evaluation-results\<app-id>\`:

| File | Nội dung |
|---|---|
| `<app-id>.json` | Báo cáo: verdict từng gate, từng kịch bản, từng assertion |
| `<app-id>.trace.jsonl` | Nhật ký: **mọi** request/response, fault, phép đo |

Trong lúc chạy, console tường thuật trực tiếp:

```
=== ASR-A3 -- graceful degradation (run 1/5) ===
  - seed: two products (one to be warmed) and a customer
  * db proxy postgres: OFF (outage)
  - unwarmed read: expect [503] / SERVICE_UNAVAILABLE
    unwarmed read: 503 [SERVICE_UNAVAILABLE] (expected [503]) in 42ms  body={...}
  - warmed reads: 600 reads; expect >= 99% success
    warmed reads: n=600 statuses={200: 600} success=100.0% p95=5ms
  * db proxy postgres: ON (reachable)
    warmed reads stay available: ok (expected >= 99%, got 100.0%)
    writes fail safely: FAIL (expected 5, got 3)
```

Xem lại trace log của một kịch bản cụ thể:

```powershell
$py = ".\evaluator\.venv-eval\Scripts\python.exe"
& $py -c @"
import json
for l in open(r'evaluation-results\app-claude\app-claude.trace.jsonl', encoding='utf-8'):
    d = json.loads(l)
    if d.get('scenario') == 'ASR-A3' and d['kind'] == 'http':
        print(d.get('step'), d['method'], d['url'], '->', d['status'], f"{d['elapsed_ms']}ms")
"@
```

Các cờ hữu ích:

- `-KeepRunning` — để container chạy tiếp sau khi xong, tiện khi cần khám nghiệm
  một failure bằng tay.
- `--verbose-requests` (truyền thẳng cho `evaluator.run`) — in từng request ra
  console. Rất ồn dưới tải: một lần chạy sinh ~1.800 request.

## Docker chết giữa chừng

Đây là lỗi đã xảy ra trong lần chạy vừa rồi và **cần biết để không đọc nhầm kết quả**:

```
error: [WinError 1450] Insufficient system resources exist to complete the requested service
unable to get image 'curlimages/curl:8.11.1': ... open //./pipe/dockerDesktopLinuxEngine:
The system cannot find the file specified
```

Khi Docker Desktop hết tài nguyên và sập, evaluator ghi nhận kịch bản đó là
`FAIL` — nhưng đó là lỗi hạ tầng, **không phải khuyết điểm của ứng dụng**. Dấu
hiệu nhận biết: `WinError 1450`, hoặc `dockerDesktopLinuxEngine` không tìm thấy,
hoặc "stack did not come back".

Cách xử lý: khởi động lại Docker Desktop, tăng bộ nhớ cho nó trong Settings →
Resources, đóng bớt ứng dụng nặng, rồi chạy lại **chỉ những kịch bản bị ảnh
hưởng** — đừng gộp kết quả của hai lần chạy khác điều kiện vào một bảng.

Ổ đĩa gần đầy cũng là nguyên nhân trực tiếp (`uv sync` đã thất bại vì lý do này).
Dọn chỗ trước khi chạy bản đầy đủ 5 lần:

```powershell
docker system df          # xem Docker đang chiếm bao nhiêu
docker system prune -a    # dọn image/container không dùng — kiểm tra kỹ trước khi chạy
```

## Chạy thủ công (khi cần kiểm soát từng tham số)

```powershell
.\evaluator\.venv-eval\Scripts\python.exe -m evaluator.run `
    --app claude-gen\app-claude `
    --app-id app-claude `
    --runs 5 `
    --base-url http://localhost:8080 `
    --dsn "postgresql://orderman:orderman@localhost:15432/orderman" `
    --toxiproxy-port 8474 `
    --output evaluation-results\app-claude
```

Nhớ tự kiểm tra ba điều kiện ở phần trên trước khi chạy cách này.
