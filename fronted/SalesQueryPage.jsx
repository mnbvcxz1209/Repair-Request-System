import { useEffect, useState } from "react"

export default function SalesQueryPage() {
    const [items, setItems] = useState([])
    const [selectedId, setSelectedId] = useState("")
    const [owners, setOwners] = useState([])
    const [loadingItems, setLoadingItems] = useState(true)
    const [loadingOwners, setLoadingOwners] = useState(false)
    const [error, setError] = useState("")

    // 載入工作內容清單
    useEffect(() => {
        async function loadItems() {
            try {
                setLoadingItems(true)
                setError("")
                const res = await fetch("http://127.0.0.1:8000/api/work-items")
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const json = await res.json()
                setItems(json.data || [])
            } catch (e) {
                setError(e.message || String(e))
            } finally {
                setLoadingItems(false)
            }
        }
        loadItems()
    }, [])

    // 選到某個工作內容後，載入負責人
    useEffect(() => {
        async function loadOwners() {
            if (!selectedId) {
                setOwners([])
                return
            }
            try {
                setLoadingOwners(true)
                setError("")
                const res = await fetch(`http://127.0.0.1:8000/api/work-items/${selectedId}/owners`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const json = await res.json()
                setOwners(json.data || [])
            } catch (e) {
                setError(e.message || String(e))
            } finally {
                setLoadingOwners(false)
            }
        }
        loadOwners()
    }, [selectedId])

    return (
        <div className="page-shell">
            <div className="card">
                <h2 className="page-title">工作內容查詢負責人 / Work Owner Lookup</h2>
                <p className="page-subtitle">選擇工作內容後，顯示對應負責人</p>

                {error && <div style={{ color: "crimson", marginBottom: 12 }}>錯誤：{error}</div>}

                <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 18 }}>
                    <label style={{ fontWeight: 600 }}>工作內容：</label>
                    <select
                        value={selectedId}
                        onChange={(e) => setSelectedId(e.target.value)}
                        disabled={loadingItems}
                        style={{ padding: "10px 12px", borderRadius: 10, border: "1px solid #e5e7eb", minWidth: 260 }}
                    >
                        <option value="">{loadingItems ? "載入中... / Loading..." : "請選擇工作內容 / Select work item"}</option>
                        {items.map((it) => (
                            <option key={it.id} value={it.id}>
                                {it.title}
                                {it.title_en ? ` / ${it.title_en}` : ""}
                            </option>
                        ))}
                    </select>
                </div>

                {selectedId && loadingOwners && <div>載入負責人中...</div>}

                {selectedId && !loadingOwners && (
                    <>
                        {owners.length === 0 ? (
                            <div style={{ color: "#6b7280" }}>此工作內容目前沒有設定負責人</div>
                        ) : (
                            <div className="table">
                                <div className="tr head">
                                    <div className="th">姓名 / Name</div>
                                    <div className="th">分機 / Campus extensions</div>
                                </div>

                                {owners.map((p) => (
                                    <div className="tr" key={p.id}>
                                        <div className="td">{p.name}</div>
                                        <div className="td mono">{p.ext || "-"}</div>
                                    </div>
                                ))}
                            </div>

                        )}
                    </>
                )}
            </div>
        </div>
    )
}
