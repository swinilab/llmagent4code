import jwt from 'jsonwebtoken';

export function authGuard(req, res, next) {
  const token = req.cookies.auth_token;
  
  if (!token) {
    return res.redirect('/login');
  }
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    res.clearCookie('auth_token');
    return res.redirect('/login');
  }
}

export function optionalAuth(req, res, next) {
  const token = req.cookies.auth_token;
  
  if (token) {
    try {
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      req.user = decoded;
    } catch (err) {
      // Silently ignore invalid token
    }
  }
  next();
}
