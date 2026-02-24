import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import Monitor from "./pages/Monitor";
import Backtest from "./pages/Backtest";
import Config from "./pages/Config";
import Doc from "./pages/Doc";
import "./App.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 10_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Monitor />} />
            <Route path="backtest" element={<Backtest />} />
            <Route path="config" element={<Config />} />
            <Route path="doc" element={<Doc />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
