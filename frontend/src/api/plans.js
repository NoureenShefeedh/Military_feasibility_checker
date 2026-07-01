const BASE = "http://localhost:5000";

export const fetchPlans = async () => {
  const res = await fetch(`${BASE}/api/plans`);
  return res.json();
};

export const fetchPlanTrips = async (planId) => {
  const res = await fetch(`${BASE}/api/plans/${planId}/trips`);
  return res.json();
};

export const checkFeasibility = async (planId, date, time = null) => {
  const res = await fetch(`${BASE}/api/feasibility`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, date, time }),
  });
  return res.json();
};
