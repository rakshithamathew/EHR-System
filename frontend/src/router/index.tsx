import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { EpicCallbackPage } from "../pages/EpicCallbackPage";
import { PatientDetailsPage } from "../pages/PatientDetailsPage";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      {
        path: "/",
        element: <DashboardPage />,
      },
      {
        path: "/dashboard",
        element: <DashboardPage />,
      },
      {
        path: "/patients/:patientId",
        element: <PatientDetailsPage />,
      },
      {
        path: "/callback",
        element: <EpicCallbackPage />,
      },
    ],
  },
]);
