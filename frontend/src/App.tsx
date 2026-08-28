import { Route, Routes } from "react-router-dom";
import { ConnectivityPage } from "./pages/ConnectivityPage";
import { JobAnalysisPage } from "./pages/JobAnalysisPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ConnectivityPage />} />
      <Route path="/create/job-analysis" element={<JobAnalysisPage />} />
    </Routes>
  );
}