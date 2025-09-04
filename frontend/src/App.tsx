import { useState, useEffect } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./App.css";

type ApiResponse = {
  output_realizowane: string;
  output_oczekuje: string;
  output_combined: string;
  output_nie_dodane: string;
  output_wykonane: string;
  timestamp: string;
};

function App() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("http://127.0.0.1:8000/get_data");
      if (!response.ok) {
        let error = "Network response was not ok";
        throw new Error(error);
      }
      const jsonData: ApiResponse = await response.json();
      setData(jsonData);
    } catch (err: any) {
      setError("Failed to fetch data");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    setError("");
    try {
      // First, call search_orders to refresh the data
      const searchResponse = await fetch("http://127.0.0.1:8000/search_orders");

      if (searchResponse.status === 200) {
        // If search_orders returned 200, then fetch the updated data
        const dataResponse = await fetch("http://127.0.0.1:8000/get_data");
        if (!dataResponse.ok) {
          throw new Error("Failed to get updated data");
        }
        const jsonData: ApiResponse = await dataResponse.json();
        setData(jsonData);
      } else {
        setError("Failed to fetch data");
        setData(null);
      }
    } catch (err: any) {
      setError("Failed to fetch data");
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Fetch data on component mount
    fetchData();

    // Set up interval to fetch data every 5 minutes (300,000 ms)
    const interval = setInterval(fetchData, 5 * 60 * 1000);

    // Cleanup interval on component unmount
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      className="container mt-5 bg-dark text-light min-vh-40"
      style={{ borderRadius: "10px", padding: "20px" }}
    >
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4>Status zamówień</h4>
        {data?.timestamp && (
          <small className="text">
            Ostatnia aktualizacja: {data.timestamp}
          </small>
        )}
      </div>

      <button
        className="btn btn-primary mb-3"
        onClick={handleRefresh}
        disabled={loading}
      >
        {loading ? "Ładowanie..." : "Odśwież dane"}
      </button>

      <div
        className="border rounded p-3 min-vh-10 bg-secondary text-light"
        style={{ minHeight: "215px", whiteSpace: "pre-line" }}
      >
        {loading && <div className="text-info"></div>}
        {error && <div className="text-danger">{error}</div>}
        {data ? (
          <div>
            <h5>
              Realizowane: <strong>{String(data.output_realizowane)}</strong>
            </h5>
            <h5>
              Oczekuje: <strong>{String(data.output_oczekuje)}</strong>
            </h5>
            <h5>
              Nie dodane: <strong>{String(data.output_nie_dodane)}</strong>
            </h5>
            <h5 style={{ paddingTop: "20px" }}>
              Wszystkie: <strong>{String(data.output_combined)}</strong>
            </h5>
            <h5>
              Wykonane: <strong>{String(data.output_wykonane)}</strong>
            </h5>
          </div>
        ) : (
          !error && !loading && ""
        )}
      </div>
    </div>
  );
}

export default App;
