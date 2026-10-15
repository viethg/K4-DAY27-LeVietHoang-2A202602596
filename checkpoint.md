Exercise 1 — Định tuyến theo confidence
Bạn mở exercises/exercise_1_confidence.py và dựng graph đầu tiên: lấy PR, cho LLM phân tích, rồi rẽ vào một trong ba node cuối theo confidence. Ở bài này chưa có HITL; ba node cuối chỉ in ra nhánh nào được chọn.

Câu hỏi bài này trả lời
Mọi thứ phía sau đều dựa vào một quyết định: PR này có cần người hay không. Nếu bước phân loại sai, các bài sau dù viết đúng cũng sẽ chạy nhầm nhánh. Vì vậy trước khi nghĩ đến chuyện dừng lại hay hỏi người, bạn cần một graph rẽ nhánh ổn định, và cần thấy tận mắt hai PR mẫu đi vào hai nhánh khác nhau.

Hai PR mẫu nằm ở repo public <https://github.com/VinUni-AI20k/PR-Demo>:

PR	Nội dung	Nhánh mong đợi
#1	Add task priority field — khoảng 40 dòng, một câu hỏi mở về migration schema	human_approval (~65%)
#2	Add user login + cloud sync — hash mật khẩu bằng MD5, lưu token dạng plaintext, SQL injection trong Storage.add, user_id hard-code, không có test	escalate (<58%)
Confidence và ba ngưỡng
Confidence ở đây là số từ 0 đến 1 mà LLM tự báo cáo về độ chắc chắn rằng review của nó đầy đủ và đúng. Nó không phải xác suất đã được hiệu chỉnh; đó là lý do bonus challenge 2 yêu cầu bạn kiểm tra xem model tự tin quá mức hay chưa đủ. Model trả về confidence qua trường confidence của PRAnalysis, kèm confidence_reasoning giải thích vì sao chọn con số đó.

Ngưỡng nằm trong common/schemas.py:

AUTO_APPROVE_THRESHOLD = 0.73   # >= 73% → no human, agent commits the comment directly
ESCALATE_THRESHOLD = 0.58       # < 58% → escalate: agent asks the reviewer specific questions
Chép
Từ 0.73 trở lên đi auto_approve, dưới 0.58 đi escalate, còn lại đi human_approval.

Tin số trong schemas.py
Comment TODO trong exercise_1_confidence.py còn ghi ngưỡng cũ (0.85 và 0.60), docstring Exercise 3 ghi "< 60%". Hãy luôn import và dùng AUTO_APPROVE_THRESHOLD, ESCALATE_THRESHOLD thay vì gõ số trực tiếp.

Vì sao dùng structured output
node_analyze phải gọi LLM qua get_llm().with_structured_output(PRAnalysis). Thay vì nhận một đoạn văn tự do rồi tự bóc tách, bạn nhận về một object Pydantic có sẵn summary, risk_factors, comments, confidence, confidence_reasoning và escalation_questions. Nhờ vậy node_route chỉ cần đọc state["analysis"].confidence, và các bài sau đưa thẳng các trường này vào payload cho người duyệt. Đây là contract mà toàn bộ Lab dựa vào, nên hãy giữ nguyên PRAnalysis; thư mục common/ được cung cấp sẵn và không cần sửa.

Làm bài
1. Trong node_analyze, tạo llm có structured output như trên. Gọi llm.invoke(...) với một message system (vai senior reviewer) và một message user chứa state['pr_title'] và state['pr_diff']. Bọc lời gọi trong console.status(...) như comment gợi ý, rồi trả về {"analysis": analysis}.
2. Trong node_route, đọc confidence, so với hai ngưỡng, trả về {"decision": ...} với một trong ba giá trị auto_approve, human_approval, escalate. Node chỉ trả quyết định; việc rẽ nhánh là của graph.
3. Trong build_graph, thêm 6 node, nối START → fetch_pr → analyze → route, dùng add_conditional_edges trên "route" với mapping cho cả ba nhánh, rồi nối mỗi node cuối tới END.
4. Chạy cả hai PR:
uv run python exercises/exercise_1_confidence.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
uv run python exercises/exercise_1_confidence.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/2
Chép
Nếu kẹt ở bước 3, hãy xem cách Exercise 2 nối graph: hàm điều kiện chỉ đọc lại giá trị route đã ghi vào state.

