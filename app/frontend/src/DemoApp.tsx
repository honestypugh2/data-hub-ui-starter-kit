import React from "react";
import DemoUploadPage from "./components/Upload/DemoUploadPage";
import DemoImageGallery from "./components/ImageGallery/DemoImageGallery";
import "./App.css";

const DemoApp: React.FC = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Starter Kit UI (DEMO)</h1>
        <div className="user-info">
          <span>demo.user@example.org</span>
          <span className="demo-badge">Demo Mode</span>
        </div>
      </header>

      <main className="app-main">
        <DemoUploadPage />
        <DemoImageGallery />
      </main>
    </div>
  );
};

export default DemoApp;
