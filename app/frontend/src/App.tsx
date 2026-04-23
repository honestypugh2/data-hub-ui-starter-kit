import React from "react";
import {
  AuthenticatedTemplate,
  UnauthenticatedTemplate,
  useMsal,
} from "@azure/msal-react";
import { loginRequest } from "./services/auth";
import UploadPage from "./components/Upload/UploadPage";
import ImageGallery from "./components/ImageGallery/ImageGallery";

const App: React.FC = () => {
  const { instance, accounts } = useMsal();
  const account = accounts[0];

  const handleLogin = () => {
    instance.loginPopup(loginRequest).catch(console.error);
  };

  const handleLogout = () => {
    instance.logoutPopup().catch(console.error);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Starter Kit UI</h1>
        <AuthenticatedTemplate>
          <div className="user-info">
            <span>{account?.name ?? account?.username}</span>
            <button className="btn btn-secondary" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
        </AuthenticatedTemplate>
      </header>

      <main className="app-main">
        <UnauthenticatedTemplate>
          <div className="login-prompt">
            <h2>Sign in to get started</h2>
            <p>Use your organization credentials to upload and process images.</p>
            <button className="btn btn-primary" onClick={handleLogin}>
              Sign in with Microsoft
            </button>
          </div>
        </UnauthenticatedTemplate>

        <AuthenticatedTemplate>
          <UploadPage />
          <ImageGallery />
        </AuthenticatedTemplate>
      </main>
    </div>
  );
};

export default App;
