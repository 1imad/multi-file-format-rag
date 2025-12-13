#!/usr/bin/env python3
"""
Test script to verify JWT authentication setup
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_auth():
    print("🔐 Testing JWT Authentication Setup\n")
    
    # Test 1: Register a new user
    print("1️⃣ Testing user registration...")
    register_data = {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=register_data)
        if response.status_code == 201 or response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Registration successful!")
            print(f"   Token: {token[:20]}...")
        elif response.status_code == 400:
            print(f"   ℹ️  User already exists, proceeding to login...")
        else:
            print(f"   ❌ Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 2: Login
    print("\n2️⃣ Testing user login...")
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   ✅ Login successful!")
            print(f"   Token: {token[:20]}...")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return
    
    # Test 3: Access protected endpoint without token
    print("\n3️⃣ Testing protected endpoint without token...")
    try:
        response = requests.get(f"{BASE_URL}/files")
        if response.status_code == 401 or response.status_code == 403:
            print(f"   ✅ Correctly rejected (status {response.status_code})")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Access protected endpoint with token
    print("\n4️⃣ Testing protected endpoint with token...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/files", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Access granted!")
            print(f"   Files: {data.get('total_files', 0)} files found")
        else:
            print(f"   ❌ Access denied: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Test /prompts endpoint (should work without auth)
    print("\n5️⃣ Testing public endpoint (/prompts)...")
    try:
        response = requests.get(f"{BASE_URL}/prompts")
        if response.status_code == 200:
            print(f"   ✅ Public endpoint accessible")
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✨ Authentication test complete!\n")

if __name__ == "__main__":
    test_auth()
