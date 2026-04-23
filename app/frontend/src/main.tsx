import React from "react";
import ReactDOM from "react-dom/client";

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);

if (DEMO_MODE) {
  // Demo mode — no MSAL, no Azure dependencies
  import("./DemoApp").then(({ default: DemoApp }) => {
    root.render(
      <React.StrictMode>
        <DemoApp />
      </React.StrictMode>
    );
  });
} else {
  // Production mode — full MSAL auth
  import("@azure/msal-browser").then(({ PublicClientApplication }) =>
    import("@azure/msal-react").then(({ MsalProvider }) =>
      import("./services/auth").then(({ msalConfig }) =>
        import("./App").then(({ default: App }) => {
          const msalInstance = new PublicClientApplication(msalConfig);
          root.render(
            <React.StrictMode>
              <MsalProvider instance={msalInstance}>
                <App />
              </MsalProvider>
            </React.StrictMode>
          );
        })
      )
    )
  );
}
