import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import { Toaster } from "@/components/ui/sonner";
import Layout from "@/pages/Layout";
import Home from "@/pages/Home";
import HowItWorks from "@/pages/HowItWorks";
import Upload from "@/pages/Upload";
import DatasetDetail from "@/pages/DatasetDetail";
import NotFound from "@/pages/NotFound";
import Agents from "@/pages/Agents";
import AgentProfile from "@/pages/AgentProfile";
import PurchaseRequests from "@/pages/PurchaseRequests";
import { AppBootstrap } from "@/bootstrap/app-bootstrap";

function App() {
  return (
    <>
      <AppBootstrap />
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <Layout>
                <Home />
              </Layout>
            }
          />
          <Route
            path="/how-it-works"
            element={
              <Layout>
                <HowItWorks />
              </Layout>
            }
          />
          <Route
            path="/upload"
            element={
              <Layout>
                <Upload />
              </Layout>
            }
          />
          <Route
            path="/dataset/:id"
            element={
              <Layout>
                <DatasetDetail />
              </Layout>
            }
          />
          <Route
            path="/agents"
            element={
              <Layout>
                <Agents />
              </Layout>
            }
          />
          <Route
            path="/agents/:handle"
            element={
              <Layout>
                <AgentProfile />
              </Layout>
            }
          />
          <Route
            path="/purchase-requests"
            element={
              <Layout>
                <PurchaseRequests />
              </Layout>
            }
          />
          <Route
            path="*"
            element={
              <Layout>
                <NotFound />
              </Layout>
            }
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" />
    </>
  );
}

export default App;
