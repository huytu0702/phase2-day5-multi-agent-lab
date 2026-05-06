# Design Template (Final Implementation)

## 1) Student Information

- **Họ và tên:** Nguyễn Huy Tú  
- **MSV:** 2A202600170  
- **Môn/Lab:** Multi-Agent Research Lab  
- **Repository:** `phase2-day5-multi-agent-lab`

---

## 2) Problem Definition

Xây dựng một hệ thống research assistant có thể chạy thực tế trong môi trường production-oriented, giải quyết bài toán:

1. Nhận query người dùng.
2. Thu thập nguồn thông tin thực tế.
3. Phân tích, tổng hợp và viết câu trả lời cuối.
4. Có đánh giá chất lượng trước khi kết thúc.
5. Có khả năng quan sát (observability) để debug từng bước.

### Success criteria

- Workflow chạy end-to-end bằng LangGraph.
- Output có citation và limitations.
- Có judge score (`score`, `passed`, `rationale`).
- Có trace local + trace cloud (Langfuse) để theo dõi từng node.

---

## 3) Why Multi-Agent Instead of Single-Agent

### Hạn chế của single-agent baseline

- Khó tách lỗi theo pha (search/analysis/writing).
- Khó giải thích vì sao output tốt/xấu.
- Khó áp guardrail routing theo trạng thái.

### Lý do chọn multi-agent

- Tách nhiệm vụ theo vai trò rõ ràng.
- Dễ đo và debug từng bước qua trace.
- Supervisor kiểm soát route + điều kiện dừng.
- Dễ mở rộng thêm quality gate (judge/rewrite policy).

---

## 4) Implemented Agent Roles

| Agent | Responsibility | Input chính | Output chính | Failure mode đã xử lý |
|---|---|---|---|---|
| Supervisor | Quyết định node tiếp theo | `iteration`, `route_history`, `sources`, `analysis_notes`, `final_answer`, `judge_score` | route + stop_reason | chặn vòng lặp bằng `max_iterations` |
| Researcher | Lấy nguồn thật và ghi research notes | `query`, `max_sources` | `sources`, `research_notes` | nguồn yếu/rỗng vẫn giữ flow an toàn |
| Analyst | Chuyển research thành claims/risks/recommendations | `research_notes`, `sources` | `analysis_notes` | normalize heading để ổn định test |
| Writer | Tạo final answer có citation + limitations | `query`, `analysis_notes`, `sources` | `final_answer` | thêm hậu xử lý bắt buộc `Citations`, `Limitations` |
| Judge (Critic) | Chấm pass/fail + rationale | `final_answer`, `sources` | `judge_score`, metadata judge | parse structured output robust hơn |

---

## 5) Shared State Design (Implemented)

Các trường đã dùng trong `ResearchState`:

- Core request/runtime: `request`, `iteration`, `max_iterations`
- Routing lifecycle: `route_history`, `stop_reason`
- Content pipeline: `sources`, `research_notes`, `analysis_notes`, `final_answer`
- Quality loop: `judge_score`, `rewrite_count`, `rewrite_limit`
- Observability & diagnostics: `agent_results`, `trace`, `token_usage`, `errors`

### Điểm tối ưu state

- State đủ để supervisor route deterministic.
- Mỗi agent ghi `AgentResult` riêng để audit output node-level.
- `trace` + `route_history` cho phép đối chiếu CLI output với Langfuse observations.

---

## 6) Routing Policy (Implemented)

Graph logic:

`START -> supervisor -> (researcher | analyst | writer | judge | END)`

Quy tắc:
1. Nếu `iteration >= max_iterations` -> `END` (`max_iterations`).
2. Nếu thiếu `sources` hoặc `research_notes` -> `researcher`.
3. Nếu thiếu `analysis_notes` -> `analyst`.
4. Nếu thiếu `final_answer` -> `writer`.
5. Nếu có final answer nhưng chưa judge -> `judge`.
6. Nếu judge pass -> `END` (`completed`).
7. Nếu judge fail và còn rewrite budget -> quay lại `writer`.
8. Nếu judge fail và hết rewrite budget -> `END` (`validation_failed_with_limit`).

Luồng thực tế đã xác minh nhiều lần:
`researcher -> analyst -> writer -> judge -> end`.

---

## 7) Guardrails (Implemented)

- **Max iterations:** `MAX_ITERATIONS` trong config/state.
- **Timeout:** `OPENAI_TIMEOUT_SECONDS`, `TIMEOUT_SECONDS`.
- **Retry:** `OPENAI_MAX_RETRIES` cho LLM client.
- **Validation:** structured output parser cho judge + hậu xử lý format output.
- **Safe stop:** stop reason rõ ràng trong state.
- **Tracing fallback:** luôn có local JSONL, Langfuse là optional theo env.

---

## 8) Observability and Tracing

### Local tracing
- Mỗi span được ghi vào `traces/local_trace.jsonl`.

### Langfuse v4
- Dùng adapter với cấu hình từ settings (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST/BASE_URL`, `LANGFUSE_V4_ENABLED`).
- Đã xác minh bằng CLI `lf`:
  - thấy trace id mới,
  - thấy observations cho từng workflow node cùng trace id.

### Lệnh kiểm tra
```bash
.venv/Scripts/lf.exe --host https://cloud.langfuse.com traces list --limit 10
.venv/Scripts/lf.exe --host https://cloud.langfuse.com observations list --trace-id <TRACE_ID> --limit 50
```

---

## 9) Optimizations and Improvements Completed

Tổng hợp từ `docs/production_implementation_plan.md` + session triển khai:

1. Tích hợp LLM thật vào Analyst/Writer/Judge thay cho placeholder.
2. Thêm `OPENAI_BASE_URL` để chạy qua OpenAI-compatible local gateway.
3. Cải thiện parser structured output (extract JSON từ code-fence/bao quanh text).
4. Chuẩn hóa output để giảm flaky do variation của model:
   - `Analysis Notes`
   - `Claims:`
   - `Citations:`
   - `Limitations:`
5. Đồng bộ tracer với settings app, tránh lệch config env.
6. Khắc phục và xác minh lỗi “không thấy trace trên Langfuse” bằng CLI (`lf`).
7. Re-run test liên tục sau từng thay đổi quan trọng để giữ stability.

---

## 10) Validation Evidence

- Multi-agent run thực tế: thành công, có `judge_score.passed = true`.
- Route history đúng pipeline mong đợi.
- `pytest -q`: pass sau khi hoàn tất fixes.
- Langfuse observations hiển thị node-level events theo trace id.

---

## 11) Final Conclusion

Bản triển khai hiện tại đã đạt mục tiêu production-oriented cho lab:
- chạy được end-to-end,
- có role separation,
- có quality gate,
- có observability đủ để debug và peer review,
- phản ánh đúng các hạng mục trong production plan và toàn bộ phần việc đã thực hiện trong session.