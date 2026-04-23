import React, { useState } from "react";
import DemoUploadPage from "./components/Upload/DemoUploadPage";
import DemoImageGallery from "./components/ImageGallery/DemoImageGallery";
import "./App.css";

const DEMO_USER = {
  name: "Demo User",
  email: "demo.user@example.org",
};

const DemoApp: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>Starter Kit UI (DEMO)</h1>
        {isAuthenticated && (
          <div className="user-info">
            <span>{DEMO_USER.name}</span>
            <span className="demo-badge">Demo Mode</span>
            <button className="btn btn-secondary" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
        )}
      </header>

      <main className="app-main">
        {!isAuthenticated ? (
          <div className="login-prompt">
            <h2>Sign in to get started</h2>
            <p>Use your organization credentials to upload and process images.</p>
            <button className="btn btn-primary" onClick={handleLogin}>
              Sign in with Email
            </button>
          </div>
        ) : (
          <>
            <DemoUploadPage />
            <DemoImageGallery />
          </>
        )}
      </main>
    </div>
  );
};

export default DemoApp;
