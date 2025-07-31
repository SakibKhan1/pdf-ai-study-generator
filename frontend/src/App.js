import React from 'react';

function App() {
  return (
    <div style={{
      height: "100vh",
      backgroundColor: "#111",
      color: "#fff",
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      fontFamily: "Arial, sans-serif",
      textAlign: "center",
      padding: "2rem"
    }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>🚧 Site Temporarily Offline</h1>
      <p style={{ fontSize: "1.2rem", maxWidth: "500px" }}>
        Currently working on some improvements to fix security concerns. Please check back soon!
      </p>
    </div>
  );
}

export default App;
