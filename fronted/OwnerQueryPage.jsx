import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

export default function OwnerQueryPage() {
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        async function load() {
            try {
                setLoading(true);
                setError("");

                // 負責人 + 工作
                const res = await fetch(`${API_BASE}/owner-work-items`);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);

                const json = await res.json();
                setRows(json.data || []);
            } catch (e) {
                setError(e.message || String(e));
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    return (
        <div className="page-shell">
            <div className="card">
                <h2 className="page-title">負責人通訊錄</h2>
                <p className="page-subtitle">姓名 / 工作 / 分機</p>

                {loading && <div>載入中...</div>}
                {error && <div style={{ color: "crimson" }}>錯誤：{error}</div>}

                {!loading && !error && (
                    <div className="table">
                        <div className="tr head">
                            <div className="th">姓名Name</div>
                            <div className="th">工作Work</div>
                            <div className="th">分機Campus extensions</div>
                        </div>

                        {rows.map((p) => (
                            <div className="tr" key={p.id}>
                                <div className="td">{p.name}</div>

                                {/*  工作 */}
                                <div className="td">
                                    {Array.isArray(p.works) && p.works.length > 0 ? (
                                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                                            {p.works.map((w) => (
                                                <span
                                                    key={w.id}
                                                    style={{
                                                        border: "1px solid #ddd",
                                                        padding: "2px 8px",
                                                        borderRadius: 999,
                                                        fontSize: 12,
                                                    }}
                                                >
                                                    {w.title}
                                                </span>
                                            ))}
                                        </div>
                                    ) : (
                                        <span style={{ color: "#777" }}>（未綁定工作）</span>
                                    )}
                                </div>

                                <div className="td mono">{p.ext || "-"}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
