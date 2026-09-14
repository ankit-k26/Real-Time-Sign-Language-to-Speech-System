import { useState } from "react";
import LivePage from "./components/LivePage";
import CollectPage from "./components/CollectPage";
import "./styles.css";

export default function App() {
  const [tab, setTab] = useState("live");

  return (
    <div className="app-shell">
      <header>
        <h1>🤟 Sign Language to Speech</h1>
        <nav>
          <button className={tab === "live" ? "active" : ""} onClick={() => setTab("live")}>Live</button>
          <button className={tab === "collect" ? "active" : ""} onClick={() => setTab("collect")}>Collect Data</button>
        </nav>
      </header>
      <main>
        {tab === "live" ? <LivePage /> : <CollectPage />}
      </main>
    </div>
  );
}
