import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Plans from "./pages/Plans";
import Feasibility from "./pages/Feasibility";

export default function App() {
  return (
    <BrowserRouter>
      <div style={{
        minHeight: "100vh",
        background: "#f4f4f4",
        fontFamily: "'Segoe UI', sans-serif"
      }}>
        <nav style={{
          background: "#1a1a2e",
          padding: "14px 32px",
          display: "flex",
          gap: "32px",
          alignItems: "center"
        }}>
          <span style={{
            color: "#fff",
            fontWeight: 600,
            fontSize: "16px",
            letterSpacing: "1px"
          }}>
            MILITARY PLANNER
          </span>
          <NavLink to="/plans" style={({ isActive }) => ({
            color: isActive ? "#c9a84c" : "#aaa",
            textDecoration: "none",
            fontSize: "14px",
            fontWeight: 500
          })}>
            Plans
          </NavLink>
          <NavLink to="/feasibility" style={({ isActive }) => ({
            color: isActive ? "#c9a84c" : "#aaa",
            textDecoration: "none",
            fontSize: "14px",
            fontWeight: 500
          })}>
            Feasibility Check
          </NavLink>
        </nav>
        <Routes>
          <Route path="/plans" element={<Plans />} />
          <Route path="/feasibility" element={<Feasibility />} />
          <Route path="/" element={<Plans />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}