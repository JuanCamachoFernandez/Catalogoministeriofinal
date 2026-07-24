import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./AuthContext";
import { ErrorBoundary } from "./ErrorBoundary";
import "./styles/theme.css";
import "./index.css";
import "./styles/public.css";
import "./styles/auth.css";
import "./styles/admin.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, gcTime: 30 * 60_000, refetchOnWindowFocus: false, retry: 1 } } });
createRoot(document.getElementById("root")!).render(<React.StrictMode><ErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter><AuthProvider><App/></AuthProvider></BrowserRouter></QueryClientProvider></ErrorBoundary></React.StrictMode>);
