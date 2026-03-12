import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";
import { Toaster } from "@/components/ui/sonner";
import Layout from "@/pages/Layout";
import Home from "@/pages/Home";
import HowItWorks from "@/pages/HowItWorks";
import Upload from "@/pages/Upload";
import DatasetDetail from "@/pages/DatasetDetail";
import NotFound from "@/pages/NotFound";
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
