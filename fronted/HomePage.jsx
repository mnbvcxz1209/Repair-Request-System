import { Link } from "react-router-dom"

export default function HomePage() {
    return (
        <div className="home-container">
            <h1 className="title">查詢系統 / Search System</h1>
            <p className="subtitle">請選擇查詢類型： / Please select query type</p>

            <div className="button-group">
                <Link to="/owner"><button>查詢負責人 / Query the person in charge</button></Link>
                <Link to="/sales"><button>查詢工作 / Query job</button></Link>
                <Link to="/comment"><button>前往留言 / leave a messsge</button></Link>
            </div>
        </div>
    )
}
