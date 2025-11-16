/**
 * ENDPOINT VALIDATOR MIDDLEWARE
 * Reduces 404s by validating requests and providing helpful error messages
 */

const validEndpoints = {
  'GET': [
    '/health',
    '/api/analytics',
    '/api/users/:userId',
    '/api/check-ins/:userId',
    '/api/journals/:userId',
    '/api/insights/:userId'
  ],
  'POST': [
    '/api/users',
    '/api/check-ins',
    '/api/details',
    '/api/journals/generate',
    '/api/insights/generate',
    '/api/conversion/calculate',
    '/api/conversion/offer',
    '/api/onboarding/flow',
    '/api/value-proposition'
  ]
};

function validateEndpoint(req, res, next) {
  const method = req.method;
  const path = req.path;
  
  // Check if endpoint exists
  const validPaths = validEndpoints[method] || [];
  const pathExists = validPaths.some(validPath => {
    if (validPath.includes(':')) {
      // Handle parameterized routes
      const pattern = validPath.replace(/:[^/]+/g, '[^/]+');
      const regex = new RegExp(`^${pattern}$`);
      return regex.test(path);
    }
    return path === validPath;
  });
  
  if (!pathExists) {
    return res.status(404).json({
      error: 'Endpoint not found',
      path: path,
      method: method,
      availableEndpoints: validEndpoints[method] || [],
      suggestion: getSuggestion(path, validPaths)
    });
  }
  
  next();
}

function getSuggestion(path, validPaths) {
  // Find the closest matching endpoint
  const suggestions = validPaths.filter(validPath => {
    const pathParts = path.split('/');
    const validParts = validPath.split('/');
    
    if (pathParts.length !== validParts.length) return false;
    
    let matches = 0;
    for (let i = 0; i < pathParts.length; i++) {
      if (validParts[i].startsWith(':') || pathParts[i] === validParts[i]) {
        matches++;
      }
    }
    
    return matches >= pathParts.length - 1;
  });
  
  return suggestions.length > 0 ? `Did you mean: ${suggestions[0]}?` : 'Check the API documentation';
}

module.exports = { validateEndpoint };
