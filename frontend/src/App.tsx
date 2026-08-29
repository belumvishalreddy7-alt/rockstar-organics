import { useEffect } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { SiteHeader } from "./components/SiteHeader";
import { SiteFooter } from "./components/SiteFooter";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Home } from "./pages/public/Home";
import { Catalogue } from "./pages/public/Catalogue";
import { ProductDetail } from "./pages/public/ProductDetail";
import { DealerDirectory } from "./pages/public/DealerDirectory";
import { FarmerSupportInfo } from "./pages/public/FarmerSupportInfo";
import { DealerProgramme } from "./pages/public/DealerProgramme";
import { Distributors } from "./pages/public/Distributors";
import { Certificates } from "./pages/public/Certificates";
import { Gallery } from "./pages/public/Gallery";
import { Knowledge, KnowledgeDetail } from "./pages/public/Knowledge";
import { Announcements, AnnouncementDetail } from "./pages/public/Announcements";
import { About, Contact, PrivacyPolicy, Terms, Disclaimer, CookieNotice, NotFound, Forbidden, ServerError } from "./pages/public/StaticPages";
import { Leadership, Manufacturing, ResearchAndDevelopment, QualityAndSafety, Sustainability, FarmerStories, Careers } from "./pages/public/CorporatePages";
import { useRouteTitle } from "./hooks/useRouteTitle";
import { Login, Register, ForgotPassword, ResetPassword } from "./pages/public/Auth";
import { Signup } from "./pages/public/Signup";
import { ChangePassword } from "./pages/public/ChangePassword";
import { FarmerDashboardLayout, FarmerCaseList, FarmerVisitList } from "./pages/farmer/FarmerDashboard";
import { NewCase } from "./pages/farmer/NewCase";
import { CaseDetail } from "./pages/farmer/CaseDetail";
import { FarmerProfile } from "./pages/farmer/FarmerProfile";
import { DealerDashboard } from "./pages/dealer/DealerDashboard";
import { DistributorDashboard } from "./pages/distributor/DistributorDashboard";
import { StaffDashboardLayout } from "./pages/staff/StaffDashboard";
import { ProductManagement } from "./pages/staff/ProductManagement";
import { DealerApplications } from "./pages/staff/DealerApplications";
import { DistributorApplications } from "./pages/staff/DistributorApplications";
import { CompanyDocuments } from "./pages/staff/CompanyDocuments";
import { AgriculturePhotos } from "./pages/staff/AgriculturePhotos";
import { CaseQueue } from "./pages/staff/CaseQueue";
import { ReviewModeration } from "./pages/staff/ReviewModeration";
import { AnnouncementManagement } from "./pages/staff/AnnouncementManagement";
import { KnowledgeManagement } from "./pages/staff/KnowledgeManagement";
import { TaskBoard } from "./pages/staff/TaskBoard";
import { EnquiryQueue } from "./pages/staff/EnquiryQueue";
import { AccountManagement } from "./pages/staff/AccountManagement";
import { MyVisits } from "./pages/staff/MyVisits";

const STAFF_ROLES = ["super_admin", "admin", "content_manager", "sales_manager", "field_officer"];

/** Forces anyone signed in with a temporary/must-change password to the
 * change-password screen before they can reach anything else - closes the
 * gap where a dealer/staff account created with a temp password could
 * simply skip changing it and keep using the temporary credential. */
function ForcedPasswordChangeGate() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user?.must_change_password && location.pathname !== "/change-password") {
      navigate("/change-password", { replace: true });
    }
  }, [loading, user, location.pathname, navigate]);

  return null;
}

export default function App() {
  useRouteTitle();
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <SiteHeader />
      <ForcedPasswordChangeGate />
      <main id="main-content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Catalogue />} />
          <Route path="/products/:slug" element={<ProductDetail />} />
          <Route path="/dealers" element={<DealerDirectory />} />
          <Route path="/farmer-support" element={<FarmerSupportInfo />} />
          <Route path="/dealer-programme" element={<DealerProgramme />} />
          <Route path="/distributors" element={<Distributors />} />
          <Route path="/certificates" element={<Certificates />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/knowledge/:slug" element={<KnowledgeDetail />} />
          <Route path="/announcements" element={<Announcements />} />
          <Route path="/announcements/:slug" element={<AnnouncementDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/leadership" element={<Leadership />} />
          <Route path="/manufacturing" element={<Manufacturing />} />
          <Route path="/research-and-development" element={<ResearchAndDevelopment />} />
          <Route path="/quality-and-safety" element={<QualityAndSafety />} />
          <Route path="/sustainability" element={<Sustainability />} />
          <Route path="/farmer-stories" element={<FarmerStories />} />
          <Route path="/careers" element={<Careers />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/legal/privacy" element={<PrivacyPolicy />} />
          <Route path="/legal/terms" element={<Terms />} />
          <Route path="/legal/disclaimer" element={<Disclaimer />} />
          <Route path="/legal/cookies" element={<CookieNotice />} />

          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/change-password" element={<ChangePassword />} />

          <Route
            path="/farmer"
            element={
              <ProtectedRoute roles={["farmer"]}>
                <FarmerDashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<FarmerCaseList />} />
            <Route path="visits" element={<FarmerVisitList />} />
            <Route path="cases/new" element={<NewCase />} />
            <Route path="profile" element={<FarmerProfile />} />
            <Route path="cases/:caseId" element={<CaseDetail />} />
          </Route>

          <Route
            path="/dealer"
            element={
              <ProtectedRoute roles={["dealer"]}>
                <DealerDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/distributor"
            element={
              <ProtectedRoute roles={["distributor"]}>
                <DistributorDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/staff"
            element={
              <ProtectedRoute roles={STAFF_ROLES}>
                <StaffDashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route path="products" element={<ProductManagement />} />
            <Route path="dealer-applications" element={<DealerApplications />} />
            <Route path="distributor-applications" element={<DistributorApplications />} />
            <Route path="documents" element={<CompanyDocuments />} />
            <Route path="gallery" element={<AgriculturePhotos />} />
            <Route path="cases" element={<CaseQueue />} />
            <Route path="reviews" element={<ReviewModeration />} />
            <Route path="announcements" element={<AnnouncementManagement />} />
            <Route path="knowledge" element={<KnowledgeManagement />} />
            <Route path="tasks" element={<TaskBoard />} />
            <Route path="enquiries" element={<EnquiryQueue />} />
            <Route path="accounts" element={<AccountManagement />} />
            <Route path="my-visits" element={<MyVisits />} />
          </Route>

          <Route path="/403" element={<Forbidden />} />
          <Route path="/500" element={<ServerError />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <SiteFooter />
    </>
  );
}
