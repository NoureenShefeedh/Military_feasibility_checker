// src/components/ResolutionTable.jsx
export default function ResolutionTable({ resolutions }) {
  if (!resolutions || resolutions.length === 0) return null;

  const resolved   = resolutions.filter(r => r.resolved);
  const unresolved = resolutions.filter(r => !r.resolved);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <p style={sectionLabelStyle}>Suggested Resolutions</p>

      {resolved.length > 0 && (
        <div>
          <p style={{ ...sectionLabelStyle, color: "#2e7d52", marginBottom: "10px" }}>
            Replacements Found
          </p>
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
                  <td style={{ ...tdStyle, color: "#c0392b", fontWeight: 600 }}>
                    {r.original}
                  </td>
                  <td style={{ ...tdStyle, color: "#2e7d52", fontWeight: 600 }}>
                    {r.replacement}
                    {r.crew_type && (
                      <span style={{ color: "#888", fontWeight: 400, marginLeft: "6px", fontSize: "12px" }}>
                        ({r.crew_type})
                      </span>
                    )}
                  </td>
                 
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {unresolved.length > 0 && (
        <div>
          <p style={{ ...sectionLabelStyle, color: "#c0392b", marginBottom: "10px" }}>
            No Replacement Found
          </p>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f7f7f7" }}>
                {["Trip", "Type", "Original", "Reason"].map(h => (
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
                  <td style={{ ...tdStyle, color: "#c0392b", fontWeight: 600 }}>
                    {r.original}
                  </td>
                  <td style={{ ...tdStyle, color: "#888" }}>
                    No available {r.conflict_type === "Vehicle" ? "vehicle" : "personnel"} of the same type
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

function Badge({ text, color }) {
  return (
    <span style={{
      background: color + "18",
      color,
      border: `1px solid ${color}40`,
      borderRadius: "4px",
      padding: "2px 8px",
      fontSize: "11px",
      fontWeight: 600
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