Checkpoint
Bài đạt khi hai PR in ra hai nhánh khác nhau. Với PR #1 bạn thấy dòng ✓ HUMAN APPROVAL, phần Final in action = pending_human_approval. Với PR #2 bạn thấy ✓ ESCALATE và action = pending_escalation. Dòng confidence = ... cho bạn biết model đặt PR ở đâu so với ngưỡng.

LLM không cho kết quả giống hệt mỗi lần chạy. Nếu PR #2 cứ bị chấm quá cao và không vào escalate, README cho phép tạm nâng ESCALATE_THRESHOLD lên 0.70 để ép nhánh. Khi đã thấy nhánh human_approval hoạt động, bạn sẵn sàng biến placeholder của nó thành một điểm dừng thật ở Exercise 2.
------
Exercise 2 — Dừng chờ người duyệt bằng `interrupt()`
Ở Exercise 1, human_approval chỉ in ra một dòng rồi kết thúc. Trong exercises/exercise_2_hitl.py, bạn biến nó thành một điểm dừng thật: graph đứng lại, cho người xem diff và lý do của LLM, chờ họ chọn approve, reject hoặc edit, rồi mới đi tiếp.

Bản chất của một lần "dừng"
Một chương trình bình thường muốn hỏi người thì gọi input() và chặn tại chỗ. Cách này không hợp với agent chạy lâu: người duyệt có thể trả lời sau vài phút hoặc vài giờ, tiến trình có thể bị tắt giữa chừng, và Exercise 5 còn phải trả lời qua trình duyệt chứ không qua terminal. LangGraph giải quyết bằng cách lưu trạng thái graph lại rồi trả quyền điều khiển cho bên gọi. Bên gọi hỏi người theo cách nào cũng được, sau đó đưa câu trả lời vào để graph chạy tiếp từ đúng chỗ đã dừng.

interrupt(), Command(resume=...), checkpointer và thread_id
interrupt(payload): gọi bên trong node. Graph dừng, và payload xuất hiện trong kết quả trả về dưới khoá "__interrupt__". Khi graph chạy tiếp, chính lời gọi interrupt() đó trả về giá trị người dùng gửi vào.
Command(resume=giá_trị): thứ bạn truyền vào app.invoke(...) để tiếp tục graph đang dừng.
Checkpointer: nơi lưu trạng thái giữa hai lần invoke. Không có checkpointer thì không có gì để tiếp tục; README ghi rõ quên checkpointer=... sẽ làm interrupt() ném GraphInterrupt thay vì dừng. Bài này dùng MemorySaver, chỉ lưu trong bộ nhớ.
thread_id: định danh của một phiên. Lần invoke đầu và mọi lần resume phải dùng cùng cfg = {"configurable": {"thread_id": ...}}, nếu không graph sẽ chạy lại từ đầu.
Một chi tiết dễ gây lỗi: node chạy lại từ đầu
Khi resume, node chứa interrupt() được chạy lại từ dòng đầu tiên, chỉ khác là lần này interrupt() trả về câu trả lời thay vì dừng. Vì thế mọi side-effect đặt trước interrupt() trong cùng node sẽ chạy hai lần. Đây là lý do khung bài tách việc đăng comment sang node commit riêng: node_human_approval chỉ hỏi và ghi lựa chọn vào state, còn node_commit đăng comment khi human_choice == "approve". Hãy giữ cách tách này, đừng gọi post_review_comment trong node có interrupt().

Cũng để ý rằng ở bài này, node_commit chỉ đăng khi bạn chọn approve; reject và edit đều đi vào nhánh bỏ qua và trả rejected. Việc dùng feedback để LLM viết lại review là bonus challenge 4.

