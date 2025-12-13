# JWT Authentication Setup

## Overview
This application now includes JWT-based authentication to secure all API endpoints. Users must register and login to access the RAG chat functionality.

## Backend Changes

### 1. Database Setup
A new `users` table has been added to PostgreSQL. Run the SQL script to create it:

```bash
psql -h $PGHOST -U $PGUSER -d $PGDATABASE -f init_db.sql
```

Or connect to your database and run:
```sql
-- See init_db.sql for the complete schema
```

### 2. Environment Variables
Add a secret key to your `.env` file:

```env
SECRET_KEY=your-super-secret-key-change-this-in-production
```

Generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Install Dependencies
Install the new Python packages:

```bash
pip install -r requirements.txt
```

New dependencies added:
- `python-jose[cryptography]` - JWT token handling
- `passlib[bcrypt]` - Password hashing

### 4. Protected Endpoints
The following endpoints now require authentication:
- `POST /upload` - Upload documents
- `GET /query` - Query documents
- `POST /chat` - Chat with documents
- `GET /files` - List uploaded files
- `DELETE /files/{filename}` - Delete files

### 5. New Endpoints
- `POST /register` - Register a new user
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword",
    "full_name": "John Doe" // optional
  }
  ```

- `POST /login` - Login and get JWT token
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword"
  }
  ```

Both endpoints return:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 6. Using Protected Endpoints
Include the JWT token in the Authorization header:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "message": "What is this document about?"
  }'
```

## Frontend Changes

### 1. New Auth Component
A new login/register UI (`Auth.tsx`) is displayed when users are not authenticated.

### 2. Token Management
- JWT tokens are stored in `localStorage`
- Tokens are automatically included in all API requests
- Users can logout to clear the token

### 3. Install Frontend Dependencies
No new dependencies were added. The existing setup works with authentication.

### 4. Running the Frontend
```bash
cd client
npm install
npm run dev
```

## Complete Setup Flow

1. **Setup Database**:
   ```bash
   psql -h $PGHOST -U $PGUSER -d $PGDATABASE -f init_db.sql
   ```

2. **Add Secret Key**:
   ```bash
   echo "SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> .env
   ```

3. **Install Backend Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Backend**:
   ```bash
   python app.py
   ```

5. **Start Frontend**:
   ```bash
   cd client
   npm run dev
   ```

6. **First Use**:
   - Open http://localhost:5173
   - Click "Register" to create an account
   - Login with your credentials
   - Start chatting with your documents!

## Security Notes

- Passwords are hashed using bcrypt before storage
- JWT tokens expire after 30 minutes (configurable in `utils/auth.py`)
- The SECRET_KEY must be kept secure and never committed to version control
- In production, use HTTPS and a strong secret key
- Consider implementing token refresh mechanisms for better UX
- Add rate limiting to prevent brute force attacks

## Token Expiration

JWT tokens expire after 30 minutes. Users will need to login again after expiration. To change the expiration time, modify `ACCESS_TOKEN_EXPIRE_MINUTES` in `utils/auth.py`.

## Troubleshooting

**"Could not validate credentials" error**:
- Check that the token is being sent in the Authorization header
- Verify the token hasn't expired
- Ensure SECRET_KEY is consistent across restarts

**"Email already registered" error**:
- Use a different email or login with existing credentials

**Database connection errors**:
- Ensure PostgreSQL is running
- Verify database credentials in `.env`
- Run the `init_db.sql` script to create the users table
