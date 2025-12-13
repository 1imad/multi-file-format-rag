# Quick Start Guide - JWT Authentication

## ⚡ Fast Setup (3 Steps)

### Step 1: Backend Setup
```bash
# Install dependencies (already done ✅)
pip install 'python-jose[cryptography]' 'passlib[bcrypt]'

# Database already has users table ✅
# SECRET_KEY already added to .env ✅
```

### Step 2: Start Backend
```bash
python app.py
```

### Step 3: Start Frontend
```bash
cd client
npm run dev
```

## 🎯 First Use

1. Open http://localhost:5173
2. Click "Register" 
3. Enter:
   - Email: your@email.com
   - Password: (your password)
   - Name: (optional)
4. Click "Register" button
5. You're in! 🎉

## 🔑 Key Features

### What's Protected Now:
- ✅ Upload documents
- ✅ Chat with AI
- ✅ Query documents
- ✅ View files
- ✅ Delete files

### What's Still Public:
- ✅ Health check
- ✅ View available prompts
- ✅ Register new account
- ✅ Login

## 🧪 Quick Test

```bash
# Test authentication (backend must be running)
python test_auth.py
```

Expected output:
```
🔐 Testing JWT Authentication Setup

1️⃣ Testing user registration...
   ✅ Registration successful!
   
2️⃣ Testing user login...
   ✅ Login successful!
   
3️⃣ Testing protected endpoint without token...
   ✅ Correctly rejected
   
4️⃣ Testing protected endpoint with token...
   ✅ Access granted!
   
5️⃣ Testing public endpoint (/prompts)...
   ✅ Public endpoint accessible

✨ Authentication test complete!
```

## 📱 Using the API

### Register
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "full_name": "John Doe"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Login
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123"
  }'
```

### Use Protected Endpoint
```bash
TOKEN="your_jwt_token_here"

curl -X GET http://localhost:8000/files \
  -H "Authorization: Bearer $TOKEN"
```

## 🛠️ Troubleshooting

**Problem:** Can't login
- ✅ Check email and password are correct
- ✅ Verify backend is running on port 8000
- ✅ Check database is running

**Problem:** "Could not validate credentials"
- ✅ Token may have expired (30 min expiration)
- ✅ Try logging in again
- ✅ Check Authorization header format

**Problem:** Frontend won't connect
- ✅ Check backend is running: `curl http://localhost:8000/health`
- ✅ Verify CORS settings in app.py
- ✅ Check browser console for errors

**Problem:** Database errors
- ✅ Run: `PGPASSWORD=123456789 psql -h localhost -U imad -d embeddings -f init_db.sql`
- ✅ Verify PostgreSQL is running
- ✅ Check .env database credentials

## 🎨 UI Features

### Login/Register Screen
- Modern gradient background
- Toggle between login and register
- Form validation
- Error messages
- Auto-redirect on success

### Main App
- Logout button in top-right
- Token persists across refreshes
- Auto-authentication on reload
- Smooth transitions

## 📖 More Info

- Full setup guide: `AUTH_SETUP.md`
- Complete summary: `JWT_AUTH_SUMMARY.md`
- Test script: `test_auth.py`

## 💡 Tips

1. **First user?** Just click "Register" and create an account
2. **Token expired?** Click "Logout" and login again
3. **Testing API?** Use the test script: `python test_auth.py`
4. **Lost password?** Delete user from database and re-register (no reset yet)

## ⏱️ Token Info

- **Expiration:** 30 minutes
- **Storage:** Browser localStorage
- **Type:** JWT (JSON Web Token)
- **Algorithm:** HS256

Change expiration time in `utils/auth.py`:
```python
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Change this
```

---

**That's it! You're ready to go! 🚀**
