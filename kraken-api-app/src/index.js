import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./Landing_page";

const rootElement = document.getElementById("root");
const root = createRoot(rootElement);

root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
