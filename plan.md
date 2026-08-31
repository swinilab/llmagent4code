
[] gen app: 
	[x] chatdev - qwen3.5 (v1)
		. latest.md
	[] chatdev (v2) @manh
	[x] claude
	[] codex @congnv


[] 2. functional test
	a. [] check domain constraint fields - validate testcases - vba/ep 
		@duc @lam
	b. use: chatdev (v1)
	[] log testcase execution: request/ response
		@manh
	[] check test log -> verify test result
		@duc @lam
	[] hiệu chỉnh functional check   
		@manh
	c. [] test generated apps @manh
		[] chatdev
		[] claude
		[] codex

[] 3. validate qa: static
	[]. ind-score: qa/ tactic @duc @hai
		. score1(tactic, function)
			. nfr-trace-> absent (0)/present (1)
			[] . check lib code template: from (doc) -- code gen: similarity score 
		. score2(tactic, function-in-trace) = % sum(score1)/num-functions
		. score3(qa, tacticset) = avg(score2-by-qa)
	[] test generated apps @duc
		[] chatdev
		[] claude
		[] codex

[] 4. validate conflicting qa -> TICS (Tactic Interaction Conflict Score)
	code: method_pipeline_v2/validators/tics/   (độc lập với StaticQualityAttributeValidator)

	. công thức (đã chỉnh so với bản nháp, theo doc "NFR trade off" mục 4-11):
		. conf-tacticset = {(x, y, w)} - 15 cặp, khoá theo NFR id, w từ ma trận doc mục 9
			. 13 cặp có w>0 (mẫu số) + 2 cặp Support w=0 (đo nhưng không chấm)
		. cùng function:  C = sqrt(S(x,f) · S(y,f))              [trung bình nhân, không phải 1/(a+b)]
		. khác function:  C = sqrt(S(x,f1) · S(y,f2)) · exp(-0.35·(d-1))   [decay mũ, không phải 1/d]
		. mỗi cặp:        C(x,y) = MAX qua mọi (f1,f2)           [không avg - avg giết signal]
		. hệ thống:       TICS = Σ w·C / Σ w  trên 13 cặp
	
	. trace(f1,f2) = đường đi ngắn nhất VÔ HƯỚNG trên code graph (2 tactic gặp nhau ở caller chung)
		[x] CALLS         - cần suy kiểu: biến cục bộ, attribute inject qua __init__, kế thừa
		[x] TXN_BOUNDARY  - call thực hiện khi transaction đang mở
		[x] SHARED_STATE  - f1 ghi self.attr, f2 đọc (loại __init__: đó là DI, không phải state)
		[] USES_CONFIG    - hoãn: codex inject config qua constructor, cần lần main.py -> self._attr
		[] USES_RESOURCE  - HOÃN CÓ CHỦ Ý: nối clique theo kiểu -> +252 cạnh / 263, riêng
		                    AsyncSession 190 cạnh -> mọi thứ về distance 2, phá metric.
		                    Chỉ làm được nếu nối theo INSTANCE cụ thể, không theo kiểu.

	[x] Phase 0: conf_tacticset.json + txn_signatures.json + 4 oracle test từ apps/codex
	[x] Phase 1: CodeGraphBuilder (PythonExtractor) - 3 oracle distance khớp tay
	[x] Phase 2: TXN_BOUNDARY + SHARED_STATE + phân loại call (external/nodeless/unresolved)
	[x] Phase 4: TICSValidator + report JSON + dump graph/bindings
	[x] Phase 5: wire pipeline --stage 5
	[x] chạy thử 8 app: 5 comparable, 3 bị gate loại (2 dùng generalized.md, 1 dùng NFR set cũ)

	. KẾT QUẢ (S=1.0 degraded - là CẬN TRÊN, S thật chỉ làm giảm):
		codex 0.768 | chatdev-v2 0.659 | chatdev-v3 0.410 | claude-latest 0.298 | chatdev-v1 0.091

	. PHÁT HIỆN QUAN TRỌNG - TICS = breadth × intensity (đẳng thức, khớp 3 chữ số cả 5 app):
		. breadth   = Σ_found w / Σ_all w   - implement được bao nhiêu cặp   -> 0.11..1.00
		. intensity = Σ_found w·C / Σ_found w - đặt sát nhau tới mức nào     -> 0.60..0.90
		. r(TICS, breadth) = +0.96 ; r(TICS, intensity) = +0.14
		=> TICS gộp 1 số CHỦ YẾU đo lại độ phủ NFR (mục 3 đã đo rồi).
		   intensity mới là phần thông tin riêng của TICS.
		[] QUYẾT ĐỊNH CẦN CHỐT: báo cáo cặp (breadth, intensity) thay vì 1 số TICS?

	[] chốt trọng số cặp NFR 2.1 x 2.2 (doc mâu thuẫn: ma trận "Support/Low" vs văn xuôi "thấp-TB")
	   . đang để 0.25 -> mẫu số 13. Nếu 0.0 -> mẫu số 12, mọi số phải tính lại.
	[] giảm 124 call chưa resolve (codex) - có thể làm vài distance dài hơn thực tế
	[] thay TraceOnlyBindingProvider bằng S(x,f) thật của mục 3 @duc @hai
	   . contract: validators/tics/contract.py :: ITacticBindingProvider
	   . khoá join = nfr_id + function_ref dạng "path.py::Class.method"
	   . S=0 cho claim không verify được, VẪN phải liệt kê (đừng lọc bỏ)

	> output table: - validate using static qa					
	
	- mutliple copy of data (cache) <-> exception detection 	
	- ..

[] writing: 
	[] pipeline: 
