import React from "react";
import ReactDOM from "react-dom/client";
import { LanguageProvider } from "@suite/i18n";
import App from "./App";
import en from "./i18n/en";
import it from "./i18n/it";
import "@suite/design-system/fonts.css";
import "./index.css";
import { fallbackVistaFetcher } from "./vistaFallback";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LanguageProvider translations={{ en, it }} defaultLanguage="it">
      <App vistaFetcher={fallbackVistaFetcher} />
    </LanguageProvider>
  </React.StrictMode>,
);
