const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();

// mentra backend
app.use(
  "/mentra",
  createProxyMiddleware({
    target: "http://localhost:3001",
    changeOrigin: true,
    pathRewrite: { "^/mentra": "" },
  })
);

// Backend API
app.use(
  "/api",
  createProxyMiddleware({
    target: "http://localhost:8000/api",
    changeOrigin: true,
  })
);

// frontend
app.use(
  "/",
  createProxyMiddleware({
    target: "http://localhost:3000",
    changeOrigin: true,
  })
);

app.listen(3002, () => {
  console.log("Gateway running on port 3002");
});