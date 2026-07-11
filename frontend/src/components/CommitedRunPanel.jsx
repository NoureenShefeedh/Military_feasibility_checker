import React from "react";

// Props:
//   data    – response from GET /api/plans/:id/scheduled-run?date=...
//             shape: { exists: true, run_id, created_at, committed_time, trips: [...] }
//             or { exists: false }, or null while nothing has been fetched yet.
//   loading – true while the fetch for `data` is in flight.
//   onBack  – called when the user clicks "← Back to Feasibility Check".
export default function CommittedRunPanel({ data, loading, onBack }) {
  if (loading) {
    return (
      <div style={panelStyle}>
        <BackBar onBack={onBack} />
        <p style={{ color: "#888", fontSize: "14px", padding: "24px 0" }}>
          Loading committed run…
        </p>
      </div>
    );
  }

  if (!data || data.exists === false) {
    return (
      <div style={panelStyle}>
        <BackBar onBack={onBack} />
        <p style={{ color: "#c0392b", fontSize: "14px", padding: "24px 0" }}>
          No committed run found for this plan and date.
        </p>
      </div>
    );
  }

  const { run_id, created_at, committed_time, trips = [] } = data;

  return (
    <div style={panelStyle}>
      <BackBar onBack={onBack} />

      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: "24px", padding: "16px 24px", borderRadius: "8px",
        background: "#f0faf4", border: "1px solid #b2dfcc",
      }}>
        <div>
          <span style={{ fontWeight: 600, fontSize: "15px", color: "#2e7d52" }}>
            Committed Run #{run_id}
          </span>
          {committed_time && (
            <span style={{ marginLeft: "12px", fontSize: "13px", color: "#555" }}>
              Start time: <strong>{committed_time}</strong>
            </span>
          )}
        </div>
        {created_at && (
          <span style={{ fontSize: "12px", color: "#888" }}>
            Committed on {fmt(created_at)}
          </span>
        )}
      </div>

      <table style={tableStyle}>
        <thead>
          <tr style={{ background: "#f7f7f7" }}>
            {["Trip", "Route", "Vehicle", "Crew", "Start", "End", "Resolution"].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trips.map((t, i) => {
            const vehicleRes = t.resolution_data?.Vehicle;
            return (
              <React.Fragment key={t.trip_id}>
                <tr style={{
                  borderBottom: vehicleRes?.rounds ? "none" : "1px solid #f0f0f0",
                  background: i % 2 === 0 ? "#fff" : "#fafafa"
                }}>
                  <td style={tdStyle}>Trip {t.trip_id}</td>
                  <td style={tdStyle}>{t.from_location} → {t.to_location}</td>
                  <td style={{ ...tdStyle, fontWeight: 600, color: "#1a1a2e" }}>
                    {t.vehicle_name || t.vehicle_number}
                  </td>
                  <td style={tdStyle}>
                    {(t.crew || []).length > 0 ? t.crew.join(", ") : "—"}
                  </td>
                  <td style={tdStyle}>{fmt(t.actual_start)}</td>
                  <td style={tdStyle}>{fmt(t.actual_end)}</td>
                  <td style={tdStyle}>
                    <ResolutionBadge resolutionData={t.resolution_data} />
                  </td>
                </tr>
                <RoundsRow
                  vehicleRes={vehicleRes}
                  colSpan={7}
                />
              </React.Fragment>
            );
          })}
        </tbody>
      </table>

      {trips.length === 0 && (
        <p style={{ color: "#888", fontSize: "13px", marginTop: "16px" }}>
          This run has no trips recorded.
        </p>
      )}
    </div>
  );
}

function BackBar({ onBack }) {
  return (
    <button
      onClick={onBack}
      style={{
        background: "transparent", border: "none", color: "#1a6eb5",
        fontSize: "13px", fontWeight: 600, cursor: "pointer",
        padding: "0 0 20px 0", display: "flex", alignItems: "center", gap: "6px",
      }}
    >
      ← Back to Feasibility Check
    </button>
  );
}

// Shows what (if anything) had to be resolved for this trip at commit time.
// resolution_data is {} for trips that ran with their original vehicle/crew
// at their normal time, and holds Vehicle/Individual resolution info
// (same shape as resolve_conflicts()'s per-conflict entries) otherwise.
function ResolutionBadge({ resolutionData }) {
  const entries = Object.entries(resolutionData || {});
  if (entries.length === 0) {
    return <Badge text="As planned" color="#888" />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      {entries.map(([conflictType, res]) => {
        const label = describeResolution(res);
        return (
          <Badge
            key={conflictType}
            text={`${conflictType}: ${label}`}
            color={res.resolution_type === "poached_from_lower_priority_plan" ? "#e67e22" : "#8e44ad"}
          />
        );
      })}
    </div>
  );
}

function describeResolution(res) {
  switch (res.resolution_type) {
    case "same_type_single":
      return `Replaced with ${res.replacement}`;
    case "poached_from_lower_priority_plan":
      return `Reclaimed from ${res.poached_from_plan}`;
    case "multi_vehicle_combo":
      return `Split across ${Array.isArray(res.replacement) ? res.replacement.join(", ") : res.replacement}`;
    case "multi_vehicle_combo_round_trips":
      return "Combo round trips";
    case "single_vehicle_round_trips":
      return `Round trips via ${res.replacement}`;
    default:
      return res.replacement_name || res.replacement || "Resolved";
  }
}

