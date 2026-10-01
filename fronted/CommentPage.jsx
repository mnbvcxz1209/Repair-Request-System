import { useEffect, useState } from "react";

const API_BASE = ""; 

export default function CommentPage() {
    const [workItems, setWorkItems] = useState([]); // {id,title}
    const [owners, setOwners] = useState([]); // {id,name,sales,ext}

    const [loadingWorkItems, setLoadingWorkItems] = useState(false);
    const [loadingOwners, setLoadingOwners] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const [form, setForm] = useState({
        name: "",
        contact: "",        // 聯絡方式
        email: "",          // 
        work_item_id: "",
        owner_id: "",
        note: "",           // 備註
    });

    const [errors, setErrors] = useState({});

    // 1) 進頁面：事項下拉
    useEffect(() => {
        (async () => {
            try {
                setLoadingWorkItems(true);
                const r = await fetch(`${API_BASE}/work-items`, { credentials: "include" });
                if (!r.ok) throw new Error(`work-items failed: ${r.status}`);
                const j = await r.json();
                setWorkItems(j.data || []);
            } catch (e) {
                console.error(e);
                alert("讀取事項失敗，請確認後端是否啟動");
            } finally {
                setLoadingWorkItems(false);
            }
        })();
    }, []);

    // 2) 選事項後：該事項對應負責人
    useEffect(() => {
        const wid = form.work_item_id;
        if (!wid) {
            setOwners([]);
            return;
        }

        (async () => {
            try {
                setLoadingOwners(true);
                setOwners([]);

                const r = await fetch(`${API_BASE}/work-items/${encodeURIComponent(wid)}/owners`, {
                    credentials: "include",
                });
                if (!r.ok) throw new Error(`owners by work-item failed: ${r.status}`);
                const j = await r.json();
                setOwners(j.data || []);
            } catch (e) {
                console.error(e);
                alert("讀取負責人失敗");
            } finally {
                setLoadingOwners(false);
            }
        })();
    }, [form.work_item_id]);

    const onChange = (key) => (e) => {
        const value = e.target.value;

        // 切換事項時
        if (key === "work_item_id") {
            setForm((p) => ({ ...p, work_item_id: value, owner_id: "" }));
            setErrors((p) => ({ ...p, work_item_id: "", owner_id: "" }));
            return;
        }

        setForm((p) => ({ ...p, [key]: value }));
        setErrors((p) => ({ ...p, [key]: "" }));
    };

    //  除了備註(note)以外：所有欄位不可空 + email 格式檢查
    const validate = () => {
        const next = {};
        if (!form.name.trim()) next.name = "請輸入姓名";
        if (!form.contact.trim()) next.contact = "請輸入聯絡方式";

        if (!form.email.trim()) {
            next.email = "請輸入電子郵件";
        } else if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
            next.email = "電子郵件格式不正確";
        }

        if (!form.work_item_id) next.work_item_id = "請選擇事項";
        if (!form.owner_id) next.owner_id = "請選擇負責人";

        setErrors(next);
        return Object.keys(next).length === 0;
    };

    //  送出留言（POST /api/comments）
    const handleSubmit = async () => {
        if (!validate()) return;

        const payload = {
            name: form.name.trim(),
            contact: form.contact.trim(),
            email: form.email.trim(), 
            work_item_id: Number(form.work_item_id),
            owner_id: Number(form.owner_id),
            note: (form.note || "").trim(), 
            notify_name: "test", 
        };

        try {
            setSubmitting(true);

            const r = await fetch(`${API_BASE}/comments`, {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!r.ok) {
                const t = await r.text().catch(() => "");
                throw new Error(`POST /api/comments failed: ${r.status} ${t}`);
            }

            const created = await r.json();

            if (created?.line_push?.attempted) {
                if (created?.line_push?.ok) {
                    alert("送出成功 / Sent successfully ");
                } else {
                    alert(
                        `送出成功，但 LINE 通知失敗：${created?.line_push?.message || created?.line_push?.error || ""
                        }`
                    );
                }
            } else {
                alert("送出成功");
            }

            // 重置表單
            setForm({
                name: "",
                contact: "",
                email: "", // 
                work_item_id: "",
                owner_id: "",
                note: "",
            });
            setOwners([]);
            setErrors({});
        } catch (e) {
            console.error(e);
            alert(`送出失敗：${e?.message || e}`);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div style={{ maxWidth: 760, margin: "0 auto", padding: 16 }}>
            <h2 style={{ marginTop: 0 }}>留言</h2>

            <div style={{ display: "grid", gap: 12, padding: 16, border: "1px solid #ddd", borderRadius: 12 }}>
                <div>
                    <div>姓名 / Name *</div>
                    <input
                        value={form.name}
                        onChange={onChange("name")}
                        placeholder="請輸入姓名 / Please input your name"
                        style={{ width: "100%", padding: 10, marginTop: 6 }}
                    />
                    {errors.name && <div style={{ color: "crimson", marginTop: 6 }}>{errors.name}</div>}
                </div>

                <div>
                    <div>聯絡方式 / Contact information *</div>
                    <input
                        value={form.contact}
                        onChange={onChange("contact")}
                        placeholder="校內分機或行動電話 / Campus extensions or phone number"
                        style={{ width: "100%", padding: 10, marginTop: 6 }}
                    />
                    {errors.contact && <div style={{ color: "crimson", marginTop: 6 }}>{errors.contact}</div>}
                </div>

                {/*  電子郵件 */}
                <div>
                    <div>電子郵件 / Email *</div>
                    <input
                        type="email"
                        value={form.email}
                        onChange={onChange("email")}
                        placeholder="example@company.com"
                        style={{ width: "100%", padding: 10, marginTop: 6 }}
                    />
                    {errors.email && <div style={{ color: "crimson", marginTop: 6 }}>{errors.email}</div>}
                </div>

                <div>
                    <div>事項 *</div>
                    <select
                        value={form.work_item_id}
                        onChange={onChange("work_item_id")}
                        disabled={loadingWorkItems}
                        style={{ width: "100%", padding: 10, marginTop: 6 }}
                    >
                        <option value="">{loadingWorkItems ? "載入中..." : "請選擇事項 / Please select an item"}</option>
                        {workItems.map((w) => (
                            <option key={w.id} value={w.id}>
                                {w.title}
                            </option>
                        ))}
                    </select>
                    {errors.work_item_id && <div style={{ color: "crimson", marginTop: 6 }}>{errors.work_item_id}</div>}
                </div>

                <div>
                    <div>負責人（依事項掛勾） / Person in charge (assigned according to the task)*</div>
                    <select
                        value={form.owner_id}
                        onChange={onChange("owner_id")}
                        disabled={!form.work_item_id || loadingOwners}
                        style={{ width: "100%", padding: 10, marginTop: 6 }}
                    >
                        <option value="">
                            {!form.work_item_id
                                ? "請先選事項 / Please select item first"
                                : loadingOwners
                                    ? "載入中..."
                                    : "請選擇負責人 / Please select the person in charge"}
                        </option>
                        {owners.map((o) => (
                            <option key={o.id} value={o.id}>
                                {o.name}
                                {o.sales ? `（${o.sales}）` : ""}
                                {o.ext ? ` #${o.ext}` : ""}
                            </option>
                        ))}
                    </select>
                    {errors.owner_id && <div style={{ color: "crimson", marginTop: 6 }}>{errors.owner_id}</div>}
                    {form.work_item_id && !loadingOwners && owners.length === 0 && (
                        <div style={{ color: "#777", marginTop: 6 }}>
                            此事項尚未綁定負責人 / This matter has not yet been assigned to a responsible person.
                        </div>
                    )}
                </div>

                <div>
                    <div>備註（可不填）/ Remarks (optional)</div>
                    <textarea
                        value={form.note}
                        onChange={onChange("note")}
                        rows={4}
                        placeholder="如果是網路相關問題請附上1.棟別樓層2.單位(完整填寫單位牌子的全稱)3.IP / If the issue is related to the network, please include: 1. Building and floor number; 2. Company name (full name of the company); 3. IP address."
                        style={{ width: "100%", padding: 10, marginTop: 6, resize: "vertical" }}
                    />
                </div>

                <button
                    onClick={handleSubmit}
                    disabled={submitting}
                    style={{ padding: "10px 14px", borderRadius: 10, cursor: "pointer" }}
                >
                    {submitting ? "送出中..." : "送出留言 / send message"}
                </button>
            </div>
        </div>
    );
}
