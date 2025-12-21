# Session Null User ID Fix

## Problem

The frontend was making requests to the user API with `null` as a string literal in the URL path:

```
GET https://smmc-io-prod.timesmart.io/user-management-service/user/null
404 Not Found
```

This indicated that the user's session was not properly maintaining the user ID, causing the frontend to pass "null" instead of an actual user ID.

## Root Cause

The session likely became invalid or expired, or the user ID was never properly stored in the session/localStorage. This could occur due to:

1. **Session Expiration**: JWT token or session expires without proper refresh
2. **Session Storage Cleared**: Browser cache/localStorage was cleared
3. **Login Not Completed**: User reached the page before authentication completed
4. **Session Timeout**: Idle timeout cleared the user context
5. **Frontend Bug**: Missing null check before constructing API URLs

## Solution Implemented

### Backend Changes (UserController.py)

Added validation for null/empty user ID parameters across all endpoints that require a user ID:

1. **`GET /{userId}`** - Get user by ID
2. **`GET /{id}/notify`** - Notify user
3. **`GET /{id}/remindContractors`** - Remind contractors
4. **`PUT /{id}/{action}`** - Block/Deactivate user
5. **`GET /{userId}/accessScope`** - Get user access scope

Each endpoint now validates the user ID parameter and returns a **400 Bad Request** error instead of 404:

```python
# Validate userId parameter
if not userId or userId.strip() == "" or userId.lower() == "null":
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="User ID is required and cannot be null or empty. Please ensure you are logged in and have an active session."
    )
```

### Benefits

1. **Better Error Messages**: Users receive a clear message to check their login status
2. **Consistent Status Codes**: 400 Bad Request (client error) instead of 404 (not found)
3. **Session Debugging**: Error message guides users to verify their session is active
4. **Security**: Prevents potential issues with passing "null" to service layer

## Frontend Recommendations

To prevent this issue in the future, the frontend should:

### 1. **Verify User ID Before API Calls**

```javascript
// In your API service
async function getUser(userId) {
  // Validate userId exists
  if (!userId || userId === 'null' || userId === null) {
    // Redirect to login or show error
    window.location.href = '/login';
    throw new Error('Session expired: User ID not found');
  }
  
  const response = await fetch(`/user-management-service/user/${userId}`, {
    headers: {
      'X-tenantID': getTenantId(),
      'Authorization': getAuthToken()
    }
  });
  
  return response.json();
}
```

### 2. **Implement Session Refresh Logic**

```javascript
// Check if session is valid
async function refreshSession() {
  try {
    const response = await fetch('/user-management-service/user/current', {
      headers: {
        'Authorization': getAuthToken(),
        'X-tenantID': getTenantId()
      }
    });
    
    if (!response.ok) {
      // Session invalid, redirect to login
      window.location.href = '/login';
      return false;
    }
    
    const user = await response.json();
    
    // Update stored user ID
    localStorage.setItem('userId', user.id);
    return true;
  } catch (error) {
    console.error('Session refresh failed:', error);
    window.location.href = '/login';
    return false;
  }
}
```

### 3. **Add Session Guards to Routes**

```javascript
// Before accessing any user page
async function ensureSessionValid() {
  const storedUserId = localStorage.getItem('userId');
  
  if (!storedUserId || storedUserId === 'null') {
    const isValid = await refreshSession();
    if (!isValid) {
      throw new Error('User session is invalid');
    }
  }
}

// In component/page mount
React.useEffect(() => {
  ensureSessionValid().catch(() => {
    // Show error message and redirect
  });
}, []);
```

### 4. **Handle Authentication Errors**

```javascript
// Axios interceptor or fetch wrapper
async function apiCall(url, options = {}) {
  const response = await fetch(url, options);
  
  if (response.status === 401) {
    // Unauthorized - session expired
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  
  if (response.status === 400) {
    const error = await response.json();
    if (error.detail && error.detail.includes('User ID')) {
      // Missing or invalid user ID
      localStorage.removeItem('userId');
      window.location.href = '/login';
    }
  }
  
  return response;
}
```

### 5. **Store User ID Safely**

```javascript
// After successful login
async function handleLoginSuccess(loginResponse) {
  // Store credentials securely
  sessionStorage.setItem('authToken', loginResponse.token);
  sessionStorage.setItem('userId', loginResponse.user.id);
  sessionStorage.setItem('tenantId', loginResponse.user.tenantId);
  
  // Optionally use localStorage for "remember me"
  if (rememberMe) {
    localStorage.setItem('userId', loginResponse.user.id);
  }
}

// Clear on logout
function handleLogout() {
  sessionStorage.clear();
  localStorage.removeItem('userId');
  window.location.href = '/login';
}
```

## Testing

### Manual Testing

1. **Test Normal Flow**:
   ```bash
   curl -X GET "http://localhost:8000/user/6424dea81a6c0d4b84d543a9" \
     -H "X-tenantID: 64246d491b70b07241d37aa1" \
     -H "Authorization: Bearer <token>"
   # Should return 200 with user data
   ```

2. **Test Null User ID**:
   ```bash
   curl -X GET "http://localhost:8000/user/null" \
     -H "X-tenantID: 64246d491b70b07241d37aa1" \
     -H "Authorization: Bearer <token>"
   # Should return 400 with error message:
   # "User ID is required and cannot be null or empty..."
   ```

3. **Test Empty User ID**:
   ```bash
   curl -X GET "http://localhost:8000/user/" \
     -H "X-tenantID: 64246d491b70b07241d37aa1" \
     -H "Authorization: Bearer <token>"
   # Should return 400 with error message
   ```

## Files Modified

- `app/api/endpoints/UserController.py`
  - Added null/empty validation to 5 endpoints
  - Returns 400 Bad Request with helpful error message

## Monitoring

Monitor these metrics to identify session issues:

1. **Bad Request Errors (400)** related to null user IDs
2. **Session Expiration Rate**: How often sessions become invalid
3. **Login Success Rate**: Are users staying logged in?
4. **Frontend Console Errors**: Any errors before API calls

## Future Improvements

1. **Implement JWT Refresh Tokens**: Automatically refresh expiring tokens
2. **Add Session Timeout Warnings**: Warn users before session expires
3. **Persistent Sessions**: Use secure cookies instead of localStorage
4. **Session Sync**: Sync session state across browser tabs
5. **Logout on Tab Close**: Prevent orphaned sessions

---

**Status**: ✅ Fixed  
**Date**: 2025-12-21  
**Components Affected**: UserController endpoints  
**Impact**: Better error handling and user guidance for session issues
