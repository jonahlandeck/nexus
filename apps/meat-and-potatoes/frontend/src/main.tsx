import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";

import "@picocss/pico/css/pico.min.css";
import "./styles.css";

import App from "./App";
import Intake from "./pages/Intake";
import Profile from "./pages/Profile";
import PlanPage from "./pages/Plan";
import Grocery from "./pages/Grocery";
import Pantry from "./pages/Pantry";

const qc = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <App />,
      children: [
        { index: true, element: <Navigate to="/intake" replace /> },
        { path: "intake", element: <Intake /> },
        { path: "profile", element: <Profile /> },
        { path: "plan", element: <PlanPage /> },
        { path: "grocery", element: <Grocery /> },
        { path: "pantry", element: <Pantry /> },
      ],
    },
  ],
  // Matches the Vite `--base` used for the build; "/" for local dev.
  { basename: import.meta.env.BASE_URL.replace(/\/$/, "") || "/" },
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
