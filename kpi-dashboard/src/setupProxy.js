const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://127.0.0.1:5059',
      // Keep Host as the frontend origin so session cookie is set for localhost (same origin as the app)
      changeOrigin: false,
      // path: when mounted at /api, request to /api/accounts gives path /accounts; backend expects /api/accounts
      pathRewrite: function (path, req) {
        return path.startsWith('/api') ? path : '/api' + path;
      },
      logLevel: 'warn',
      cookieDomainRewrite: '', // leave cookie domain as-is so browser keeps it for current host (localhost)
    })
  );
};
