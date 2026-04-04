const express = require("express");
const http = require("http");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const MENTRA_TARGET = "http://localhost:3001";
const DASHBOARD_WS_TARGET = "ws://localhost:3001";
const API_TARGET = "http://localhost:8000/api";
const FRONTEND_TARGET = "http://localhost:3000";

app.use((req, _res, next) => {
  console.log(`[gateway] ${req.method} ${req.originalUrl}`);
  next();
});

// mentra backend
const mentraProxy = createProxyMiddleware({
  target: MENTRA_TARGET,
  changeOrigin: true,
  pathRewrite: { "^/mentra": "" },
  on: {
    proxyReq: (proxyReq, req) => {
      console.log(
        `[gateway] -> mentra http ${req.method} ${req.originalUrl} => ${MENTRA_TARGET}${proxyReq.path}`
      );
    },
    proxyReqWs: (_proxyReq, req) => {
      console.log(`[gateway] -> mentra ws ${req.url} => ${MENTRA_TARGET}${req.url}`);
    },
  },
});
app.use("/mentra", mentraProxy);

const dashboardWsProxy = createProxyMiddleware({
  target: DASHBOARD_WS_TARGET,
  changeOrigin: true,
  ws: true,
  on: {
    proxyReqWs: (_proxyReq, req) => {
      console.log(`[gateway] -> dashboard ws ${req.url} => ${DASHBOARD_WS_TARGET}${req.url}`);
    },
  },
});

// Backend API
app.use(
  "/api",
  createProxyMiddleware({
    target: API_TARGET,
    changeOrigin: true,
    on: {
      proxyReq: (proxyReq, req) => {
        console.log(`[gateway] -> api http ${req.method} ${req.originalUrl} => ${API_TARGET}${proxyReq.path}`);
      },
    },
  })
);

// frontend
const frontendProxy = createProxyMiddleware({
  target: FRONTEND_TARGET,
  changeOrigin: true,
  ws: true,
  on: {
    proxyReq: (proxyReq, req) => {
      console.log(
        `[gateway] -> frontend http ${req.method} ${req.originalUrl} => ${FRONTEND_TARGET}${proxyReq.path}`
      );
    },
    proxyReqWs: (_proxyReq, req) => {
      console.log(`[gateway] -> frontend ws ${req.url} => ${FRONTEND_TARGET}${req.url}`);
    },
  },
});
app.use("/", frontendProxy);

const server = http.createServer(app);
server.on("upgrade", (req, socket, head) => {
  const pathname = req.url ? req.url.split("?")[0] : "";
  if (pathname.startsWith("/ws")) {
    dashboardWsProxy.upgrade(req, socket, head);
    return;
  }
  if (pathname.startsWith("/mentra")) {
    mentraProxy.upgrade(req, socket, head);
    return;
  }
  frontendProxy.upgrade(req, socket, head);
});

server.listen(3002, () => {
  console.log("Gateway running on port 3002");
});
