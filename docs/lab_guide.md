# Lab Guide: Multi-Agent Research System (Final Reported Version)

## Student

- **Họ và tên:** Nguyễn Huy Tú  
- **MSV:** 2A202600170

---

## 1) Lab Objective

Nâng cấp starter skeleton thành hệ thống multi-agent chạy thực tế, có thể:
- thực thi pipeline nghiên cứu hoàn chỉnh,
- tạo câu trả lời có dẫn chứng,
- chấm chất lượng đầu ra,
- quan sát được toàn bộ vòng đời xử lý qua trace.

---

## 2) Implemented Scope

### 2.1 Runtime & Model
- Dùng `.venv` để chạy toàn bộ runtime/test.
- LLM model runtime: `gpt-5.4-mini`.
- Hỗ trợ OpenAI-compatible endpoint qua `OPENAI_BASE_URL`.

### 2.2 Workflow
- Multi-agent workflow build bằng LangGraph.
- Route deterministic qua supervisor.
- Có guardrail dừng an toàn theo state.

### 2.3 Agents
- `Researcher`: lấy nguồn và tạo research notes.
- `Analyst`: tạo phân tích có cấu trúc.
- `Writer`: sinh final answer có citation + limitations.
- `Judge/Critic`: chấm điểm và pass/fail verdict.

### 2.4 Observability
- Local trace JSONL luôn bật.
- Langfuse v4 bật theo env config.
- Xác minh trace bằng CLI `lf` (traces + observations).

---

## 3) Work Completed (from production plan + session)

### A. LLM integration improvements
1. Nối `LLMClient` vào Analyst/Writer/Judge.
2. Bổ sung retry + timeout sử dụng config thống nhất.
3. Thêm `OPENAI_BASE_URL` vào settings và client builder.

### B. Output reliability improvements
1. Robust JSON extraction cho structured judge output.
2. Hậu xử lý đảm bảo section bắt buộc trong output:
   - analysis có `Analysis Notes`, `Claims:`
   - answer có `Citations:` và `Limitations:`
3. Giảm lỗi do model trả về format không đồng nhất.

### C. Workflow quality improvements
1. Route và stop reason rõ ràng trong state.
2. Kiểm chứng route history thực tế theo đúng flow.
3. Judge loop có rewrite budget + safe termination.

### D. Langfuse troubleshooting & fix
1. Xác định đúng CLI có trong `.venv`: `lf`.
2. Khắc phục lỗi 401 khi CLI chưa có đúng auth context.
3. Đồng bộ tracer dùng settings app thay vì đọc env rời rạc.
4. Xác nhận trace xuất hiện trên cloud và kiểm tra được node-level observations.

---

## 4) Commands Used for Verification

```bash
# Run workflow thực tế
python -m multi_agent_research_lab.cli multi-agent --query "..." --json

# Run test suite
pytest -q

# Langfuse CLI
.venv/Scripts/lf.exe --help
.venv/Scripts/lf.exe --host https://cloud.langfuse.com traces list --limit 10
.venv/Scripts/lf.exe --host https://cloud.langfuse.com observations list --trace-id <TRACE_ID> --limit 50
```

---

## 5) Evidence Checklist

- [x] LLM thật chạy trong analyst/writer/judge
- [x] Workflow route đúng `researcher -> analyst -> writer -> judge -> end`
- [x] Judge trả về `score/passed/rationale`
- [x] Output có citation + limitations
- [x] Test suite pass
- [x] Trace local ghi thành công
- [x] Langfuse trace/observation kiểm tra được bằng CLI

---

## 6) Key Optimizations Summary

1. **Config-driven runtime**: giảm hardcode, tăng tính tái cấu hình.
2. **Structured-output robustness**: giảm fail do format model.
3. **Deterministic orchestration**: route chuẩn, stop rõ ràng.
4. **Observability reliability**: theo dõi được từng node và debug nhanh hơn.
5. **Regression control**: validate lại bằng test sau mỗi thay đổi trọng yếu.

---

## 7) Final Result

Triển khai đã đạt mức “lab production-ready” theo mục tiêu:
- chạy được end-to-end,
- có đánh giá chất lượng,
- có khả năng truy vết đầy đủ,
- phản ánh đúng các hạng mục đã cam kết trong production implementation plan và phần việc thực hiện trong session.