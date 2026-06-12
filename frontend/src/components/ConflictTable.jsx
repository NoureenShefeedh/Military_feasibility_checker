export default function ConflictTable({ conflicts, resolutions }) {
  const vehicles = conflicts.filter(c => c.conflict_type === "Vehicle");
  const crew     = conflicts.filter(c => c.conflict_type === "Individual");

  const resolved   = (resolutions || []).filter(r => r.resolved);
  const unresolved = (resolutions || []).filter(r => !r.resolved);

  if (conflicts.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>

      {/* Vehicle conflicts */}
      {vehicles.length > 0 && <Section title="Vehicle Conflicts" data={vehicles} />}

      {/* Personnel conflicts */}
      {crew.length > 0 && <Section title="Personnel Conflicts" data={crew} />}

      {/* Replacements found */}
      {resolved.length > 0 && (
        <div>
          <p style={sectionLabelStyle}>Suggested Replacements</p>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f7f7f7" }}>
                {["Trip", "Type", "Original", "Replacement"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resolved.map((r, i) => (
                <tr key={i} style={{
                  borderBottom: "1px solid #f0f0f0",
                  background: i % 2 === 0 ? "#fff" : "#fafafa"
                }}>
                  <td style={tdStyle}>Trip {r.trip_id}</td>
                  <td style={tdStyle}>
                    <Badge
                      text={r.conflict_type}
                      color={r.conflict_type === "Vehicle" ? "#1a1a2e" : "#2e7d52"}
                    />
                  </td>
                  <td style={{ ...tdStyle, fontWeight: 600, color: "#c0392b" }}>
                    {r.original}
                  </td>
                  <td style={{ ...tdStyle, fontWeight: 600, color: "#2e7d52" }}>
                    {r.conflict_type === "Vehicle"
                      ? <>{r.replacement} <span style={{ color: "#888", fontWeight: 400, fontSize: "12px" }}>{r.replacement_name}</span></>
                      : <>{r.replacement_name} {r.crew_type && <span style={{ color: "#888", fontWeight: 400, fontSize: "12px" }}>({r.crew_type})</span>}</>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* No replacement found */}
      {unresolved.length > 0 && (
        <div>
          <p style={sectionLabelStyle}>No Replacement Found</p>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f7f7f7" }}>
                {["Trip", "Type", "Original", "Status"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {unresolved.map((r, i) => (
                <tr key={i} style={{
                  borderBottom: "1px solid #f0f0f0",
                  background: i % 2 === 0 ? "#fff" : "#fafafa"
                }}>
                  <td style={tdStyle}>Trip {r.trip_id}</td>
                  <td style={tdStyle}>
                    <Badge
                      text={r.conflict_type}
                      color={r.conflict_type === "Vehicle" ? "#1a1a2e" : "#2e7d52"}
                    />
                  </td>
                  <td style={{ ...tdStyle, fontWeight: 600, color: "#c0392b" }}>
                    {r.original}
                  </td>
                  <td style={tdStyle}>
                    <Badge
                      text={`No available ${r.conflict_type === "Vehicle" ? "vehicle" : "personnel"} of same type`}
                      color="#c0392b"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}

function Section({ title, data }) {
  return (
    <div>
      <p style={sectionLabelStyle}>{title}</p>
      <table style={tableStyle}>
        <thead>
          <tr style={{ background: "#f7f7f7" }}>
            {["Trip", "Name / Vehicle", "Issue", "Reason", "Details", "Trip Window"].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((c, i) => (
            <tr key={i} style={{
              borderBottom: "1px solid #f0f0f0",
              background: i % 2 === 0 ? "#fff" : "#fafafa"
            }}>
              <td style={tdStyle}>Trip {c.trip_id}</td>
              <td style={{ ...tdStyle, fontWeight: 600, color: "#1a1a2e" }}>
                {c.identifier}
              </td>
              <td style={tdStyle}>
                <SubtypeBadge subtype={c.conflict_subtype} />
              </td>
              <td style={tdStyle}>{c.reason}</td>
              <td style={tdStyle}>
                <Details conflict={c} />
              </td>
              <td style={tdStyle}>
                {fmt(c.actual_start)} → {fmt(c.actual_end)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SubtypeBadge({ subtype }) {
  const map = {
    unavailable:    { label: "Unavailable",      color: "#c0392b" },
    fuel:           { label: "Insufficient Fuel", color: "#8e44ad" },
    fuel_stop_late: { label: "Fuel Stop Late",    color: "#e67e22" },
    cannot_reach:   { label: "Cannot Reach",      color: "#d35400" },
  };
  const { label, color } = map[subtype] || { label: subtype, color: "#888" };
  return <Badge text={label} color={color} />;
}

function Details({ conflict }) {
  const { conflict_subtype, not_available_from, not_available_to, earliest_available } = conflict;

  if (conflict_subtype === "unavailable") {
    return (
      <>
        <span style={{ color: "#888", fontSize: "12px" }}>Busy: </span>
        {fmt(not_available_from)} → {fmt(not_available_to)}
        <br />
        <span style={{ color: "#888", fontSize: "12px" }}>Free from: </span>
        <span style={{ color: "#2e7d52", fontWeight: 600 }}>{fmt(earliest_available)}</span>
      </>
    );
  }
  if (conflict_subtype === "cannot_reach") {
    return (
      <>
        <span style={{ color: "#888", fontSize: "12px" }}>Earliest arrival: </span>
        <span style={{ color: "#d35400", fontWeight: 600 }}>{fmt(earliest_available) || "—"}</span>
      </>
    );
  }
  if (conflict_subtype === "fuel") {
    return <span style={{ color: "#8e44ad", fontSize: "12px", fontWeight: 500 }}>Vehicle cannot be fuelled in time</span>;
  }
  if (conflict_subtype === "fuel_stop_late") {
    return <span style={{ color: "#e67e22", fontSize: "12px", fontWeight: 500 }}>Fuel stop required but causes late arrival</span>;
  }
  return <span>—</span>;
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
      whiteSpace:   "nowrap"
    }}>
      {text}
    </span>
  );
}

const sectionLabelStyle = {
  fontSize: "11px", fontWeight: 600, letterSpacing: "1px",
  textTransform: "uppercase", color: "#888", margin: "0 0 12px"
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

function fmt(dtStr) {
  if (!dtStr) return "—";
  const d = new Date(dtStr);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit"
  });
}
