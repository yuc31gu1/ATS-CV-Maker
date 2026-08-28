import { Route, Routes } from "react-router-dom";
import { ConnectivityPage } from "./pages/ConnectivityPage";
import { JobAnalysisPage } from "./pages/JobAnalysisPage";
import { MatchPage } from "./pages/MatchPage";
import { ResumeEditorPage } from "./pages/ResumeEditorPage";
import { ReviewPage } from "./pages/ReviewPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ConnectivityPage />} />
      <Route path="/resume" element={<ResumeEditorPage />} />
      <Route path="/create/job-analysis" element={<JobAnalysisPage />} />
      <Route path="/create/match" element={<MatchPage />} />
      <Route path="/create/review" element={<ReviewPage />} />
    </Routes>
  );
}