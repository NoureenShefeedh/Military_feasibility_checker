import { useEffect, useState } from "react";
import { fetchPlans, checkFeasibility } from "../api/plans";

const BASE = "http://localhost:5000";
import ConflictTable from "../components/ConflictTable";

export default function Feasibility() {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [canCommit, setCanCommit] = useState(false);
  const [runExists, setRunExists] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [committingFeasible, setCommittingFeasible] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  useEffect(() => {
    fetchPlans().then(setPlans);
  }, []);

  const handleCheck = async () => {
    if (!selectedPlan || !date) return;
    setLoading(true);
    setCanCommit(false);
    setRunExists(false);
    setCommitResult(null);

    const data = await checkFeasibility(selectedPlan, date, time || null);
    setResult(data);

    const resolutions = data.resolutions?.resolutions ?? [];
    const conflicts   = data.conflicts ?? [];

    try {
      const res = await fetch(`${BASE}/api/plans/${selectedPlan}/can-commit`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conflicts, resolutions, date }),
      });
      const json = await res.json();
      setCanCommit(json.can_commit);
      setRunExists(json.run_id_exists);
    } catch {
      setCanCommit(false);
    }

    setLoading(false);
  };

  const handleCommit = async () => {
    if (!canCommit || committing) return;
    setCommitting(true);
    setCommitResult(null);
    try {
      const res = await fetch(`${BASE}/api/plans/${selectedPlan}/commit`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, time: time || "" }),
      });
      const json = await res.json();
      if (res.ok) {
        setCommitResult({ success: true, run_id: json.run_id, trips_saved: json.trips_saved, type: "replacement" });
        setRunExists(true);
      } else {
        setCommitResult({ success: false, error: json.error || "Commit failed." });
      }
    } catch {
      setCommitResult({ success: false, error: "Network error." });
    }
    setCommitting(false);
  };

  const handleCommitFeasible = async () => {
    if (committingFeasible) return;
    setCommittingFeasible(true);
    setCommitResult(null);
    const nextFeasibleTimes = result?.resolutions?.next_feasible_times ?? [];
    const missing = nextFeasibleTimes.filter(ft => !ft.feasible_start);
    if (missing.length > 0) {
      setCommitResult({ success: false, error: "Some trips have no feasible start time — cannot commit." });
      setCommittingFeasible(false);
      return;
    }
    try {
      const res = await fetch(`${BASE}/api/plans/${selectedPlan}/commit-feasible`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, time: time || "", next_feasible_times: nextFeasibleTimes }),
      });
      const json = await res.json();
      if (res.ok) {
        setCommitResult({ success: true, run_id: json.run_id, trips_saved: json.trips_saved, type: "feasible" });
        setRunExists(true);
      } else {
        setCommitResult({ success: false, error: json.error || "Commit failed." });
      }
    } catch {
      setCommitResult({ success: false, error: "Network error." });
    }
    setCommittingFeasible(false);
  };

  return (
    <div style={{ padding: "40px", maxWidth: "1000px", margin: "0 auto" }}>
      <h2 style={{ fontSize: "22px", color: "#1a1a2e", marginBottom: "8px" }}>
        Feasibility Check
      </h2>
      <p style={{ color: "#888", fontSize: "14px", marginBottom: "32px" }}>
        Select a plan and provide a date to check if it can be executed.
      </p>

      {/* Input row */}
      <div style={{
        display: "flex", gap: "16px", alignItems: "flex-end",
        marginBottom: "40px", background: "#fff",
        padding: "24px", borderRadius: "8px", border: "1px solid #e8e8e8"
      }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Operation</label>
          <select
            value={selectedPlan}
            onChange={e => { setSelectedPlan(e.target.value); setResult(null); setCanCommit(false); setCommitResult(null); }}
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
            type="date" value={date}
            onChange={e => { setDate(e.target.value); setResult(null); setCanCommit(false); setCommitResult(null); }}
            style={inputStyle}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>Start Time (optional)</label>
          <input
            type="time" value={time}
            onChange={e => { setTime(e.target.value); setResult(null); setCanCommit(false); setCommitResult(null); }}
            style={inputStyle}
          />
        </div>
        <button
          onClick={handleCheck}
          disabled={!selectedPlan || !date || loading}
          style={{
            background: "#1a1a2e", color: "#fff", border: "none",
            padding: "10px 24px", borderRadius: "6px", fontSize: "14px",
            fontWeight: 600, cursor: "pointer", height: "40px",
            opacity: (!selectedPlan || !date) ? 0.5 : 1
          }}
        >
          {loading ? "Checking..." : "Check"}
        </button>
      </div>

      {/* Result */}
      {result && (
        <>
          {/* Status bar + Commit button */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            gap: "12px", marginBottom: "24px", padding: "16px 24px",
            borderRadius: "8px",
            background: result.feasible ? "#f0faf4" : "#fff5f5",
            border: `1px solid ${result.feasible ? "#b2dfcc" : "#ffc0c0"}`
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{
                width: "10px", height: "10px", borderRadius: "50%",
                background: result.feasible ? "#2e7d52" : "#c0392b", flexShrink: 0
              }} />
              <span style={{ fontWeight: 600, fontSize: "15px", color: result.feasible ? "#2e7d52" : "#c0392b" }}>
                {result.feasible
                  ? "Plan is feasible — no conflicts detected"
                  : `Plan is not feasible — ${result.conflicts.length} conflict(s) found`}
              </span>
            </div>


          </div>

          {/* Commit feedback */}
          {commitResult && (
            <div style={{
              marginBottom: "20px", padding: "14px 20px", borderRadius: "8px",
              background: commitResult.success ? "#f0faf4" : "#fff5f5",
              border: `1px solid ${commitResult.success ? "#b2dfcc" : "#ffc0c0"}`,
              fontSize: "14px", fontWeight: 600,
              color: commitResult.success ? "#2e7d52" : "#c0392b",
            }}>
              {commitResult.success
                ? commitResult.type === "feasible"
                  ? `✓ Run committed at feasible times — ${commitResult.trips_saved} trip(s) saved (Run #${commitResult.run_id})`
                  : `✓ Run committed with replacements — ${commitResult.trips_saved} trip(s) saved (Run #${commitResult.run_id})`
                : `✗ ${commitResult.error}`}
            </div>
          )}

          <ConflictTable
            conflicts={result.conflicts}
            resolutions={result.resolutions?.resolutions ?? result.resolutions}
            feasibleTimes={result.resolutions?.next_feasible_times ?? []}
          />

          {/* ── Commit with Replacements — only when every conflict is resolved ── */}
          {canCommit && !commitResult?.success && (
            <div style={{
              marginTop: "28px",
              padding: "20px 24px",
              borderRadius: "8px",
              background: "#f0faf4",
              border: "1px solid #b2dfcc",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div>
                <p style={{ margin: 0, fontWeight: 600, fontSize: "14px", color: "#2e7d52" }}>
                  Commit with suggested replacements
                </p>
                <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>
                  Saves the run using the replacement vehicles and personnel found above.
                </p>
                {runExists && (
                  <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#e67e22", fontWeight: 500 }}>
                    ⚠ Replaces the existing run for this date
                  </p>
                )}
              </div>
              <button
                onClick={handleCommit}
                disabled={committing}
                style={{
                  background: committing ? "#888" : "#2e7d52",
                  color: "#fff", border: "none", padding: "10px 28px",
                  borderRadius: "6px", fontSize: "14px", fontWeight: 600,
                  cursor: committing ? "not-allowed" : "pointer", whiteSpace: "nowrap",
                  flexShrink: 0, marginLeft: "24px",
                }}
              >
                {committing ? "Committing..." : "Commit with Replacements"}
              </button>
            </div>
          )}

          {/* ── Commit at Next Feasible Time — shown when there are feasible times available ── */}
          {(() => {
            const feasibleTimes = result.resolutions?.next_feasible_times ?? [];
            const allFeasible   = feasibleTimes.length > 0 && feasibleTimes.every(ft => !!ft.feasible_start);
            if (!allFeasible || commitResult?.success) return null;
            return (
              <div style={{
                marginTop: "16px",
                padding: "20px 24px",
                borderRadius: "8px",
                background: "#f0f5ff",
                border: "1px solid #b3c8f5",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}>
                <div>
                  <p style={{ margin: 0, fontWeight: 600, fontSize: "14px", color: "#1a6eb5" }}>
                    Commit at next feasible times
                  </p>
                  <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#666" }}>
                    Conflicted trips shift to their earliest feasible start. Original vehicles and crew are kept — no replacements.
                  </p>
                  {runExists && (
                    <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#e67e22", fontWeight: 500 }}>
                      ⚠ Replaces the existing run for this date
                    </p>
                  )}
                </div>
                <button
                  onClick={handleCommitFeasible}
                  disabled={committingFeasible}
                  style={{
                    background: committingFeasible ? "#888" : "#1a6eb5",
                    color: "#fff", border: "none", padding: "10px 28px",
                    borderRadius: "6px", fontSize: "14px", fontWeight: 600,
                    cursor: committingFeasible ? "not-allowed" : "pointer", whiteSpace: "nowrap",
                    flexShrink: 0, marginLeft: "24px",
                  }}
                >
                  {committingFeasible ? "Committing..." : "Commit at Feasible Time"}
                </button>
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}

const labelStyle = {
  display: "block", fontSize: "11px", fontWeight: 600,
  letterSpacing: "0.8px", textTransform: "uppercase", color: "#888", marginBottom: "6px"
};

const inputStyle = {
  width: "100%", padding: "8px 12px", border: "1px solid #ddd",
  borderRadius: "6px", fontSize: "13px", color: "#1a1a2e",
  background: "#fafafa", boxSizing: "border-box", height: "40px"
};
