import React from "react";

export default function ConflictTable({ conflicts, resolutions }) {
  const vehicles = conflicts.filter(c => c.conflict_type === "Vehicle");
  const crew     = conflicts.filter(c => c.conflict_type === "Individual");

  const resolved   = (resolutions || []).filter(r => r.resolved);
  const unresolved = (resolutions || []).filter(r => !r.resolved);

  if (conflicts.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>

      {vehicles.length > 0 && <Section title="Vehicle Conflicts" data={vehicles} />}
      {crew.length > 0     && <Section title="Personnel Conflicts" data={crew} />}

      {resolved.length > 0 && (
        <div>
          <p style={sectionLabelStyle}>Suggested Replacements</p>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f7f7f7" }}>
                {["Trip", "Type", "Original", "Replacement", "Type Match"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resolved.map((r, i) => (
                <React.Fragment key={i}>
                  <tr style={{
                    borderBottom: r.rounds ? "none" : "1px solid #f0f0f0",
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
                        ? <>
                            {Array.isArray(r.replacement)
                              ? r.replacement.join(", ")
                              : r.replacement}
                            {/* Only show name separately if it differs from the number */}
                            {r.replacement_name && r.replacement_name !== r.replacement && (
                              <span style={{ color: "#888", fontWeight: 400, fontSize: "12px", marginLeft: "6px" }}>
                                {Array.isArray(r.replacement_name)
                                  ? r.replacement_name.join(", ")
                                  : r.replacement_name}
                              </span>
                            )}
                            {/* Poach note */}
                            {r.resolution_type === "poached_from_lower_priority_plan" && r.poached_from_plan && (
                              <span style={{ color: "#e67e22", fontWeight: 500, fontSize: "12px", marginLeft: "8px" }}>
                                ↩ Taken from: {r.poached_from_plan}
                              </span>
                            )}
                          </>
                        : <>
                            {r.replacement_name}
                            {/* Poach note for individuals */}
                            {r.resolution_type === "poached_from_lower_priority_plan" && r.poached_from_plan && (
                              <span style={{ color: "#e67e22", fontWeight: 500, fontSize: "12px", marginLeft: "8px" }}>
                                ↩ Taken from: {r.poached_from_plan}
                              </span>
                            )}
                            {/* crew type — only when not a poach */}
                            {r.crew_type && r.resolution_type !== "poached_from_lower_priority_plan" && (
                              <span style={{ color: "#888", fontWeight: 400, fontSize: "12px", marginLeft: "6px" }}>
                                ({r.crew_type})
                              </span>
                            )}
                          </>
                      }
                    </td>
                    <td style={tdStyle}>
                      <TypeMatchBadge resolution={r} />
                    </td>
                  </tr>

                  {/* Inline round trip schedule — only renders when rounds exist */}
                  <RoundsTable rounds={r.rounds} resolutionType={r.resolution_type} />
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

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

function RoundsTable({ rounds, resolutionType }) {
  if (!rounds) return null;

  // ── combo round trips: rounds is a dict keyed by vehicle number ──
  if (resolutionType === "multi_vehicle_combo_round_trips") {
    return (
      <>
        {Object.entries(rounds).map(([vn, vdata]) => (
          <tr key={vn}>
            <td colSpan={5} style={{ padding: "0 14px 14px 14px", background: "#f4f8ff" }}>
              <div style={{
                border: "1px solid #c8ddf5", borderRadius: "6px",
                overflow: "hidden", marginTop: "4px"
              }}>
                <div style={{
                  padding: "8px 14px", background: "#e8f0fb",
                  fontSize: "11px", fontWeight: 700, letterSpacing: "0.8px",
                  textTransform: "uppercase", color: "#1a6eb5"
                }}>
                  {vn} — Round Trip Schedule
                  <span style={{ fontWeight: 400, marginLeft: "8px", color: "#555" }}>
                    (Share: {vdata.load_share?.toLocaleString()} kg,
                    Fuel: {vdata.fuel_cost} L)
                  </span>
                </div>
                <RoundsRows rounds={vdata.rounds} />
              </div>
            </td>
          </tr>
        ))}
      </>
    );
  }

  // ── single vehicle round trips: rounds is an array ──
  if (!Array.isArray(rounds) || rounds.length === 0) return null;

  return (
    <tr>
      <td colSpan={5} style={{ padding: "0 14px 14px 14px", background: "#f4f8ff" }}>
        <div style={{
          border: "1px solid #c8ddf5", borderRadius: "6px",
          overflow: "hidden", marginTop: "4px"
        }}>
          <div style={{
            padding: "8px 14px", background: "#e8f0fb",
            fontSize: "11px", fontWeight: 700, letterSpacing: "0.8px",
            textTransform: "uppercase", color: "#1a6eb5"
          }}>
            Round Trip Schedule
          </div>
          <RoundsRows rounds={rounds} />
        </div>
      </td>
    </tr>
  );
}

function RoundsRows({ rounds }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
      <thead>
        <tr style={{ background: "#f0f5fd" }}>
          {["Round", "Load (kg)", "Depart", "Arrive", "Note"].map(h => (
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
            <td style={{ padding: "7px 12px", color: "#e67e22", fontSize: "11px", fontWeight: 500 }}>
              {r.refuel_note || "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TypeMatchBadge({ resolution }) {
  const { resolution_type, split, conflict_type } = resolution;

  if (resolution_type === "poached_from_lower_priority_plan") {
    return <Badge text="Lower Priority Plan ↩" color="#e67e22" />;
  }
  if (conflict_type === "Individual") {
    return <Badge text="Same Type" color="#2e7d52" />;
  }
  if (resolution_type === "same_type_single") {
    return <Badge text="Same Type" color="#2e7d52" />;
  }
  if (resolution_type === "multi_vehicle_combo" && split) {
    return <Badge text="Split Load ⚠" color="#8e44ad" />;
  }
  if (resolution_type === "multi_vehicle_combo") {
    return <Badge text="Cross Type ⚠" color="#e67e22" />;
  }
  if (resolution_type === "single_vehicle_round_trips") {
    return <Badge text="Round Trips ↺" color="#1a6eb5" />;
  }
  if (resolution_type === "multi_vehicle_combo_round_trips") {
    return <Badge text="Combo Round Trips ↺" color="#8e44ad" />;
  }
  return <Badge text="—" color="#888" />;
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
    unavailable:    { label: "Unavailable",       color: "#c0392b" },
    fuel:           { label: "Insufficient Fuel",  color: "#8e44ad" },
    fuel_stop_late: { label: "Fuel Stop Late",     color: "#e67e22" },
    cannot_reach:   { label: "Cannot Reach",       color: "#d35400" },
    cascade:        { label: "Cascade Conflict",   color: "#7f8c8d" },
  };
  const { label, color } = map[subtype] || { label: subtype, color: "#888" };
  return <Badge text={label} color={color} />;
}

function Details({ conflict }) {
  const { conflict_subtype, not_available_from, not_available_to, earliest_available, blocking_trip_id } = conflict;

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
    return (
      <span style={{ color: "#8e44ad", fontSize: "12px", fontWeight: 500 }}>
        Vehicle cannot be fuelled in time
      </span>
    );
  }
  if (conflict_subtype === "fuel_stop_late") {
    return (
      <span style={{ color: "#e67e22", fontSize: "12px", fontWeight: 500 }}>
        Fuel stop required but causes late arrival
      </span>
    );
  }
  if (conflict_subtype === "cascade") {
    return (
      <span style={{ color: "#7f8c8d", fontSize: "12px", fontWeight: 500 }}>
        Blocked by Trip {blocking_trip_id}
      </span>
    );
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
