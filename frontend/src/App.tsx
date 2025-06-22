import { useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./App.css";

type ApiResponse = {
  output_realizowane: string;
  output_oczekuje: string;
  output_combined: string;
  output_nie_dodane: string;
};

function App() {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleClick = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        "https://adam-search-860977612313.europe-central2.run.app/search_orders"
      );
      if (!response.ok) {
        let error = "Network response was not ok";
        throw new Error(error);
        setError(error);
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

  return (
    <div
      className="container mt-5 bg-dark text-light min-vh-40"
      style={{ borderRadius: "10px", padding: "20px" }}
    >
      <button
        className="btn btn-primary mb-3"
        onClick={handleClick}
        disabled={loading}
      >
        {loading ? "Ładowanie..." : "Wyszukaj"}
      </button>
      <div
        className="border rounded p-3 min-vh-10 bg-secondary text-light"
        style={{ minHeight: "50px", whiteSpace: "pre-line" }}
      >
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
          </div>
        ) : (
          !error && ""
        )}
      </div>
    </div>
  );
}

export default App;
