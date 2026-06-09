import { useEffect, useState } from "react";
import { fetchPlans, fetchPlanTrips } from "../api/plans";
import TripCard from "../components/TripCard";

export default function Plans() {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchPlans().then(setPlans);
  }, []);

  const handleSelectPlan = async (plan) => {
    setSelectedPlan(plan);
    setLoading(true);
    const data = await fetchPlanTrips(plan.plan_id);
    setTrips(data);
    setLoading(false);
  };

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 52px)" }}>
      {/* Left sidebar — plan list */}
      <div style={{
        width: "280px",
        background: "#fff",
        borderRight: "1px solid #e0e0e0",
        padding: "24px 0",
        flexShrink: 0
      }}>
        <p style={{
          padding: "0 20px 12px",
          fontSize: "11px",
          fontWeight: 600,
          letterSpacing: "1.5px",
          color: "#888",
          textTransform: "uppercase",
          margin: 0
        }}>
          Plans
        </p>
        {plans.map(plan => (
          <div
            key={plan.plan_id}
            onClick={() => handleSelectPlan(plan)}
            style={{
              padding: "14px 20px",
              cursor: "pointer",
              borderLeft: selectedPlan?.plan_id === plan.plan_id
                ? "3px solid #1a1a2e" : "3px solid transparent",
              background: selectedPlan?.plan_id === plan.plan_id
                ? "#f7f7f7" : "transparent",
              transition: "all 0.15s"
            }}
          >
            <div style={{ fontWeight: 600, fontSize: "14px", color: "#1a1a2e" }}>
              {plan.plan_name}
            </div>
            <div style={{ fontSize: "12px", color: "#888", marginTop: "4px" }}>
              {plan.num_of_vehicles} vehicles · T0 {plan.default_start_time}
            </div>
          </div>
        ))}
      </div>

      {/* Right — trip details */}
      <div style={{ flex: 1, padding: "32px", overflowY: "auto" }}>
        {!selectedPlan && (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "#aaa",
            fontSize: "14px"
          }}>
            Select an operation to view trip details
          </div>
        )}
        {selectedPlan && (
          <>
            <div style={{ marginBottom: "28px" }}>
              <h2 style={{ margin: 0, fontSize: "22px", color: "#1a1a2e" }}>
                {selectedPlan.plan_name}
              </h2>
              <div style={{
                display: "flex",
                gap: "24px",
                marginTop: "10px",
                fontSize: "13px",
                color: "#666"
              }}>
                <span>Vehicles: {selectedPlan.num_of_vehicles}</span>
                <span>Default T0: {selectedPlan.default_start_time}</span>
                <span>Total Fuel: {selectedPlan.total_fuel} L</span>
              </div>
            </div>
            {loading ? (
              <div style={{ color: "#888", fontSize: "14px" }}>Loading trips...</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {trips.map(trip => (
                  <TripCard key={trip.trip_id} trip={trip} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}