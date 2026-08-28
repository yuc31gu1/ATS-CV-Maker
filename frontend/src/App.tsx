import { Route, Routes } from "react-router-dom";
import { ConnectivityPage } from "./pages/ConnectivityPage";
import { JobAnalysisPage } from "./pages/JobAnalysisPage";
import { ResumeEditorPage } from "./pages/ResumeEditorPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ConnectivityPage />} />
      <Route path="/resume" element={<ResumeEditorPage />} />
      <Route path="/create/job-analysis" element={<JobAnalysisPage />} />
    </Routes>
  );
}