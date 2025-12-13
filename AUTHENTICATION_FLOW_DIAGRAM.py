"""
ASCII Diagram: JWT Authentication Flow

═══════════════════════════════════════════════════════════════════════════════
                         REGISTRATION FLOW
═══════════════════════════════════════════════════════════════════════════════

┌──────────┐                                    ┌──────────┐
│  Client  │                                    │ Backend  │
│ (React)  │                                    │(FastAPI) │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /register                             │
     │  { email, password, full_name }                │
     │ ──────────────────────────────────────────────>│
     │                                                │
     │                        2. Check if user exists │
     │                        3. Hash password        │
     │                        4. Create user in DB    │
     │                        5. Generate JWT token   │
     │                                                │
     │  6. { access_token, token_type: "bearer" }     │
     │<───────────────────────────────────────────────│
     │                                                │
     │  7. Store token in localStorage                │
     │  8. Redirect to main app                       │
     │                                                │


═══════════════════════════════════════════════════════════════════════════════
                            LOGIN FLOW
═══════════════════════════════════════════════════════════════════════════════

┌──────────┐                                    ┌──────────┐
│  Client  │                                    │ Backend  │
│ (React)  │                                    │(FastAPI) │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /login                                │
     │  { email, password }                           │
     │ ──────────────────────────────────────────────>│
     │                                                │
     │                        2. Find user by email   │
     │                        3. Verify password      │
     │                        4. Check if active      │
     │                        5. Generate JWT token   │
     │                                                │
     │  6. { access_token, token_type: "bearer" }     │
     │<───────────────────────────────────────────────│
     │                                                │
     │  7. Store token in localStorage                │
     │  8. Show main app                              │
     │                                                │


═══════════════════════════════════════════════════════════════════════════════
                      PROTECTED ENDPOINT ACCESS
═══════════════════════════════════════════════════════════════════════════════

┌──────────┐                                    ┌──────────┐
│  Client  │                                    │ Backend  │
│ (React)  │                                    │(FastAPI) │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /chat (or any protected endpoint)     │
     │  Headers:                                      │
     │    Authorization: Bearer <JWT_TOKEN>           │
     │  Body: { message, chat_history, ... }          │
     │ ──────────────────────────────────────────────>│
     │                                                │
     │                        2. Extract token        │
     │                        3. Verify signature     │
     │                        4. Check expiration     │
     │                        5. Extract user email   │
     │                        6. Execute endpoint     │
     │                                                │
     │  7. Response data                              │
     │<───────────────────────────────────────────────│
     │                                                │


═══════════════════════════════════════════════════════════════════════════════
                      TOKEN EXPIRATION / 401 ERROR
═══════════════════════════════════════════════════════════════════════════════

┌──────────┐                                    ┌──────────┐
│  Client  │                                    │ Backend  │
│ (React)  │                                    │(FastAPI) │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. POST /chat                                 │
     │  Authorization: Bearer <EXPIRED_TOKEN>         │
     │ ──────────────────────────────────────────────>│
     │                                                │
     │                        2. Verify token         │
     │                        3. Token expired!       │
     │                                                │
     │  4. 401 Unauthorized                           │
     │<───────────────────────────────────────────────│
     │                                                │
     │  5. Detect 401 status                          │
     │  6. Clear token from localStorage              │
     │  7. Show login screen                          │
     │                                                │


═══════════════════════════════════════════════════════════════════════════════
                           LOGOUT FLOW
═══════════════════════════════════════════════════════════════════════════════

┌──────────┐                                    ┌──────────┐
│  Client  │                                    │ Backend  │
│ (React)  │                                    │(FastAPI) │
└────┬─────┘                                    └────┬─────┘
     │                                                │
     │  1. User clicks "Logout" button                │
     │                                                │
     │  2. Clear token from localStorage              │
     │  3. Reset app state                            │
     │  4. Show login screen                          │
     │                                                │
     │  (No backend call needed - stateless JWT)      │
     │                                                │


═══════════════════════════════════════════════════════════════════════════════
                         JWT TOKEN STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

JWT Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzAyNDg4MDAwfQ.signature

Parts:
┌─────────────────────────────────────────────────────────┐
│ Header (Base64)                                         │
│ { "alg": "HS256", "typ": "JWT" }                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Payload (Base64)                                        │
│ {                                                       │
│   "sub": "user@example.com",    # User email           │
│   "exp": 1702488000             # Expiration timestamp │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Signature (HMAC SHA256)                                 │
│ HMACSHA256(                                             │
│   base64UrlEncode(header) + "." +                      │
│   base64UrlEncode(payload),                            │
│   SECRET_KEY                                            │
│ )                                                       │
└─────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                      PASSWORD HASHING FLOW
═══════════════════════════════════════════════════════════════════════════════

Registration/Password Change:
┌─────────────────┐
│ Plain Password  │  "securepass123"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bcrypt Hash     │  Generate salt + hash
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Hashed Password │  $2b$12$LQv3c1yqBWVHxkd0LHAkCOeMxFBbF...
│ (Stored in DB)  │
└─────────────────┘

Login/Verification:
┌─────────────────┐
│ User Input      │  "securepass123"
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐   ┌──────────────┐
│ Hash it     │   │ Get hash     │
│             │   │ from DB      │
└──────┬──────┘   └──────┬───────┘
       │                 │
       └────────┬────────┘
                │
                ▼
         ┌─────────────┐
         │ Compare     │  bcrypt.verify()
         └──────┬──────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
   ┌───────┐        ┌──────┐
   │ Match │        │ Fail │
   │ ✓     │        │ ✗    │
   └───────┘        └──────┘


═══════════════════════════════════════════════════════════════════════════════
                    DATABASE SCHEMA
═══════════════════════════════════════════════════════════════════════════════

┌────────────────────────────────────────────────────────────┐
│                       users table                          │
├────────────────────────────────────────────────────────────┤
│ id               SERIAL PRIMARY KEY                        │
│ email            VARCHAR(255) UNIQUE NOT NULL              │
│ hashed_password  VARCHAR(255) NOT NULL                     │
│ full_name        VARCHAR(255)                              │
│ is_active        BOOLEAN DEFAULT TRUE                      │
│ created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP       │
│ updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP       │
├────────────────────────────────────────────────────────────┤
│ Indexes:                                                   │
│   idx_users_email ON (email)                              │
├────────────────────────────────────────────────────────────┤
│ Triggers:                                                  │
│   update_users_updated_at (updates updated_at on change)  │
└────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
                      COMPONENT HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

App.tsx (Root)
│
├─ State: token, setToken
├─ useEffect: Check localStorage for token
│
├─ If no token:
│  └─> Auth.tsx
│      ├─ Login form
│      ├─ Register form
│      └─ onLogin(token) → setToken → localStorage
│
└─ If token exists:
   └─> Chat.tsx (props: token, onLogout)
       ├─ All API calls include: Authorization: Bearer {token}
       ├─ 401 errors trigger: onLogout()
       │
       ├─> FileList.tsx (props: token)
       │   └─ API calls with Authorization header
       │
       ├─> UploadModal.tsx (props: token)
       │   └─ Upload with Authorization header
       │
       ├─> SettingsModal.tsx
       └─> HtmlPreviewModal.tsx


═══════════════════════════════════════════════════════════════════════════════
"""
