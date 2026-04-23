import type { Configuration, PopupRequest } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "",
    authority: import.meta.env.VITE_AZURE_AUTHORITY || "",
    redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI || "http://localhost:3000",
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

export const loginRequest: PopupRequest = {
  scopes: [import.meta.env.VITE_API_SCOPE || "User.Read"],
};
