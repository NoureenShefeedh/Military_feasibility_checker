export default function TripCard({ trip }) {
  return (
    <div style={{
      background: "#fff",
      border: "1px solid #e8e8e8",
      borderRadius: "8px",
      padding: "20px 24px",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: "16px"
      }}>
        <div>
          <span style={{
            fontSize: "11px",
            fontWeight: 600,
            letterSpacing: "1px",
            color: "#888",
            textTransform: "uppercase"
          }}>
            Trip {trip.trip_id}
          </span>
          <h3 style={{ margin: "4px 0 0", fontSize: "16px", color: "#1a1a2e" }}>
            {trip.from_location} → {trip.to_location}
          </h3>
        </div>
        <div style={{
          background: "#f0f0f0",
          borderRadius: "4px",
          padding: "4px 10px",
          fontSize: "12px",
          color: "#555",
          fontWeight: 500
        }}>
          {trip.distance_km} km
        </div>
      </div>

      {/* Info grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: "16px",
        marginBottom: "16px"
      }}>
        <InfoBlock label="Vehicle" value={`${trip.vehicle_name} (${trip.vehicle_number})`} />
        <InfoBlock label="Vehicle Type" value={trip.vehicle_type} />
        <InfoBlock label="Unit" value={trip.unit} />
        <InfoBlock label="Load" value={trip.load_type} />
        <InfoBlock label="Quantity" value={`${trip.quantity} units`} />
        <InfoBlock label="Duration" value={trip.duration} />
      </div>

      {/* Timing */}
      <div style={{
        background: "#f7f7f7",
        borderRadius: "6px",
        padding: "10px 14px",
        fontSize: "12px",
        color: "#555",
        marginBottom: "16px"
      }}>
        Starts <strong>T0 + {trip.start_offset}</strong> · Duration <strong>{trip.duration}</strong>
      </div>

      {/* Crew */}
      <div>
        <p style={{
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "1px",
          color: "#888",
          textTransform: "uppercase",
          margin: "0 0 8px"
        }}>
          Crew
        </p>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {trip.crew.map(c => (
            <div key={c.id} style={{
              background: "#1a1a2e",
              color: "#fff",
              borderRadius: "4px",
              padding: "5px 10px",
              fontSize: "12px"
            }}>
              {c.name}
              <span style={{ color: "#c9a84c", marginLeft: "6px" }}>{c.role}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function InfoBlock({ label, value }) {
  return (
    <div>
      <div style={{
        fontSize: "11px",
        color: "#888",
        fontWeight: 600,
        letterSpacing: "0.8px",
        textTransform: "uppercase",
        marginBottom: "3px"
      }}>
        {label}
      </div>
      <div style={{ fontSize: "13px", color: "#1a1a2e", fontWeight: 500 }}>
        {value}
      </div>
    </div>
  );
}