// Renders the round-by-round schedule for a trip's Vehicle resolution, if
// it used one of the round-trip strategies. Returns null (no extra row)
// for trips that didn't need round trips — same_type_single, poach,
// combo (single-pass), or no conflict at all.
function RoundsRow({ vehicleRes, colSpan }) {
  if (!vehicleRes || !vehicleRes.rounds) return null;

  const { resolution_type, rounds } = vehicleRes;

  // ── Combo round trips: rounds is a dict { vehicle_number: { load_share, fuel_cost, rounds: [...] } } ──
  if (resolution_type === "multi_vehicle_combo_round_trips") {
    const byVehicle = Object.entries(rounds);
    if (byVehicle.length === 0) return null;
    return (
      <tr>
        <td colSpan={colSpan} style={{ padding: "0 14px 14px 14px", background: "#f4f8ff" }}>
          {byVehicle.map(([vn, vdata]) => (
            <div key={vn} style={{
              border: "1px solid #c8ddf5", borderRadius: "6px",
              overflow: "hidden", marginTop: "8px"
            }}>
              <div style={{
                padding: "8px 14px", background: "#e8f0fb",
                fontSize: "11px", fontWeight: 700, letterSpacing: "0.8px",
                textTransform: "uppercase", color: "#1a6eb5"
              }}>
                {vn} — Round Trip Schedule
                <span style={{ fontWeight: 400, marginLeft: "8px", color: "#555" }}>
                  (Share: {vdata.load_share?.toLocaleString()} kg, Fuel: {vdata.fuel_cost} L)
                </span>
              </div>
              <RoundsTable rounds={vdata.rounds} />
            </div>
          ))}
        </td>
      </tr>
    );
  }

  // ── Single vehicle round trips: rounds is a flat array ──
  if (!Array.isArray(rounds) || rounds.length === 0) return null;

  return (
    <tr>
      <td colSpan={colSpan} style={{ padding: "0 14px 14px 14px", background: "#f4f8ff" }}>
        <div style={{
          border: "1px solid #c8ddf5", borderRadius: "6px",
          overflow: "hidden", marginTop: "8px"
        }}>
          <div style={{
            padding: "8px 14px", background: "#e8f0fb",
            fontSize: "11px", fontWeight: 700, letterSpacing: "0.8px",
            textTransform: "uppercase", color: "#1a6eb5"
          }}>
            Round Trip Schedule
          </div>
          <RoundsTable rounds={rounds} />
        </div>
      </td>
    </tr>
  );
}

function RoundsTable({ rounds }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
      <thead>
        <tr style={{ background: "#f0f5fd" }}>
          {["Round", "Load (kg)", "Depart", "Arrive", "Refuel"].map(h => (
            <th key={h} style={{
              padding: "7px 12px", textAlign: "left",
              color: "#555", fontWeight: 600,
              borderBottom: "1px solid #d0e2f5"
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rounds.map((r, i) => (
          <tr key={i} style={{
            borderBottom: i < rounds.length - 1 ? "1px solid #e8f0fb" : "none",
            background: i % 2 === 0 ? "#fff" : "#f9fbff"
          }}>
            <td style={{ padding: "7px 12px", fontWeight: 700, color: "#1a6eb5" }}>
              #{r.round}
            </td>
            <td style={{ padding: "7px 12px", color: "#444" }}>
              {r.load?.toLocaleString()}
            </td>
            <td style={{ padding: "7px 12px", color: "#444" }}>
              {fmt(r.depart_start)}
            </td>
            <td style={{ padding: "7px 12px", color: "#444" }}>
              {fmt(r.arrive_end)}
            </td>
            <td style={{ padding: "7px 12px", color: r.refuel_note ? "#8e44ad" : "#bbb", fontSize: "11px" }}>
              {r.refuel_note || "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Badge({ text, color }) {
  return (
    <span style={{
      background:   color + "18",
      color,
      border:       `1px solid ${color}40`,
      borderRadius: "4px",
      padding:      "2px 8px",
      fontSize:     "11px",
      fontWeight:   600,
      whiteSpace:   "nowrap",
      display:      "inline-block",
    }}>
      {text}
    </span>
  );
}

function fmt(dtStr) {
  if (!dtStr) return "—";
  const d = new Date(dtStr);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit"
  });
}

const panelStyle = {
  background: "#fff", borderRadius: "8px",
  border: "1px solid #e8e8e8", padding: "24px",
};

const tableStyle = {
  width: "100%", borderCollapse: "collapse", fontSize: "13px",
  background: "#fff", borderRadius: "8px", overflow: "hidden",
  border: "1px solid #e8e8e8"
};

const thStyle = {
  padding: "10px 14px", textAlign: "left", fontWeight: 600,
  color: "#555", fontSize: "12px", borderBottom: "1px solid #e8e8e8"
};

const tdStyle = { padding: "10px 14px", color: "#444", verticalAlign: "middle" };