Làm bài
1. Trong node_human_approval, gọi interrupt(...) với payload có đủ các khoá mà comment TODO liệt kê: kind là "approval_request", confidence, confidence_reasoning, summary, comments (danh sách c.model_dump()) và diff_preview (2000 ký tự đầu của diff). prompt_human() đọc đúng các khoá này để vẽ panel, nên thiếu khoá nào sẽ lỗi ngay khi hiển thị. Trả về human_choice và human_feedback từ câu trả lời.
2. Trong build_graph, compile với checkpointer=MemorySaver().
3. Trong main(), viết vòng lặp resume: lấy payload, đưa cho prompt_human(), rồi invoke lại với Command(resume=...) và cùng cfg. Dùng while chứ không dùng if, vì sau một lần resume graph có thể dừng thêm lần nữa.
1. Chạy với PR #1:
uv run python exercises/exercise_2_hitl.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
Chép
Approve là đăng comment thật
Chọn approve sẽ đăng một comment công khai lên PR #1 của VinUni-AI20k/PR-Demo dưới username của bạn. Hãy kiểm tra nội dung trong panel trước khi gõ approve.

Checkpoint
Terminal dừng lại với một panel viền xanh tên Approval request, hiện confidence, lý do, summary, danh sách comment đề xuất và phần diff preview, rồi hỏi Choice (approve/reject/edit)?. Gõ approve: bạn thấy dòng ✓ posted comment to ... và phần Done in committed. Mở PR #1 trên GitHub, comment ### Automated review (confidence ...) xuất hiện dưới tên bạn. Thử chạy lại và chọn reject: terminal in skipping comment và kết quả là rejected, không có comment mới.

Nhánh approve chỉ phù hợp khi LLM đã gần chắc chắn. Với PR như #2, hỏi "duyệt hay không" là chưa đủ; Exercise 3 xử lý trường hợp đó.
-----
Exercise 3 — Escalation: hỏi reviewer câu hỏi cụ thể
Khi confidence thấp, agent không nên đưa người duyệt một lựa chọn approve/reject. Trong exercises/exercise_3_escalation.py, agent hỏi những câu hỏi cụ thể để lấy thêm ngữ cảnh, rồi phân tích lại với câu trả lời đó.

Vì sao không chỉ hỏi "duyệt hay không"
Confidence thấp nghĩa là LLM thiếu thông tin để đánh giá, chứ chưa chắc PR sai. Ví dụ README nêu: "Why MD5? Is SYNC_URL meant to be HTTPS in production?". Đó là những điều chỉ tác giả hoặc người hiểu hệ thống mới trả lời được. Nếu chỉ hỏi approve/reject, người duyệt phải tự đọc lại toàn bộ diff và tự đoán LLM đang lo điều gì. Hỏi đúng câu thì người duyệt trả lời trong vài dòng, và LLM có ngữ cảnh để viết một review tốt hơn.

Hai node mới và một trường có sẵn
escalation_questions: trường có sẵn trong PRAnalysis, mặc định rỗng. LLM chỉ điền khi được dặn trong prompt.
node_escalate: dừng bằng interrupt() với kind="escalation". Câu trả lời trả về là một dict {câu_hỏi: câu_trả_lời}, được lưu vào state["escalation_answers"].
node_synthesize: gọi LLM lần thứ hai với diff, phân tích ban đầu và phần hỏi–đáp, rồi trả về một PRAnalysis mới thay cho bản cũ.
node_commit đã được viết để nhận hai đường vào: từ human_approval thì chỉ đăng khi approve, còn từ synthesize thì luôn đăng review đã tinh chỉnh, kèm phần hỏi–đáp ở cuối comment. Vì vậy bạn không cần sửa commit, chỉ cần nối đường cho đúng.

node_escalate đã có sẵn phần dự phòng: nếu LLM không sinh câu hỏi nào, nó dùng hai câu hỏi chung. Phần dự phòng giữ cho graph không hỏng, nhưng mục tiêu của bài là để LLM tự sinh câu hỏi bám vào diff.

