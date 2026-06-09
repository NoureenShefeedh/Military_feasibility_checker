export default function ConflictTable({ conflicts, schedule }) {
  const vehicles = conflicts.filter(c => c.conflict_type === "Vehicle");
  const crew = conflicts.filter(c => c.conflict_type === "Individual");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>

      {/* Always show schedule */}
      {schedule && schedule.length > 0 && (
        <div>
          <p style={sectionLabelStyle}>Computed Trip Schedule</p>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f7f7f7" }}>
                {["Trip", "Actual Start", "Actual End", "Type"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {schedule.map((s, i) => (
                <tr key={i} style={{
                  borderBottom: "1px solid #f0f0f0",
                  background: i % 2 === 0 ? "#fff" : "#fafafa"
                }}>
                  <td style={tdStyle}>Trip {s.trip_id}</td>
                  <td style={tdStyle}>{fmt(s.actual_start)}</td>
                  <td style={tdStyle}>{fmt(s.actual_end)}</td>
                  <td style={tdStyle}>
                    <Badge
                      text={s.sequenced ? "Sequenced" : "Independent"}
                      color={s.sequenced ? "#c9a84c" : "#888"}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {vehicles.length > 0 && <Section title="Vehicle Conflicts" data={vehicles} />}
      {crew.length > 0 && <Section title="Personnel Conflicts" data={crew} />}
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
                <Badge
                  text={c.conflict_subtype === "unavailable" ? "Unavailable" : "Cannot Reach"}
                  color={c.conflict_subtype === "unavailable" ? "#c0392b" : "#e67e22"}
                />
              </td>
              <td style={tdStyle}>{c.reason}</td>
              <td style={tdStyle}>
                {c.conflict_subtype === "unavailable"
                  ? <>
                      <span style={{ color: "#888", fontSize: "12px" }}>Busy: </span>
                      {fmt(c.not_available_from)} → {fmt(c.not_available_to)}
                      <br />
                      <span style={{ color: "#888", fontSize: "12px" }}>Free from: </span>
                      <span style={{ color: "#2e7d52", fontWeight: 600 }}>
                        {fmt(c.earliest_available)}
                      </span>
                    </>
                  : <>
                      <span style={{ color: "#888", fontSize: "12px" }}>Earliest arrival: </span>
                      <span style={{ color: "#e67e22", fontWeight: 600 }}>
                        {fmt(c.earliest_available) || "—"}
                      </span>
                    </>
                }
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

function Badge({ text, color }) {
  return (
    <span style={{
      background: color + "18",
      color: color,
      border: `1px solid ${color}40`,
      borderRadius: "4px",
      padding: "2px 8px",
      fontSize: "11px",
      fontWeight: 600,
      whiteSpace: "nowrap"
    }}>
      {text}
    </span>
  );
}

const sectionLabelStyle = {
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "1px",
  textTransform: "uppercase",
  color: "#888",
  margin: "0 0 12px"
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
  background: "#fff",
  borderRadius: "8px",
  overflow: "hidden",
  border: "1px solid #e8e8e8"
};

const thStyle = {
  padding: "10px 14px",
  textAlign: "left",
  fontWeight: 600,
  color: "#555",
  fontSize: "12px",
  borderBottom: "1px solid #e8e8e8"
};

const tdStyle = {
  padding: "10px 14px",
  color: "#444",
  verticalAlign: "middle"
};

function fmt(dtStr) {
  if (!dtStr) return "—";
  const d = new Date(dtStr);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit"
  });
}