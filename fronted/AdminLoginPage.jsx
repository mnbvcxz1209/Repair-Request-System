import { useState } from "react"
import { useNavigate } from "react-router-dom"

const API = "http://127.0.0.1:8000" // 或你已改 localhost

export default function AdminLoginPage() {
    const [username, setUsername] = useState("admin")
    const [password, setPassword] = useState("")
    const [err, setErr] = useState("")
    const [loading, setLoading] = useState(false)
    const nav = useNavigate()

    async function onLogin(e) {
        e.preventDefault()
        try {
            setErr("")
            setLoading(true)
            const res = await fetch(`${API}/api/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify({ username, password }),
            })
            const data = await res.json()
            if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
            nav("/admin")
        } catch (e2) {
            setErr(e2.message || String(e2))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="page-shell">
            <div className="card" style={{ maxWidth: 420 }}>
                <h2 className="page-title">管理者登入</h2>
                <p className="page-subtitle">輸入帳號密碼後才能進入管理介面</p>

                {err && <div style={{ color: "crimson", marginBottom: 10 }}>錯誤：{err}</div>}

                <form onSubmit={onLogin} style={{ display: "grid", gap: 10 }}>
                    <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="帳號" />
                    <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="密碼" type="password" />
                    <button disabled={loading} type="submit">{loading ? "登入中..." : "登入"}</button>
                </form>
            </div>
        </div>
    )
}
