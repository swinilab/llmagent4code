# Open profile — đánh giá cho `prompts/latest.md`

## Khác gì với profile prescriptive

`prompts/generate.md` cố định mọi thứ: sáu tactic, ngưỡng số, interface quan
sát, test hook. Evaluator tự inject fault rồi so số đo với `thresholds.yaml`.

`prompts/latest.md` chỉ đưa định nghĩa tactic từ Bass/Clements/Kazman. Agent tự
chọn cơ chế, tự chọn ngưỡng, tự viết verification. Evaluator **không thể** chấm
bằng ngưỡng nó chưa từng nêu — nên nó chuyển sang kiểm tra bằng chứng mà agent
được yêu cầu phải tạo ra.

Hệ quả cho việc diễn giải kết quả:

| | prescriptive PASS | open PASS |
|---|---|---|
| Khẳng định được | cơ chế hành xử đúng đặc tả dưới fault do evaluator inject | agent đã xây cơ chế, tự kiểm chứng đáng tin, và bằng chứng của nó chịu được audit độc lập |
| Về hành vi | mạnh | yếu hơn |
| Về năng lực thiết kế | yếu hơn | mạnh |

Đừng gộp hai con số này vào một bảng.

## Các gate

**G0 — chạy được.** Dùng lại `gates/g0_artifact.py`: build, start, manifest
tồn tại. Fail thì dừng.

**G1 — functional.** Sinh probe cơ học từ `domain.yaml` qua `common/bva.py`;
các case cần diễn giải nằm ở `cases_interpretive.py`.

**G2 — traceability.** `g2_traceability.py`. Khác bản prescriptive ở chỗ tactic
không so khớp verbatim mà so theo **taxonomy**: leaf phải có thật trong cây
Availability/Performance, và nếu citation có nêu context thì context phải đúng.
`Timeout` được chấp nhận, `Detect Faults / Timeout` cũng vậy, nhưng
`Performance > Detect Faults > Timeout` bị từ chối vì đặt sai quality
attribute, và `Degradation` bị từ chối vì không phải tên tactic.

Ngoài ra G2 kiểm `librariesUsed` có xuất hiện trong **thân hàm được khai** —
bắt được trường hợp entry trỏ vào request handler thay vì hàm thật sự gọi vào
cơ chế.

**G3 — self-verification audit.** Phần mới hoàn toàn. Đọc
`verification/results/*.json` và kiểm năm điều, xếp theo mức độ dễ qua mặt:

1. `passed` được **tính lại** từ `observed` vs `threshold`, không tin giá trị khai
2. mọi metric trong `threshold` phải có trong `observed`
3. `faultInduced.verified` phải `true` — fault được xác nhận từ ngoài app
4. `baseline` phải khác `observed` — chứng tỏ fault thật sự chạm tới hệ thống
5. suite phải fail khi cơ chế bị gỡ (xem `falsifiability.py`)

Điểm 4 là thứ bắt được ca mà điểm 3 không bắt được: proxy tắt đúng, nhưng ứng
dụng vẫn tới được database bằng đường khác.

## Đổi sang domain khác

Sửa **duy nhất** `domain.yaml` và `cases_interpretive.py`:

```yaml
domain: hospital-admissions
entities: [patient, ward, admission, discharge, billing]
minimum_workflow_steps: 5
constraints:
  patient:
    name: {required: true, length: [2, 100]}
    ...
```

Bảng ràng buộc phải chép từ **prompt**, không phải từ app đã sinh. Nếu hai bên
lệch nhau thì prompt đúng và file này sai — chấm agent theo ràng buộc nó chưa
từng nhận là ra một con số vô nghĩa.

`cases_interpretive.py` giữ các case mà generator không suy ra được: `\p{L}`
nghĩa là chữ Unicode, `GBP` hợp lệ ISO nhưng ngoài allow-list, `19.9` nằm trong
khoảng nhưng sai độ chính xác. Mỗi case phải trích được về một dòng trong bảng.

Không đụng tới `common/`, `harness/`, `report/`.

## Giới hạn còn lại

Hai thứ vẫn cần người hoặc LLM-judge:

- **Ngưỡng agent chọn có hợp lý không.** Khai timeout 30s cho một DB read là
  hợp lệ về hình thức, vô lý về kỹ thuật. Không có baseline nào trong prompt để
  máy so.
- **Hàm được khai có đúng là tactic đó không.** G2 xác nhận hàm tồn tại và có
  nhắc tới library; nó không đọc được ngữ nghĩa.

Cả hai đều có điểm neo cụ thể (`nfr-trace.json` chỉ đúng hàm cần đọc), nên
judge không phải quét cả repo.
