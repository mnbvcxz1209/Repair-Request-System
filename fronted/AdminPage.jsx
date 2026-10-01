import { useEffect, useMemo, useState } from "react"

const API = "http://127.0.0.1:8000"

export default function AdminPage() {
    const [items, setItems] = useState([])
    const [owners, setOwners] = useState([])
    const [selectedItemId, setSelectedItemId] = useState("")
    const [selectedOwnerIds, setSelectedOwnerIds] = useState(new Set())
    const [newTitle, setNewTitle] = useState("")
    const [loading, setLoading] = useState(false)
    const [msg, setMsg] = useState("")
    const [err, setErr] = useState("")

    const selectedItem = useMemo(
        () => items.find((x) => String(x.id) === String(selectedItemId)),
        [items, selectedItemId]
    )

    async function apiJson(url, options) {
        const res = await fetch(url, options)
        const data = await res.json().catch(() => ({}))
        if (!res.ok) {
            throw new Error(data.error || `HTTP ${res.status}`)
        }
        return data
    }

    async function loadItems() {
        const j = await apiJson(`${API}/api/work-items`)
        setItems(j.data || [])
    }

    async function loadOwners() {
        const j = await apiJson(`${API}/api/owners/all`)
        setOwners(j.data || [])
    }

    async function loadOwnersForItem(id) {
        if (!id) {
            setSelectedOwnerIds(new Set())
            return
        }
        const j = await apiJson(`${API}/api/work-items/${id}/owners`)
        const ids = new Set((j.data || []).map((x) => x.id))
        setSelectedOwnerIds(ids)
    }

    useEffect(() => {
        ; (async () => {
            try {
                setErr("")
                setLoading(true)
                await Promise.all([loadItems(), loadOwners()])
            } catch (e) {
                setErr(e.message || String(e))
            } finally {
                setLoading(false)
            }
        })()
    }, [])

    useEffect(() => {
        ; (async () => {
            try {
                setErr("")
                await loadOwnersForItem(selectedItemId)
            } catch (e) {
                setErr(e.message || String(e))
            }
        })()
    }, [selectedItemId])

    async function onCreateWorkItem() {
        try {
            setMsg("")
            setErr("")
            const title = newTitle.trim()
            if (!title) return setErr("請輸入工作內容名稱")
            setLoading(true)
            await apiJson(`${API}/api/work-items`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title }),
            })
            setNewTitle("")
            await loadItems()
            setMsg("✅ 已新增工作內容")
        } catch (e) {
            setErr(e.message || String(e))
        } finally {
            setLoading(false)
        }
    }

    async function onDeleteWorkItem(id) {
        if (!confirm("確定要刪除這個工作內容？（會連帶刪掉關聯）")) return
        try {
            setMsg("")
            setErr("")
            setLoading(true)
            await apiJson(`${API}/api/work-items/${id}`, { method: "DELETE" })
            if (String(selectedItemId) === String(id)) setSelectedItemId("")
            await loadItems()
            setMsg("✅ 已刪除工作內容")
        } catch (e) {
            setErr(e.message || String(e))
        } finally {
            setLoading(false)
        }
    }

    function toggleOwner(id) {
        setSelectedOwnerIds((prev) => {
            const next = new Set(prev)
            if (next.has(id)) next.delete(id)
            else next.add(id)
            return next
        })
    }

    async function onSaveOwners() {
        if (!selectedItemId) return setErr("請先選擇工作內容")
        try {
            setMsg("")
            setErr("")
            setLoading(true)
            await apiJson(`${API}/api/work-items/${selectedItemId}/owners`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ownerIds: Array.from(selectedOwnerIds) }),
            })
            setMsg("✅ 已儲存負責人設定")
        } catch (e) {
            setErr(e.message || String(e))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="page-shell">
            <div className="card">
                <h2 className="page-title">管理者介面</h2>
                <p className="page-subtitle">管理工作內容、以及每個工作內容的負責人</p>

                {loading && <div style={{ marginBottom: 10 }}>處理中...</div>}
                {err && <div style={{ color: "crimson", marginBottom: 10 }}>錯誤：{err}</div>}
                {msg && <div style={{ color: "#065f46", marginBottom: 10 }}>{msg}</div>}

                {/* 新增工作內容 */}
                <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 18 }}>
                    <input
                        value={newTitle}
                        onChange={(e) => setNewTitle(e.target.value)}
                        placeholder="新增工作內容，例如：帳號申請"
                        style={{
                            flex: 1,
                            padding: "10px 12px",
                            borderRadius: 10,
                            border: "1px solid #e5e7eb",
                        }}
                    />
                    <button onClick={onCreateWorkItem} disabled={loading}>
                        新增
                    </button>
                </div>

                {/* 工作內容清單 */}
                <div className="table" style={{ marginBottom: 18 }}>
                    <div className="tr head" style={{ gridTemplateColumns: "1fr 120px" }}>
                        <div className="th">工作內容</div>
                        <div className="th">操作</div>
                    </div>

                    {items.map((it) => (
                        <div className="tr" key={it.id} style={{ gridTemplateColumns: "1fr 120px" }}>
                            <div className="td">
                                <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
                                    <input
                                        type="radio"
                                        name="workItem"
                                        checked={String(selectedItemId) === String(it.id)}
                                        onChange={() => setSelectedItemId(String(it.id))}
                                    />
                                    {it.title}
                                </label>
                            </div>
                            <div className="td">
                                <button onClick={() => onDeleteWorkItem(it.id)} disabled={loading}>
                                    刪除
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {/* 綁定負責人 */}
                <h3 style={{ margin: "8px 0" }}>
                    綁定負責人 {selectedItem ? `：${selectedItem.title}` : ""}
                </h3>
                <div style={{ color: "#6b7280", marginBottom: 10 }}>
                    勾選後按「儲存設定」，即可更新這個工作內容的負責人。
                </div>

                {!selectedItemId ? (
                    <div style={{ color: "#6b7280" }}>請先在上方選擇一個工作內容</div>
                ) : (
                    <>
                        <div className="table">
                            <div className="tr head">
                                <div className="th">姓名</div>
                                <div className="th">備註</div>
                                <div className="th">分機</div>
                            </div>

                            {owners.map((p) => (
                                <div className="tr" key={p.id}>
                                    <div className="td">
                                        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedOwnerIds.has(p.id)}
                                                onChange={() => toggleOwner(p.id)}
                                            />
                                            {p.name}
                                        </label>
                                    </div>
                                    <div className="td">{p.sales}</div>
                                    <div className="td mono">{p.ext}</div>
                                </div>
                            ))}
                        </div>

                        <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end" }}>
                            <button onClick={onSaveOwners} disabled={loading}>
                                儲存設定
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