Làm bài
1. Trong node_analyze, bổ sung system prompt theo comment TODO: khi confidence thấp, điền escalation_questions với 2–4 câu hỏi cụ thể, giàu ngữ cảnh, nêu rõ file hoặc đoạn nào trong diff. Comment TODO ghi mốc 60%; ngưỡng thật trong code là 0.58.
2. Trong node_escalate, gọi interrupt(...) với payload kind="escalation" gồm pr_url, confidence, confidence_reasoning, summary, risk_factors và questions. Trả về {"escalation_answers": answers}.
3. Trong node_synthesize, dựng prompt gồm diff gốc, phân tích ban đầu và từng cặp hỏi–đáp. Gọi get_llm().with_structured_output(PRAnalysis).invoke(...) và trả về {"analysis": refined}.
4. Trong build_graph, nối escalate → synthesize → commit. Vòng resume trong main() đã có sẵn.
5. Chạy với PR #2:
uv run python exercises/exercise_3_escalation.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/2
Chép
Checkpoint
Terminal hiện một panel viền vàng có tiêu đề Escalation conf=..., sau đó lần lượt in từng câu hỏi dạng Q: ... và chờ bạn gõ câu trả lời. Đọc các câu hỏi trước khi trả lời: chúng nên nhắc tới điểm cụ thể trong PR #2 như cách hash mật khẩu hay truy vấn trong Storage.add. Nếu bạn chỉ thấy hai câu hỏi chung của phần dự phòng, prompt ở bước 1 chưa đủ rõ.

Sau khi trả lời hết, phần Final in final_action = committed_after_escalation và final confidence = ... của bản phân tích mới. Trên GitHub, comment trên PR #2 có thêm phần "Reviewer answered escalation questions".

Lúc này agent đã đi đủ cả ba nhánh, nhưng mọi thứ vẫn chỉ nằm trong bộ nhớ. Tắt terminal là mất cả trạng thái lẫn dấu vết ai đã quyết định gì. Exercise 4 giải quyết hai việc đó.
------

Exercise 4 — Audit trail SQLite và phát lại phiên
Trong exercises/exercise_4_audit.py, bạn làm cho mỗi phiên review để lại dấu vết có thể truy vấn: mỗi bước quan trọng ghi một dòng có cấu trúc vào bảng audit_events. Phần checkpointer bền vững và vòng resume đã được viết sẵn trong run().

Vì sao agent có quyền đăng comment cần audit trail
Khi agent tự đăng comment hoặc dừng chờ người, đội cần trả lời được những câu hỏi như: PR này đi nhánh nào, LLM tự tin bao nhiêu, ai đã duyệt, mỗi bước mất bao lâu. README đưa ra một truy vấn kiểm tra đáng chú ý: một PR rủi ro cao mà lại được tự động duyệt là điều không được xảy ra.

SELECT * FROM audit_events WHERE risk_level = 'high' AND decision = 'auto';
Chép
Muốn chạy được truy vấn như vậy, log phải là các cột riêng, không phải một chuỗi văn bản tự do.

Hai cơ chế lưu trữ trong cùng một file
Cơ chế	Mục đích	Dạng dữ liệu	Ai dùng
Checkpointer của LangGraph (AsyncSqliteSaver)	Resume sau khi tiến trình chết, time-travel	Blob trạng thái	Runtime LangGraph
Bảng audit_events	Nhật ký quyết định có cấu trúc	Cột riêng, truy vấn được	Auditor, con người
Cả hai nằm trong ./hitl_audit.db, file này được tạo tự động ở lần chạy đầu. Yêu cầu "ghi vào audit trail" của bài được đáp ứng bởi audit_events; checkpointer là phần có thêm nhờ dùng AsyncSqliteSaver. Lab dùng SQLite thay cho PostgreSQL để không cần cài đặt; theo README, schema dạng cột giúp các truy vấn trên AuditEntry chuyển sang Postgres được bằng cách đổi checkpointer và connection string.

