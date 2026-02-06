const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5059',
      changeOrigin: true,
      // Keep the /api prefix when forwarding to backend
      // Default behavior strips the matched prefix, so we need to add it back
      pathRewrite: function (path, req) {
        // path will be /login (after /api is stripped)
        // We want to keep it as /api/login
        return '/api' + path;
      },
      logLevel: 'debug'
    })
  );
};
