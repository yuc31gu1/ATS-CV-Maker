import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { JobAnalysisPage } from "./pages/JobAnalysisPage";
import { MatchPage } from "./pages/MatchPage";
import { ResultPage } from "./pages/ResultPage";
import { ResumeEditorPage } from "./pages/ResumeEditorPage";
import { ReviewPage } from "./pages/ReviewPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/resume" element={<ResumeEditorPage />} />
      <Route path="/create" element={<Navigate to="/create/job-analysis" replace />} />
      <Route path="/create/job-analysis" element={<JobAnalysisPage />} />
      <Route path="/create/match" element={<MatchPage />} />
      <Route path="/create/review" element={<ReviewPage />} />
      <Route path="/create/result" element={<ResultPage />} />
      <Route path="/history" element={<HistoryPage />} />
    </Routes>
  );
}