Đọc các trường của AuditEntry
AuditEntry (trong common/schemas.py) có timestamp tự điền, agent_id, action, confidence, risk_level, reviewer_id, decision, reason và execution_time_ms. Cách điền đúng là trả lời câu hỏi: tại bước này, điều gì đã thực sự được biết? node_fetch_pr là ví dụ mẫu duy nhất, hãy đọc kỹ trước khi viết. Ở bước đó chưa có phân tích, nên confidence=0.0, risk_level="med" làm giá trị trung tính, decision="pending", reviewer_id để None vì chưa có người tham gia.

Ba quy tắc giúp bạn điền các node còn lại:

Từ khi có analysis, tính risk_level bằng risk_level_for(confidence); đừng tự đặt chuỗi.
decision chỉ nhận auto, approve, reject, edit, escalate hoặc pending. Node route là dòng đầu tiên có quyết định thật.
reviewer_id chỉ có giá trị ở các bước có người, lấy từ os.environ.get("GITHUB_USER").
Làm bài
Docstring đầu file liệt kê 10 TODO.

1. Viết thân hàm audit(): một lời gọi write_audit_event(thread_id=state["thread_id"], pr_url=state["pr_url"], entry=entry). Hàm này là async, nên nhớ await.
2. Ghi một AuditEntry cho mỗi node analyze, route, commit, auto_approve và synthesize. Đo thời gian bằng t0 đã có sẵn: int((time.monotonic() - t0) * 1000). Ở synthesize, dùng confidence mới refined.confidence.
3. Ghi hai entry cho mỗi node human_approval và escalate: một dòng trước interrupt() khi chưa ai trả lời, một dòng sau khi đã có câu trả lời. Dòng trước interrupt sẽ được ghi lại lần nữa khi node chạy lại lúc resume; đó là hệ quả của cơ chế bạn đã gặp ở Exercise 2, và bạn sẽ thấy nó khi replay.
4. Chạy một phiên, rồi phát lại bằng thread_id được in ra:
uv run python exercises/exercise_4_audit.py --pr https://github.com/VinUni-AI20k/PR-Demo/pull/1
uv run python -m audit.replay --thread <thread_id-in-ra-ở-trên>
uv run python -m audit.replay --list
Chép
Checkpoint
audit.replay --thread in ra một dòng thời gian, mỗi dòng có action, conf=, risk= (màu xanh, vàng hoặc đỏ), decision= và reviewer=. Một phiên PR #1 hoàn chỉnh đi qua fetch_pr, analyze, route, các dòng human_approval và commit. Ở dòng sau khi bạn trả lời, reviewer là username của bạn thay vì -. --list hiện bảng các phiên gần đây cùng worst_risk và số event.

Bạn có thể xem trực tiếp file bằng sqlite3 nếu máy có sẵn:

sqlite3 hitl_audit.db "SELECT action, confidence, decision, reviewer_id FROM audit_events ORDER BY id;"
Chép
Nếu schema bị cũ sau khi bạn sửa code, xoá hitl_audit.db để tạo lại từ đầu. Khi đã có build_graph(checkpointer) chạy được cùng audit trail, bạn có đủ phần lõi để gắn giao diện web ở Exercise 5.
-----
Exercise 5 — Giao diện duyệt bằng Streamlit
Ở bài cuối, bạn bọc graph của Exercise 1–4 trong một ứng dụng Streamlit (app.py ở gốc repo), để người duyệt điều khiển toàn bộ luồng trên trình duyệt thay vì terminal.

Cùng ba nhánh, ba trải nghiệm khác nhau
Graph không đổi, nhưng điều người duyệt cần thấy thì khác nhau theo nhánh:

