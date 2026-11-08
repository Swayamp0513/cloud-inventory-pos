# OmniCloud - Multi-Store & Franchise Inventory with Role-Based Authentication

## 🔐 Multi-Tenant Role-Based Access Control (RBAC)

1. **Brand Owner (`ADMIN`)**:
   - Complete global visibility across all franchises.
   - Authorisation to register new franchise outlets.
   - Comprehensive cross-store business analytics and revenue reports.
   - **Pre-configured account**: `owner` / `admin123`

2. **Franchise Store Manager (`MANAGER`)**:
   - Tied specifically to their designated branch/outlet.
   - Can only modify inventory and create customer bills for their assigned store.
   - Analytics scoped to their individual branch performance.
   - **Pre-configured accounts**:
     - `manager1` / `pass123` (Metro Station Express)
     - `manager2` / `pass123` (Suburban Galleria Outlet)

3. **Sign Up & Validation**:
   - Secure password hashing using Werkzeug `generate_password_hash` & `check_password_hash` (PBKDF2/SHA256).
   - Session validation and role enforcement on all API endpoints.

---

## 🚀 Easy & 100% Free Cloud Deployment
- **Render.com**: Push to GitHub -> New Web Service -> Build: `pip install -r requirements.txt`, Start: `gunicorn app:app`.
- **Local**: `pip install -r requirements.txt && python app.py`
