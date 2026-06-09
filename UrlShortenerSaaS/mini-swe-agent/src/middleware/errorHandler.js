export function errorHandler(err, req, res, next) {
  console.error('Error:', err);
  
  if (res.headersSent) {
    return next(err);
  }
  
  const isApiRoute = req.path.startsWith('/api');
  
  if (isApiRoute) {
    return res.status(500).json({
      error: {
        code: 'INTERNAL_SERVER_ERROR',
        message: 'An internal server error occurred'
      }
    });
  }
  
  res.status(500).render('error', {
    error: process.env.NODE_ENV === 'production' ? 'An error occurred' : err.message
  });
}