Confidence	Nhánh	Người duyệt thấy gì
Cao	auto_approve	Thẻ thành công: confidence, summary của LLM và link xem comment trên GitHub. Người duyệt không phải làm gì.
Trung bình	human_approval	Thẻ duyệt: diff, lý do của LLM, danh sách comment và ba nút Approve / Reject / Edit.
Thấp	escalate	Thẻ escalation: risk factors được làm nổi bật và một form chứa các câu hỏi của LLM.
Streamlit chạy lại cả file sau mỗi lần bấm
Đây là điều cần nắm trước khi viết app.py. Mỗi lần người dùng bấm nút hoặc submit form, Streamlit chạy lại toàn bộ script từ trên xuống. Biến Python thường sẽ mất; chỉ st.session_state còn giữ giá trị. Vì vậy khung bài lưu thread_id, pr_url, interrupt_payload và final trong st.session_state.

Bài toán này khớp với cách interrupt() hoạt động. Lần chạy đầu, graph dừng và trả payload; app lưu payload rồi vẽ thẻ tương ứng. Ở lần chạy lại sau khi người dùng bấm nút, renderer trả về câu trả lời, và app gọi graph với Command(resume=...) trên cùng thread_id. Vì trạng thái graph nằm trong AsyncSqliteSaver chứ không nằm trong tiến trình, tải lại trang vẫn không làm mất phiên.

Phần nào đã có sẵn, phần nào là của bạn
Khung app.py đã viết sẵn phần "Main flow" ở cuối file. Khi form được submit, nó tạo thread_id mới bằng uuid4, gọi run_graph(), và nếu kết quả có "__interrupt__" thì lưu payload vào st.session_state.interrupt_payload. Ở mỗi lần chạy lại, nó xem payload["kind"]: approval_request thì gọi render_approval_card, còn lại thì gọi render_escalation_card. Renderer nào trả về khác None thì app resume graph với câu trả lời đó rồi gọi st.rerun().

Nói cách khác, khung đã lo phần điều phối. Hai renderer chỉ có một trách nhiệm: trả None khi người dùng chưa quyết định, và trả đúng dạng dữ liệu mà node đang chờ khi họ đã quyết định. Nếu renderer trả sai dạng, lỗi sẽ không hiện ở UI mà hiện khi node đọc câu trả lời sau interrupt(). Vì thế hãy đối chiếu lại với Exercise 4: node_human_approval đọc resp.get("choice") và resp.get("feedback"), còn node_escalate lưu nguyên dict câu trả lời vào escalation_answers.

Phần hiển thị kết quả cuối cũng đã có: final_action bắt đầu bằng auto hoặc committed thì hiện st.success, rejected thì hiện cảnh báo. Theo README, thẻ của nhánh auto_approve nên có confidence, summary của LLM và link xem comment trên GitHub; bạn bổ sung các thông tin này vào phần hiển thị cuối.

Làm bài
1. Ở đầu app.py, import build_graph từ lời giải Exercise 4 (from exercises.exercise_4_audit import build_graph), hoặc chép phần nối graph vào thẳng file.
2. Hoàn thành run_graph(): build graph với cp làm checkpointer; nếu resume_value là None thì await app.ainvoke({"pr_url": ..., "thread_id": ...}, cfg), ngược lại thì await app.ainvoke(Command(resume=resume_value), cfg); trả về result.
3. Trong render_approval_card(), cho mỗi nút trả về dict tương ứng, ví dụ {"choice": "approve", "feedback": feedback}. Đây đúng là dạng mà node_human_approval đọc bằng resp.get("choice").
4. Trong render_escalation_card(), vẽ một st.text_input cho mỗi câu trong payload["questions"], gom thành dict {câu_hỏi: câu_trả_lời} và trả về dict đó khi form được submit.
5. Điền sidebar "Recent sessions" từ bảng audit_events: hiện thread_id, pr_url, worst_risk và last_event. Hàm audit.replay.list_threads in bảng bằng Rich ra console chứ không trả dữ liệu, nên hãy dùng lại câu SQL trong đó qua common.db.db_conn, rồi hiển thị bằng Streamlit. Khi chọn một dòng, gán st.session_state.thread_id và rerun.
streamlit đã có trong pyproject.toml, nên chỉ cần kiểm tra lại dòng này. Chạy ứng dụng:

