import { useEffect, useState } from "react";
import { fetchPlans, checkFeasibility } from "../api/plans";
import ConflictTable from "../components/ConflictTable";
import ResolutionTable from "../components/ResolutionTable";
export default function Feasibility() {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPlans().then(setPlans);
  }, []);

  const handleCheck = async () => {
    if (!selectedPlan || !date) return;
    setLoading(true);
    const data = await checkFeasibility(selectedPlan, date, time || null);
    setResult(data);
    setLoading(false);
  };

  return (
    <div style={{ padding: "40px", maxWidth: "900px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "22px", color: "#1a1a2e", marginBottom: "8px" }}>
        Feasibility Check
      </h2>
      <p style={{ color: "#888", fontSize: "14px", marginBottom: "32px" }}>
        Select a plan and provide a date to check if it can be executed.
      </p>

      {/* Input row */}
      <div style={{
        display: "flex",
        gap: "16px",
        alignItems: "flex-end",
        marginBottom: "40px",
        background: "#fff",
        padding: "24px",
        borderRadius: "8px",
        border: "1px solid #e8e8e8"
      }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Operation</label>
          <select
            value={selectedPlan}
            onChange={e => { setSelectedPlan(e.target.value); setResult(null); }}
            style={inputStyle}
          >
            <option value="">Select a plan</option>
            {plans.map(p => (
              <option key={p.plan_id} value={p.plan_id}>{p.plan_name}</option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Date</label>
          <input
            type="date"
            value={date}
            onChange={e => { setDate(e.target.value); setResult(null); }}
            style={inputStyle}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Start Time (optional)</label>
          <input
            type="time"
            value={time}
            onChange={e => { setTime(e.target.value); setResult(null); }}
            style={inputStyle}
          />
        </div>
        <button
          onClick={handleCheck}
          disabled={!selectedPlan || !date || loading}
          style={{
            background: "#1a1a2e",
            color: "#fff",
            border: "none",
            padding: "10px 24px",
            borderRadius: "6px",
            fontSize: "14px",
            fontWeight: 600,
            cursor: "pointer",
            height: "40px",
            opacity: (!selectedPlan || !date) ? 0.5 : 1
          }}
        >
          {loading ? "Checking..." : "Check"}
        </button>
      </div>

      {/* Result */}
      {result && (
        <>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "24px",
            padding: "16px 24px",
            borderRadius: "8px",
            background: result.feasible ? "#f0faf4" : "#fff5f5",
            border: `1px solid ${result.feasible ? "#b2dfcc" : "#ffc0c0"}`
          }}>
            <div style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: result.feasible ? "#2e7d52" : "#c0392b",
              flexShrink: 0
            }} />
            <span style={{
              fontWeight: 600,
              fontSize: "15px",
              color: result.feasible ? "#2e7d52" : "#c0392b"
            }}>
              {result.feasible
                ? "Plan is feasible — no conflicts detected"
                : `Plan is not feasible — ${result.conflicts.length} conflict(s) found`}
            </span>
          </div>

          
          <ConflictTable
  conflicts={result.conflicts}
  schedule={result.schedule}
  resolutions={result.resolutions}  // ← add this
/>
{!result.feasible && (
  <ResolutionTable resolutions={result.resolutions} />
)}
        </>
      )}
    </div>
  );
}

const labelStyle = {
  display: "block",
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "0.8px",
  textTransform: "uppercase",
  color: "#888",
  marginBottom: "6px"
};

const inputStyle = {
  width: "100%",
  padding: "8px 12px",
  border: "1px solid #ddd",
  borderRadius: "6px",
  fontSize: "13px",
  color: "#1a1a2e",
  background: "#fafafa",
  boxSizing: "border-box",
  height: "40px"
};