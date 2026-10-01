import { BrowserRouter, Routes, Route, Link, Outlet, useLocation } from "react-router-dom"
import HomePage from "./pages/HomePage"
import OwnerQueryPage from "./pages/OwnerQueryPage"
import SalesQueryPage from "./pages/SalesQueryPage"
import AdminPage from "./pages/AdminPage"
import "./App.css"
import AdminLoginPage from "./pages/AdminLoginPage"
import AdminGuard from "./components/AdminGuard"
import CommentPage from "./pages/CommentPage";


function Layout() {
  const location = useLocation()
  const isHome = location.pathname === "/"

  return (
    <>
      <nav className="navbar">
        <Link to="/">首頁</Link>
        <Link to="/owner">查詢負責人</Link>
        <Link to="/sales">查詢工作內容</Link>
        <Link to="/admin-login">管理者</Link>
      </nav>

      <main className={isHome ? "main center" : "main"}>
        <Outlet />
      </main>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 這一層套用 Layout */}
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/owner" element={<OwnerQueryPage />} />
          <Route path="/sales" element={<SalesQueryPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin-login" element={<AdminLoginPage />} />
          <Route
            path="/admin"
            element={
              <AdminGuard>
                <AdminPage />
              </AdminGuard>
            }
          />
          <Route path="/comment" element={<CommentPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