uv run streamlit run app.py
Chép
Checkpoint
Mở trang Streamlit, dán URL PR #1 và bấm Run review. Sau spinner, bạn thấy thẻ "Approval requested — confidence ..." với diff có thể mở rộng và ba nút. Bấm Approve: trang hiện thông báo thành công kèm thread_id và lệnh replay. Lặp lại với PR #2: bạn thấy thẻ "Strong escalation", hộp đỏ liệt kê risk factors và form câu hỏi; điền và bấm Submit answers thì review đã tinh chỉnh được đăng. Chạy audit.replay --thread với thread_id hiển thị trên trang: dòng thời gian khớp với những gì bạn vừa bấm. Thấy đủ ba điều này nghĩa là app đã sẵn sàng để nộp.
----
**Nộp bài**
Nộp bài
Bài cá nhân. Bạn nộp link fork của repo Lab (KX-DAY27-HoVaTen-MSSV) trên tài khoản GitHub của bạn, chứa toàn bộ lời giải: đủ 4 exercise và app.py chạy được.

Bài được kiểm tra bằng cách chạy code, nên repo phải tự đứng được. Người kiểm tra cần clone về, tạo .env của riêng họ từ .env.example, chạy uv sync và các lệnh trong Lab mà không phải sửa gì. Đó là lý do bạn giữ nguyên bố cục thư mục: app.py import từ exercises/ và common/, còn audit.replay được chạy dưới dạng module từ gốc repo. Đổi tên hay di chuyển các thư mục này sẽ làm import hỏng.

Cấu trúc repo
Fork phải mang tên đúng mẫu KX-DAY27-HoVaTen-MSSV, nên khi clone về thư mục gốc cũng có tên đó. Nếu lúc fork bạn giữ tên mặc định, hãy đổi tên fork trong Settings → General → Repository name trước khi nộp. Bên trong giữ nguyên bố cục của Lab:

KX-DAY27-HoVaTen-MSSV/
├── app.py
├── pyproject.toml
├── .env.example
├── common/
├── audit/
└── exercises/
    ├── exercise_1_confidence.py
    ├── exercise_2_hitl.py
    ├── exercise_3_escalation.py
    └── exercise_4_audit.py
Chép
Vì bạn clone từ fork, origin đã trỏ tới repo của bạn. Commit lời giải và push lên fork:

git add .
git commit -m "Day27 HITL lab solution"
git push origin main
Chép
Mở trang fork trên GitHub và kiểm tra các file exercise đã có code của bạn, không còn là khung TODO.

Điều kiện đạt
Fork ở chế độ Public: người chấm mở được link mà không cần bạn cấp quyền.
Đủ 4 file exercise và app.py, không còn raise NotImplementedError ở các phần bạn phải làm.
Mỗi exercise chạy được bằng lệnh tương ứng trong Lab, và uv run streamlit run app.py mở được ứng dụng chạy hết luồng.
Comment review trên VinUni-AI20k/PR-Demo hiện dưới username GitHub của bạn.
Trước khi nộp link0/5

Fork tên đúng mẫu `KX-DAY27-HoVaTen-MSSV` và nằm dưới tài khoản của bạn.

`git status` không liệt kê `.env` hay `hitl_audit.db`.

Link nộp là link fork của bạn, không phải repo gốc `VinUni-AI20k`.

Mở link trong cửa sổ ẩn danh (chưa đăng nhập GitHub) vẫn thấy fork, tức fork đang Public.

Các lệnh chạy của Lab chạy lại được từ một bản clone sạch.
Hai file cần để ngoài Git đều đã có trong .gitignore: .env chứa token của bạn, còn *.db loại hitl_audit.db, vốn là dữ liệu audit và checkpoint của máy bạn. Nếu git status vẫn liệt kê một trong hai file này, hãy dừng lại và kiểm tra trước khi push. Một token đã bị push lên GitHub thì phải coi là đã lộ, và bạn cần thu hồi nó ở trang token của GitHub.

Cuối cùng, dán link fork vào form nộp bài của Lab này.