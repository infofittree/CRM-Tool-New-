import { Routes, Route, Navigate } from "react-router-dom";
import { ProtectedRoute, RoleGuard } from "@/lib/auth";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import LeadManagement from "@/pages/LeadManagement";
import LeadDetail from "@/pages/LeadDetail";
import Tasks from "@/pages/Tasks";
import DataEntry from "@/pages/DataEntry";
import Analytics from "@/pages/Analytics";
import Team from "@/pages/Team";
import InquiryPortal from "@/pages/InquiryPortal";
import WeeklyReview from "@/pages/WeeklyReview";
import Settings from "@/pages/Settings";
import AppShell from "@/components/layout/AppShell";
import { SalespersonProvider } from "@/lib/salespersonContext";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <SalespersonProvider>
              <AppShell />
            </SalespersonProvider>
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/leads" element={<LeadManagement />} />
        <Route path="/leads/:id" element={<LeadDetail />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/team" element={<RoleGuard roles={["Admin", "Manager"]}><Team /></RoleGuard>} />
        <Route path="/weekly-review" element={<WeeklyReview />} />
        <Route path="/data-entry" element={<DataEntry />} />
        <Route path="/inquiries" element={<InquiryPortal />} />
        <Route path="/settings" element={<RoleGuard roles={["Admin"]}><Settings /></RoleGuard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
